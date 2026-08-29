"""
routes/internacao.py — Módulo de Internação Hospitalar.

Fluxo: mapa de leitos → admissão → prontuário (prescrição/evolução/controles) → alta
"""

from datetime import date, datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from ..extensions import db
from ..models.auditoria import AcaoAuditoria
from ..models.internacao import (
    CondicaoAlta,
    ControlesPaciente,
    EvolucaoEnfermagem,
    EvolucaoMedica,
    FrequenciaAdministracao,
    Internacao,
    ItemPrescricao,
    Leito,
    PrescricaoEnfermagem,
    PrescricaoMedica,
    StatusInternacao,
    StatusLeito,
    TipoAlta,
    TipoInternacao,
    TipoItemPrescricao,
    TipoLeito,
    TransferenciaLeito,
    ViaAdministracao,
)
from ..models.paciente import Paciente
from ..services.auditoria_service import registrar_acesso
from ..utils.authz import requer_permissao

bp = Blueprint("internacao", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gerar_numero_internacao() -> str:
    agora = datetime.now()
    ultimo = db.session.query(db.func.max(Internacao.id)).scalar() or 0
    return f"INT{agora.strftime('%Y%m%d')}{(ultimo + 1):04d}"


def _gerar_numero_prescricao() -> str:
    agora = datetime.now()
    ultimo = db.session.query(db.func.max(PrescricaoMedica.id)).scalar() or 0
    return f"RX{agora.strftime('%Y%m%d')}{(ultimo + 1):04d}"


def _choices_enum(enum_class, vazio="Selecione..."):
    return [("", vazio)] + [(e.name, e.value) for e in enum_class]


# ---------------------------------------------------------------------------
# Formulários
# ---------------------------------------------------------------------------

class AdmissaoForm(FlaskForm):
    paciente_id = HiddenField("Paciente", validators=[DataRequired()])
    leito_id = SelectField("Leito *", validators=[DataRequired()], choices=[])
    medico_responsavel_id = SelectField("Médico responsável *", validators=[DataRequired()], choices=[])
    tipo = SelectField("Tipo de internação *", validators=[DataRequired()], choices=[
        ("", "Selecione..."),
        ("ELETIVA", "Eletiva"), ("URGENCIA", "Urgência"),
        ("EMERGENCIA", "Emergência"), ("OBSTETRICIA", "Obstetrícia"),
        ("PSIQUIATRIA", "Psiquiatria"),
    ])
    motivo = StringField("Motivo da internação *", validators=[DataRequired(), Length(max=500)])
    hipotese_diagnostica = StringField("Hipótese diagnóstica", validators=[Optional()])
    cid10_principal = StringField("CID-10 principal", validators=[Optional()])
    convenio = StringField("Convênio", validators=[Optional()], render_kw={"placeholder": "SUS, Unimed..."})
    origem_pa = BooleanField("Veio do Pronto-Atendimento")
    observacoes_admissao = TextAreaField("Observações", validators=[Optional()])
    submit = SubmitField("Confirmar admissão")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Leitos livres ou reservados
        leitos = Leito.query.filter(
            Leito.status.in_([StatusLeito.LIVRE, StatusLeito.RESERVADO]),
            Leito.ativo == True
        ).order_by(Leito.ala, Leito.numero).all()
        self.leito_id.choices = [("", "Selecione o leito...")] + [
            (str(l.id), f"{l.numero} — {l.tipo.value} | {l.ala or ''} {l.andar or ''}".strip())
            for l in leitos
        ]
        from ..models.usuario import TipoPerfil, Usuario
        medicos = Usuario.query.join(Usuario.perfil).filter(
            Usuario.perfil.has(tipo=TipoPerfil.MEDICO)
        ).order_by(Usuario.nome).all()
        self.medico_responsavel_id.choices = [("", "Selecione...")] + [
            (str(m.id), m.nome) for m in medicos
        ]


class TransferenciaForm(FlaskForm):
    leito_destino_id = SelectField("Leito destino *", validators=[DataRequired()], choices=[])
    motivo = StringField("Motivo da transferência", validators=[Optional()])
    submit = SubmitField("Transferir")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        leitos = Leito.query.filter(
            Leito.status.in_([StatusLeito.LIVRE, StatusLeito.RESERVADO]),
            Leito.ativo == True
        ).order_by(Leito.ala, Leito.numero).all()
        self.leito_destino_id.choices = [("", "Selecione...")] + [
            (str(l.id), f"{l.numero} — {l.tipo.value} | {l.ala or ''}")
            for l in leitos
        ]


class AltaForm(FlaskForm):
    tipo_alta = SelectField("Tipo de alta *", validators=[DataRequired()], choices=[
        ("", "Selecione..."),
        ("ALTA_MEDICA", "Alta médica"), ("ALTA_A_PEDIDO", "Alta a pedido"),
        ("TRANSFERENCIA", "Transferência"), ("OBITO", "Óbito"),
        ("EVASAO", "Evasão"), ("ALTA_ADMINISTRATIVA", "Alta administrativa"),
    ])
    condicao_alta = SelectField("Condição na alta *", validators=[DataRequired()], choices=[
        ("", "Selecione..."),
        ("CURADO", "Curado"), ("MELHORADO", "Melhorado"),
        ("INALTERADO", "Inalterado"), ("PIORADO", "Piorado"), ("OBITO", "Óbito"),
    ])
    diagnostico_principal_alta = StringField("Diagnóstico principal", validators=[Optional()])
    cid10_principal = StringField("CID-10 principal", validators=[Optional()])
    resumo_alta = TextAreaField("Resumo da internação *", validators=[DataRequired()])
    orientacoes_alta = TextAreaField("Orientações ao paciente", validators=[Optional()])
    retorno_dias = IntegerField("Retorno em (dias)", validators=[Optional(), NumberRange(1, 365)])
    submit = SubmitField("Confirmar alta e gerar laudo")


class PrescricaoForm(FlaskForm):
    data_prescricao = DateField("Data da prescrição", validators=[DataRequired()])
    observacoes = TextAreaField("Observações gerais", validators=[Optional()])
    submit = SubmitField("Salvar prescrição")


class ItemPrescricaoForm(FlaskForm):
    class Meta:
        csrf = False

    tipo = SelectField("Tipo", choices=[], validators=[DataRequired()])
    descricao = StringField("Medicamento / item *", validators=[DataRequired()])
    dose = StringField("Dose", validators=[Optional()])
    via = SelectField("Via", choices=[], validators=[Optional()])
    frequencia = SelectField("Frequência", choices=[], validators=[Optional()])
    duracao = StringField("Duração", validators=[Optional()])
    horarios = StringField("Horários", validators=[Optional()])
    diluicao = StringField("Diluição", validators=[Optional()])
    observacoes = StringField("Observações", validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo.choices = _choices_enum(TipoItemPrescricao)
        self.via.choices = _choices_enum(ViaAdministracao)
        self.frequencia.choices = _choices_enum(FrequenciaAdministracao)


class ControlesForm(FlaskForm):
    # Sinais vitais
    pressao_sistolica = IntegerField("PAS", validators=[Optional(), NumberRange(0, 300)])
    pressao_diastolica = IntegerField("PAD", validators=[Optional(), NumberRange(0, 200)])
    frequencia_cardiaca = IntegerField("FC", validators=[Optional(), NumberRange(0, 300)])
    frequencia_respiratoria = IntegerField("FR", validators=[Optional(), NumberRange(0, 100)])
    temperatura = DecimalField("Temp °C", validators=[Optional()], places=1)
    saturacao_o2 = IntegerField("SpO₂ %", validators=[Optional(), NumberRange(0, 100)])
    glicemia_capilar = IntegerField("HGT mg/dL", validators=[Optional()])
    escala_dor = IntegerField("Dor 0–10", validators=[Optional(), NumberRange(0, 10)])
    nivel_consciencia = StringField("Consciência", validators=[Optional()])
    # Entradas
    soro_ev = IntegerField("Soro EV (mL)", validators=[Optional()], default=0)
    medicacao_ev = IntegerField("Medicação EV (mL)", validators=[Optional()], default=0)
    ingesta_oral = IntegerField("Ingesta oral (mL)", validators=[Optional()], default=0)
    outros_entrada = IntegerField("Outros entrada (mL)", validators=[Optional()], default=0)
    # Saídas
    diurese = IntegerField("Diurese (mL)", validators=[Optional()], default=0)
    drenos = IntegerField("Drenos (mL)", validators=[Optional()], default=0)
    vomitos = IntegerField("Vômitos (mL)", validators=[Optional()], default=0)
    outros_saida = IntegerField("Outros saída (mL)", validators=[Optional()], default=0)
    evacuacao = BooleanField("Evacuou?")
    evacuacao_caracteristicas = StringField("Características", validators=[Optional()])
    observacoes = TextAreaField("Observações", validators=[Optional()])
    submit = SubmitField("Registrar controles")


class EvolucaoMedicaForm(FlaskForm):
    subjetivo = TextAreaField("S — Subjetivo (queixas)", validators=[Optional()])
    objetivo = TextAreaField("O — Objetivo (exame físico / resultados)", validators=[Optional()])
    avaliacao = TextAreaField("A — Avaliação (diagnóstico)", validators=[Optional()])
    plano = TextAreaField("P — Plano (conduta)", validators=[Optional()])
    evolucao_livre = TextAreaField("Ou texto livre", validators=[Optional()])
    cid10_atual = StringField("CID-10 atual", validators=[Optional()])
    submit = SubmitField("Salvar evolução")


class EvolucaoEnfermagemForm(FlaskForm):
    turno = SelectField("Turno", choices=[
        ("manha", "Manhã (07h–13h)"),
        ("tarde", "Tarde (13h–19h)"),
        ("noite", "Noite (19h–07h)"),
    ])
    conteudo = TextAreaField("Evolução *", validators=[DataRequired()])
    observacoes = TextAreaField("Observações", validators=[Optional()])
    submit = SubmitField("Salvar evolução")


class PrescricaoEnfermagemForm(FlaskForm):
    conteudo = TextAreaField("Cuidados de enfermagem *", validators=[DataRequired()])
    observacoes = TextAreaField("Observações", validators=[Optional()])
    submit = SubmitField("Salvar prescrição")


# ---------------------------------------------------------------------------
# Rotas — Leitos
# ---------------------------------------------------------------------------

@bp.route("/leitos")
@login_required
@requer_permissao("internacao.ver")
def mapa_leitos():
    """Mapa visual de leitos agrupado por ala/andar."""
    leitos = Leito.query.filter_by(ativo=True).order_by(Leito.ala, Leito.andar, Leito.numero).all()

    # Agrupar por ala
    alas: dict = {}
    for leito in leitos:
        chave = leito.ala or "Geral"
        alas.setdefault(chave, []).append(leito)

    # Contadores
    total = len(leitos)
    livres = sum(1 for l in leitos if l.status == StatusLeito.LIVRE)
    ocupados = sum(1 for l in leitos if l.status == StatusLeito.OCUPADO)

    return render_template(
        "internacao/mapa_leitos.html",
        alas=alas, total=total, livres=livres, ocupados=ocupados
    )


@bp.route("/leitos/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("internacao.admitir")
def novo_leito():
    """Cadastro de novo leito."""
    if request.method == "POST":
        leito = Leito(
            numero=request.form.get("numero", "").strip().upper(),
            tipo=TipoLeito[request.form.get("tipo")],
            andar=request.form.get("andar") or None,
            ala=request.form.get("ala") or None,
            quarto=request.form.get("quarto") or None,
            isolamento=bool(request.form.get("isolamento")),
        )
        db.session.add(leito)
        db.session.commit()
        flash(f"Leito {leito.numero} cadastrado.", "success")
        return redirect(url_for("internacao.mapa_leitos"))
    return render_template("internacao/form_leito.html",
                           tipos=TipoLeito)


# ---------------------------------------------------------------------------
# Rotas — Admissão
# ---------------------------------------------------------------------------

@bp.route("/admitir", methods=["GET", "POST"])
@login_required
@requer_permissao("internacao.admitir")
def admitir():
    """Admissão de paciente — registra a internação e ocupa o leito."""
    form = AdmissaoForm()

    # Pré-preenche paciente via GET (vindo do PA ou da busca)
    paciente_id = request.args.get("paciente_id")
    paciente = None
    if paciente_id:
        paciente = Paciente.query.get(int(paciente_id))
        if paciente:
            form.paciente_id.data = str(paciente.id)

    if form.validate_on_submit():
        paciente = db.get_or_404(Paciente, int(form.paciente_id.data))
        leito = db.get_or_404(Leito, int(form.leito_id.data))

        internacao = Internacao(
            numero=_gerar_numero_internacao(),
            paciente_id=paciente.id,
            leito_id=leito.id,
            medico_responsavel_id=int(form.medico_responsavel_id.data),
            admitido_por_id=current_user.id,
            tipo=TipoInternacao[form.tipo.data],
            motivo=form.motivo.data,
            hipotese_diagnostica=form.hipotese_diagnostica.data,
            cid10_principal=form.cid10_principal.data,
            convenio=form.convenio.data or "SUS",
            origem_pa=form.origem_pa.data,
            observacoes_admissao=form.observacoes_admissao.data,
            status=StatusInternacao.ATIVA,
        )
        leito.status = StatusLeito.OCUPADO
        db.session.add(internacao)
        db.session.commit()

        flash(
            f"Paciente {paciente.nome_exibicao} admitido no leito {leito.numero}. "
            f"Internação {internacao.numero}.",
            "success"
        )
        return redirect(url_for("internacao.prontuario", id=internacao.id))

    return render_template("internacao/admissao.html", form=form, paciente=paciente)


# ---------------------------------------------------------------------------
# Rotas — Prontuário da Internação
# ---------------------------------------------------------------------------

@bp.route("/<int:id>")
@login_required
@requer_permissao("internacao.ver")
def prontuario(id: int):
    """Prontuário central da internação com todas as abas."""
    internacao = db.get_or_404(Internacao, id)
    hoje = date.today()

    # Trilha de auditoria LGPD: registra a visualização do prontuário (S-07)
    registrar_acesso(
        AcaoAuditoria.VISUALIZAR,
        paciente_id=internacao.paciente_id,
        recurso="internacao.prontuario",
        recurso_id=internacao.id,
        detalhe=f"Prontuário da internação {internacao.numero}",
    )

    # Prescrição médica ativa (mais recente)
    prescricao_ativa = internacao.prescricoes_medicas.filter_by(ativa=True).first()

    # Controles de hoje
    controles_hoje = internacao.controles.filter(
        db.func.date(ControlesPaciente.registrado_em) == hoje
    ).all()

    # Balanço hídrico acumulado do dia
    balanco_dia = sum(c.balanco_hidrico for c in controles_hoje)

    # Evoluções recentes
    evolucoes_medicas = internacao.evolucoes_medicas.limit(5).all()
    evolucoes_enfermagem = internacao.evolucoes_enfermagem.limit(5).all()

    return render_template(
        "internacao/prontuario.html",
        internacao=internacao,
        prescricao_ativa=prescricao_ativa,
        controles_hoje=controles_hoje,
        balanco_dia=balanco_dia,
        evolucoes_medicas=evolucoes_medicas,
        evolucoes_enfermagem=evolucoes_enfermagem,
        hoje=hoje,
    )


# ---------------------------------------------------------------------------
# Rotas — Prescrição Médica
# ---------------------------------------------------------------------------

@bp.route("/<int:id>/prescricao/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("internacao.prescrever")
def nova_prescricao(id: int):
    """Cria nova prescrição médica (desativa a anterior)."""
    internacao = db.get_or_404(Internacao, id)
    form = PrescricaoForm()

    if request.method == "GET":
        form.data_prescricao.data = date.today()

    if form.validate_on_submit():
        # Desativa prescrição anterior
        internacao.prescricoes_medicas.filter_by(ativa=True).update({"ativa": False})

        prescricao = PrescricaoMedica(
            numero=_gerar_numero_prescricao(),
            internacao_id=internacao.id,
            medico_id=current_user.id,
            data_prescricao=form.data_prescricao.data,
            observacoes=form.observacoes.data,
            ativa=True,
        )
        db.session.add(prescricao)
        db.session.flush()

        # Itens enviados via form dinâmico
        itens_desc = request.form.getlist("item_descricao")
        itens_tipo = request.form.getlist("item_tipo")
        itens_dose = request.form.getlist("item_dose")
        itens_via = request.form.getlist("item_via")
        itens_freq = request.form.getlist("item_frequencia")
        itens_dur = request.form.getlist("item_duracao")
        itens_hor = request.form.getlist("item_horarios")
        itens_dil = request.form.getlist("item_diluicao")
        itens_obs = request.form.getlist("item_observacoes")

        for i, desc in enumerate(itens_desc):
            if not desc.strip():
                continue
            item = ItemPrescricao(
                prescricao_id=prescricao.id,
                ordem=i + 1,
                tipo=TipoItemPrescricao[itens_tipo[i]] if itens_tipo[i] else TipoItemPrescricao.MEDICAMENTO,
                descricao=desc.strip(),
                dose=itens_dose[i] if i < len(itens_dose) else None,
                via=ViaAdministracao[itens_via[i]] if i < len(itens_via) and itens_via[i] else None,
                frequencia=FrequenciaAdministracao[itens_freq[i]] if i < len(itens_freq) and itens_freq[i] else None,
                duracao=itens_dur[i] if i < len(itens_dur) else None,
                horarios=itens_hor[i] if i < len(itens_hor) else None,
                diluicao=itens_dil[i] if i < len(itens_dil) else None,
                observacoes=itens_obs[i] if i < len(itens_obs) else None,
            )
            db.session.add(item)

        db.session.commit()
        flash(f"Prescrição {prescricao.numero} salva.", "success")
        return redirect(url_for("internacao.prontuario", id=internacao.id))

    # Copia itens da prescrição anterior (se houver)
    prescricao_anterior = internacao.prescricoes_medicas.first()

    return render_template(
        "internacao/prescricao.html",
        form=form,
        internacao=internacao,
        prescricao_anterior=prescricao_anterior,
        tipos_item=TipoItemPrescricao,
        vias=ViaAdministracao,
        frequencias=FrequenciaAdministracao,
    )


# ---------------------------------------------------------------------------
# Rotas — Controles do Paciente
# ---------------------------------------------------------------------------

@bp.route("/<int:id>/controles", methods=["GET", "POST"])
@login_required
@requer_permissao("internacao.prescrever_enfermagem")
def controles(id: int):
    """Registro de controles (sinais vitais + balanço hídrico)."""
    internacao = db.get_or_404(Internacao, id)
    form = ControlesForm()

    if form.validate_on_submit():
        ctrl = ControlesPaciente(
            internacao_id=internacao.id,
            registrado_por_id=current_user.id,
            pressao_sistolica=form.pressao_sistolica.data,
            pressao_diastolica=form.pressao_diastolica.data,
            frequencia_cardiaca=form.frequencia_cardiaca.data,
            frequencia_respiratoria=form.frequencia_respiratoria.data,
            temperatura=form.temperatura.data,
            saturacao_o2=form.saturacao_o2.data,
            glicemia_capilar=form.glicemia_capilar.data,
            escala_dor=form.escala_dor.data,
            nivel_consciencia=form.nivel_consciencia.data,
            soro_ev=form.soro_ev.data or 0,
            medicacao_ev=form.medicacao_ev.data or 0,
            ingesta_oral=form.ingesta_oral.data or 0,
            outros_entrada=form.outros_entrada.data or 0,
            diurese=form.diurese.data or 0,
            drenos=form.drenos.data or 0,
            vomitos=form.vomitos.data or 0,
            outros_saida=form.outros_saida.data or 0,
            evacuacao=form.evacuacao.data,
            evacuacao_caracteristicas=form.evacuacao_caracteristicas.data,
            observacoes=form.observacoes.data,
        )
        db.session.add(ctrl)
        db.session.commit()
        flash("Controles registrados.", "success")
        return redirect(url_for("internacao.prontuario", id=internacao.id))

    return render_template("internacao/controles.html", form=form, internacao=internacao)


# ---------------------------------------------------------------------------
# Rotas — Evoluções
# ---------------------------------------------------------------------------

@bp.route("/<int:id>/evolucao-medica", methods=["GET", "POST"])
@login_required
@requer_permissao("internacao.evoluir")
def evolucao_medica(id: int):
    internacao = db.get_or_404(Internacao, id)
    form = EvolucaoMedicaForm()

    if form.validate_on_submit():
        ev = EvolucaoMedica(
            internacao_id=internacao.id,
            medico_id=current_user.id,
            subjetivo=form.subjetivo.data,
            objetivo=form.objetivo.data,
            avaliacao=form.avaliacao.data,
            plano=form.plano.data,
            evolucao_livre=form.evolucao_livre.data,
            cid10_atual=form.cid10_atual.data,
        )
        db.session.add(ev)
        db.session.commit()
        flash("Evolução médica registrada.", "success")
        return redirect(url_for("internacao.prontuario", id=internacao.id))

    return render_template("internacao/evolucao_medica.html", form=form, internacao=internacao)


@bp.route("/<int:id>/evolucao-enfermagem", methods=["GET", "POST"])
@login_required
@requer_permissao("internacao.prescrever_enfermagem")
def evolucao_enfermagem(id: int):
    internacao = db.get_or_404(Internacao, id)
    form = EvolucaoEnfermagemForm()

    if form.validate_on_submit():
        ev = EvolucaoEnfermagem(
            internacao_id=internacao.id,
            profissional_id=current_user.id,
            turno=form.turno.data,
            conteudo=form.conteudo.data,
            observacoes=form.observacoes.data,
        )
        db.session.add(ev)
        db.session.commit()
        flash("Evolução de enfermagem registrada.", "success")
        return redirect(url_for("internacao.prontuario", id=internacao.id))

    return render_template("internacao/evolucao_enfermagem.html", form=form, internacao=internacao)


@bp.route("/<int:id>/prescricao-enfermagem", methods=["GET", "POST"])
@login_required
@requer_permissao("internacao.prescrever_enfermagem")
def prescricao_enfermagem(id: int):
    internacao = db.get_or_404(Internacao, id)
    form = PrescricaoEnfermagemForm()

    if form.validate_on_submit():
        # Desativa a anterior
        internacao.prescricoes_enfermagem.filter_by(ativa=True).update({"ativa": False})
        pef = PrescricaoEnfermagem(
            internacao_id=internacao.id,
            enfermeiro_id=current_user.id,
            data_prescricao=date.today(),
            conteudo=form.conteudo.data,
            observacoes=form.observacoes.data,
            ativa=True,
        )
        db.session.add(pef)
        db.session.commit()
        flash("Prescrição de enfermagem salva.", "success")
        return redirect(url_for("internacao.prontuario", id=internacao.id))

    return render_template("internacao/prescricao_enfermagem.html", form=form, internacao=internacao)


# ---------------------------------------------------------------------------
# Rotas — Transferência de Leito
# ---------------------------------------------------------------------------

@bp.route("/<int:id>/transferir", methods=["GET", "POST"])
@login_required
@requer_permissao("internacao.admitir")
def transferir(id: int):
    internacao = db.get_or_404(Internacao, id)
    form = TransferenciaForm()

    if form.validate_on_submit():
        leito_destino = db.get_or_404(Leito, int(form.leito_destino_id.data))
        leito_origem = internacao.leito

        transferencia = TransferenciaLeito(
            internacao_id=internacao.id,
            leito_origem_id=leito_origem.id,
            leito_destino_id=leito_destino.id,
            motivo=form.motivo.data,
            realizada_por_id=current_user.id,
        )

        # Atualiza status dos leitos
        leito_origem.status = StatusLeito.LIMPEZA
        leito_destino.status = StatusLeito.OCUPADO
        internacao.leito_id = leito_destino.id

        db.session.add(transferencia)
        db.session.commit()

        flash(
            f"Transferência realizada: {leito_origem.numero} → {leito_destino.numero}.",
            "success"
        )
        return redirect(url_for("internacao.prontuario", id=internacao.id))

    return render_template("internacao/transferencia.html", form=form, internacao=internacao)


# ---------------------------------------------------------------------------
# Rotas — Alta Hospitalar
# ---------------------------------------------------------------------------

@bp.route("/<int:id>/alta", methods=["GET", "POST"])
@login_required
@requer_permissao("internacao.alta")
def alta(id: int):
    internacao = db.get_or_404(Internacao, id)
    form = AltaForm()

    if form.validate_on_submit():
        internacao.alta_em = datetime.now(timezone.utc)
        internacao.tipo_alta = TipoAlta[form.tipo_alta.data]
        internacao.condicao_alta = CondicaoAlta[form.condicao_alta.data]
        internacao.diagnostico_principal_alta = form.diagnostico_principal_alta.data
        internacao.resumo_alta = form.resumo_alta.data
        internacao.orientacoes_alta = form.orientacoes_alta.data
        internacao.retorno_dias = form.retorno_dias.data
        internacao.dado_alta_por_id = current_user.id

        if form.tipo_alta.data == "OBITO":
            internacao.status = StatusInternacao.OBITO
        elif form.tipo_alta.data == "TRANSFERENCIA":
            internacao.status = StatusInternacao.TRANSFERIDA
        else:
            internacao.status = StatusInternacao.ALTA

        # Libera o leito
        internacao.leito.status = StatusLeito.LIMPEZA

        db.session.commit()

        # Gera o laudo de alta em PDF
        try:
            from ..services.pdf_service import gerar_laudo_alta
            pdf_path = gerar_laudo_alta(internacao)
            internacao.alta_pdf_path = pdf_path
            db.session.commit()
            flash(
                f"Alta de {internacao.paciente.nome_exibicao} registrada. "
                f"Laudo gerado.",
                "success"
            )
        except Exception as e:
            flash(
                f"Alta registrada, mas houve erro ao gerar PDF: {e}",
                "warning"
            )

        return redirect(url_for("internacao.mapa_leitos"))

    return render_template("internacao/alta.html", form=form, internacao=internacao)


@bp.route("/<int:id>/alta/pdf")
@login_required
@requer_permissao("internacao.ver")
def baixar_laudo_alta(id: int):
    """Download do laudo de alta em PDF."""
    internacao = db.get_or_404(Internacao, id)
    if not internacao.alta_pdf_path:
        abort(404)
    import os
    if not os.path.exists(internacao.alta_pdf_path):
        abort(404)

    # Trilha de auditoria LGPD: registra o download do laudo de alta (S-07)
    registrar_acesso(
        AcaoAuditoria.BAIXAR_DOCUMENTO,
        paciente_id=internacao.paciente_id,
        recurso="internacao.baixar_laudo_alta",
        recurso_id=internacao.id,
        detalhe=f"Laudo de alta {internacao.numero}",
    )

    return send_file(
        internacao.alta_pdf_path,
        as_attachment=True,
        download_name=f"laudo_alta_{internacao.numero}.pdf"
    )


# ---------------------------------------------------------------------------
# Rota — Lista de internações ativas
# ---------------------------------------------------------------------------

@bp.route("/")
@login_required
@requer_permissao("internacao.ver")
def listar():
    """Lista de internações ativas."""
    internacoes = Internacao.query.filter_by(
        status=StatusInternacao.ATIVA
    ).order_by(Internacao.admissao_em).all()

    return render_template("internacao/lista.html", internacoes=internacoes)


# ---------------------------------------------------------------------------
# Rotas — Assinatura digital (ICP-Brasil)
# ---------------------------------------------------------------------------

@bp.route("/prescricao/<int:pid>/assinar", methods=["POST"])
@login_required
@requer_permissao("certificado.usar")
def assinar_prescricao(pid: int):
    """Gera o PDF da prescrição, assina digitalmente e sela o documento."""
    from ..models.certificado import TipoDocumentoAssinado
    from ..routes.certificado import assinar_documento
    from ..services.pdf_service import gerar_pdf_prescricao

    prescricao = db.get_or_404(PrescricaoMedica, pid)

    if prescricao.assinada:
        flash("Esta prescrição já está assinada.", "info")
        return redirect(url_for("internacao.prontuario", id=prescricao.internacao_id))

    try:
        pdf_path = gerar_pdf_prescricao(prescricao)
        doc = assinar_documento(
            pdf_path,
            TipoDocumentoAssinado.PRESCRICAO_MEDICA,
            f"Prescrição {prescricao.numero}",
            paciente_id=prescricao.internacao.paciente_id,
            origem_tipo="prescricao_medica",
            origem_id=prescricao.id,
        )
    except ValueError as e:
        flash(str(e) + " Cadastre um certificado em Certificação Digital.", "warning")
        return redirect(url_for("internacao.prontuario", id=prescricao.internacao_id))
    except Exception as e:
        flash(f"Erro ao assinar: {e}", "danger")
        return redirect(url_for("internacao.prontuario", id=prescricao.internacao_id))

    prescricao.assinada = True
    prescricao.assinada_em = doc.assinado_em
    prescricao.assinatura_hash = doc.hash_documento
    prescricao.pdf_path = doc.pdf_path
    db.session.commit()

    flash(f"Prescrição {prescricao.numero} assinada digitalmente. "
          f"Código de validação: {doc.codigo_validacao}.", "success")
    return redirect(url_for("internacao.prontuario", id=prescricao.internacao_id))


@bp.route("/evolucao-medica/<int:eid>/assinar", methods=["POST"])
@login_required
@requer_permissao("certificado.usar")
def assinar_evolucao_medica(eid: int):
    """Gera o PDF da evolução médica, assina digitalmente e sela."""
    from ..models.certificado import TipoDocumentoAssinado
    from ..routes.certificado import assinar_documento
    from ..services.pdf_service import gerar_pdf_evolucao_medica

    evolucao = db.get_or_404(EvolucaoMedica, eid)

    if evolucao.assinada:
        flash("Esta evolução já está assinada.", "info")
        return redirect(url_for("internacao.prontuario", id=evolucao.internacao_id))

    try:
        pdf_path = gerar_pdf_evolucao_medica(evolucao)
        doc = assinar_documento(
            pdf_path,
            TipoDocumentoAssinado.EVOLUCAO_MEDICA,
            f"Evolução médica de {evolucao.registrado_em.strftime('%d/%m/%Y')}",
            paciente_id=evolucao.internacao.paciente_id,
            origem_tipo="evolucao_medica",
            origem_id=evolucao.id,
        )
    except ValueError as e:
        flash(str(e) + " Cadastre um certificado em Certificação Digital.", "warning")
        return redirect(url_for("internacao.prontuario", id=evolucao.internacao_id))
    except Exception as e:
        flash(f"Erro ao assinar: {e}", "danger")
        return redirect(url_for("internacao.prontuario", id=evolucao.internacao_id))

    evolucao.assinada = True
    evolucao.assinada_em = doc.assinado_em
    evolucao.assinatura_hash = doc.hash_documento
    evolucao.pdf_path = doc.pdf_path
    db.session.commit()

    flash(f"Evolução médica assinada digitalmente. "
          f"Código de validação: {doc.codigo_validacao}.", "success")
    return redirect(url_for("internacao.prontuario", id=evolucao.internacao_id))


@bp.route("/evolucao-enfermagem/<int:eid>/assinar", methods=["POST"])
@login_required
@requer_permissao("certificado.usar")
def assinar_evolucao_enfermagem(eid: int):
    """Gera o PDF da evolução de enfermagem, assina digitalmente e sela."""
    from ..models.certificado import TipoDocumentoAssinado
    from ..routes.certificado import assinar_documento
    from ..services.pdf_service import gerar_pdf_evolucao_enfermagem

    evolucao = db.get_or_404(EvolucaoEnfermagem, eid)

    if evolucao.assinada:
        flash("Esta evolução já está assinada.", "info")
        return redirect(url_for("internacao.prontuario", id=evolucao.internacao_id))

    try:
        pdf_path = gerar_pdf_evolucao_enfermagem(evolucao)
        doc = assinar_documento(
            pdf_path,
            TipoDocumentoAssinado.EVOLUCAO_MEDICA,  # tipo genérico de evolução
            f"Evolução de enfermagem de {evolucao.registrado_em.strftime('%d/%m/%Y')}",
            paciente_id=evolucao.internacao.paciente_id,
            origem_tipo="evolucao_enfermagem",
            origem_id=evolucao.id,
        )
    except ValueError as e:
        flash(str(e) + " Cadastre um certificado em Certificação Digital.", "warning")
        return redirect(url_for("internacao.prontuario", id=evolucao.internacao_id))
    except Exception as e:
        flash(f"Erro ao assinar: {e}", "danger")
        return redirect(url_for("internacao.prontuario", id=evolucao.internacao_id))

    evolucao.assinada = True
    evolucao.assinada_em = doc.assinado_em
    evolucao.assinatura_hash = doc.hash_documento
    evolucao.pdf_path = doc.pdf_path
    db.session.commit()

    flash(f"Evolução de enfermagem assinada. Código: {doc.codigo_validacao}.", "success")
    return redirect(url_for("internacao.prontuario", id=evolucao.internacao_id))


@bp.route("/prescricao-enfermagem/<int:pid>/assinar", methods=["POST"])
@login_required
@requer_permissao("certificado.usar")
def assinar_prescricao_enfermagem(pid: int):
    """Gera o PDF da prescrição de enfermagem, assina digitalmente e sela."""
    from ..models.certificado import TipoDocumentoAssinado
    from ..routes.certificado import assinar_documento
    from ..services.pdf_service import gerar_pdf_prescricao_enfermagem

    pef = db.get_or_404(PrescricaoEnfermagem, pid)

    if pef.assinada:
        flash("Esta prescrição de enfermagem já está assinada.", "info")
        return redirect(url_for("internacao.prontuario", id=pef.internacao_id))

    try:
        pdf_path = gerar_pdf_prescricao_enfermagem(pef)
        doc = assinar_documento(
            pdf_path,
            TipoDocumentoAssinado.PRESCRICAO_MEDICA,  # tipo genérico de prescrição
            f"Prescrição de enfermagem de {pef.data_prescricao.strftime('%d/%m/%Y')}",
            paciente_id=pef.internacao.paciente_id,
            origem_tipo="prescricao_enfermagem",
            origem_id=pef.id,
        )
    except ValueError as e:
        flash(str(e) + " Cadastre um certificado em Certificação Digital.", "warning")
        return redirect(url_for("internacao.prontuario", id=pef.internacao_id))
    except Exception as e:
        flash(f"Erro ao assinar: {e}", "danger")
        return redirect(url_for("internacao.prontuario", id=pef.internacao_id))

    pef.assinada = True
    pef.assinada_em = doc.assinado_em
    pef.assinatura_hash = doc.hash_documento
    pef.pdf_path = doc.pdf_path
    db.session.commit()

    flash(f"Prescrição de enfermagem assinada. Código: {doc.codigo_validacao}.", "success")
    return redirect(url_for("internacao.prontuario", id=pef.internacao_id))
