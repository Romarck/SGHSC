"""
routes/emergencia.py — Pronto-Atendimento / Emergência.

Fluxo: registro chegada → triagem Manchester → atendimento médico → saída
"""

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import (
    DecimalField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, NumberRange, Optional

from ..extensions import db
from ..models.emergencia import (
    AtendimentoEmergencia,
    ClassificacaoManchester,
    MotivoSaidaEmergencia,
    StatusAtendimentoEmergencia,
    TriagemManchester,
)
from ..models.paciente import Paciente
from ..utils.authz import requer_permissao

bp = Blueprint("emergencia", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gerar_numero_atendimento() -> str:
    from datetime import datetime
    agora = datetime.now()
    ultimo = db.session.query(db.func.max(AtendimentoEmergencia.id)).scalar() or 0
    return f"PA{agora.strftime('%Y%m%d')}{(ultimo + 1):04d}"


# ---------------------------------------------------------------------------
# Formulários
# ---------------------------------------------------------------------------

class RegistroChegadaForm(FlaskForm):
    paciente_id = HiddenField("Paciente", validators=[DataRequired()])
    modo_chegada = SelectField("Modo de chegada", choices=[
        ("", "Selecione..."),
        ("proprios_meios", "Próprios meios"),
        ("acompanhante", "Acompanhante"),
        ("ambulancia_municipal", "Ambulância municipal"),
        ("samu", "SAMU"),
        ("bombeiros", "Corpo de Bombeiros"),
        ("policia", "Polícia Militar"),
        ("ubs", "Encaminhado pela UBS"),
        ("outro_hospital", "Transferência de outro hospital"),
    ], validators=[Optional()])
    submit = SubmitField("Registrar chegada")


class TriagemForm(FlaskForm):
    queixa_principal = StringField(
        "Queixa principal *",
        validators=[DataRequired()],
        render_kw={"placeholder": "Ex: Dor no peito há 2 horas"}
    )
    discriminador = StringField(
        "Discriminador Manchester",
        validators=[Optional()],
        render_kw={"placeholder": "Ex: Dor torácica moderada"}
    )
    classificacao = SelectField("Classificação de risco *", validators=[DataRequired()], choices=[
        ("", "Selecione a cor..."),
        ("VERMELHO", "🔴 Vermelho — Emergência (imediato)"),
        ("LARANJA", "🟠 Laranja — Muito urgente (≤10 min)"),
        ("AMARELO", "🟡 Amarelo — Urgente (≤60 min)"),
        ("VERDE", "🟢 Verde — Pouco urgente (≤120 min)"),
        ("AZUL", "🔵 Azul — Não urgente (≤240 min)"),
    ])

    # Sinais vitais
    pressao_sistolica = IntegerField("PAS (mmHg)", validators=[Optional(), NumberRange(min=0, max=300)])
    pressao_diastolica = IntegerField("PAD (mmHg)", validators=[Optional(), NumberRange(min=0, max=200)])
    frequencia_cardiaca = IntegerField("FC (bpm)", validators=[Optional(), NumberRange(min=0, max=300)])
    frequencia_respiratoria = IntegerField("FR (irpm)", validators=[Optional(), NumberRange(min=0, max=100)])
    temperatura = DecimalField("Temperatura (°C)", validators=[Optional(), NumberRange(min=30, max=45)], places=1)
    saturacao_o2 = IntegerField("SpO₂ (%)", validators=[Optional(), NumberRange(min=0, max=100)])
    glicemia_capilar = IntegerField("Glicemia capilar (mg/dL)", validators=[Optional(), NumberRange(min=0, max=1000)])
    peso = DecimalField("Peso (kg)", validators=[Optional()], places=1)
    altura = DecimalField("Altura (m)", validators=[Optional()], places=2)
    escala_dor = IntegerField("Escala de dor (0–10)", validators=[Optional(), NumberRange(min=0, max=10)])
    observacoes = TextAreaField("Observações", validators=[Optional()])

    submit = SubmitField("Confirmar triagem")


class AtendimentoMedicoForm(FlaskForm):
    anamnese = TextAreaField("Anamnese", validators=[Optional()])
    exame_fisico = TextAreaField("Exame físico", validators=[Optional()])
    hipotese_diagnostica = StringField("Hipótese diagnóstica", validators=[Optional()])
    cid10_principal = StringField("CID-10 principal", validators=[Optional()])
    conduta = TextAreaField("Conduta", validators=[Optional()])
    submit = SubmitField("Salvar atendimento")


class SaidaForm(FlaskForm):
    motivo_saida = SelectField("Motivo da saída *", validators=[DataRequired()], choices=[
        ("", "Selecione..."),
        ("ALTA_MEDICA", "Alta médica"),
        ("INTERNACAO", "Internação"),
        ("TRANSFERENCIA", "Transferência"),
        ("OBITO", "Óbito"),
        ("EVASAO", "Evasão"),
        ("RECUSA_ATENDIMENTO", "Recusa de atendimento"),
    ])
    destino_internacao = StringField("Destino (internação)", validators=[Optional()])
    destino_transferencia = StringField("Hospital de destino (transferência)", validators=[Optional()])
    submit = SubmitField("Confirmar saída")


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@bp.route("/")
@login_required
@requer_permissao("emergencia.ver")
def fila():
    """Fila de espera e painel de atendimentos ativos."""
    ativos = AtendimentoEmergencia.query.filter(
        AtendimentoEmergencia.status != StatusAtendimentoEmergencia.FINALIZADO
    ).order_by(AtendimentoEmergencia.chegada_em).all()

    hoje = datetime.now(timezone.utc).date()
    finalizados_hoje = AtendimentoEmergencia.query.filter(
        db.func.date(AtendimentoEmergencia.saida_em) == hoje,
        AtendimentoEmergencia.status == StatusAtendimentoEmergencia.FINALIZADO
    ).count()

    return render_template(
        "emergencia/fila.html",
        ativos=ativos,
        finalizados_hoje=finalizados_hoje
    )


@bp.route("/registrar-chegada", methods=["GET", "POST"])
@login_required
@requer_permissao("emergencia.triar")
def registrar_chegada():
    """Registro de chegada do paciente ao PA."""
    form = RegistroChegadaForm()

    if form.validate_on_submit():
        paciente = db.get_or_404(Paciente, int(form.paciente_id.data))

        atendimento = AtendimentoEmergencia(
            numero=_gerar_numero_atendimento(),
            paciente_id=paciente.id,
            registrado_por_id=current_user.id,
            modo_chegada=form.modo_chegada.data or None,
            status=StatusAtendimentoEmergencia.AGUARDANDO_TRIAGEM,
        )
        db.session.add(atendimento)
        db.session.commit()

        flash(
            f"Chegada de {paciente.nome_exibicao} registrada. "
            f"Atendimento {atendimento.numero}.",
            "success"
        )
        return redirect(url_for("emergencia.triagem", id=atendimento.id))

    # Busca paciente por query string (vindo da busca HTMX)
    paciente_id = request.args.get("paciente_id")
    paciente = None
    if paciente_id:
        paciente = Paciente.query.get(int(paciente_id))
        if paciente:
            form.paciente_id.data = str(paciente.id)

    return render_template(
        "emergencia/registrar_chegada.html",
        form=form,
        paciente=paciente
    )


@bp.route("/atendimento/<int:id>/triagem", methods=["GET", "POST"])
@login_required
@requer_permissao("emergencia.triar")
def triagem(id: int):
    """Triagem Manchester do atendimento."""
    atendimento = db.get_or_404(AtendimentoEmergencia, id)

    if atendimento.triagem:
        flash("Este atendimento já foi triado.", "info")
        return redirect(url_for("emergencia.atendimento", id=id))

    form = TriagemForm()

    if form.validate_on_submit():
        t = TriagemManchester(
            atendimento_id=atendimento.id,
            queixa_principal=form.queixa_principal.data,
            discriminador=form.discriminador.data,
            classificacao=ClassificacaoManchester[form.classificacao.data],
            pressao_sistolica=form.pressao_sistolica.data,
            pressao_diastolica=form.pressao_diastolica.data,
            frequencia_cardiaca=form.frequencia_cardiaca.data,
            frequencia_respiratoria=form.frequencia_respiratoria.data,
            temperatura=form.temperatura.data,
            saturacao_o2=form.saturacao_o2.data,
            glicemia_capilar=form.glicemia_capilar.data,
            peso=form.peso.data,
            altura=form.altura.data,
            escala_dor=form.escala_dor.data,
            observacoes=form.observacoes.data,
            realizada_por_id=current_user.id,
        )
        atendimento.status = StatusAtendimentoEmergencia.TRIADO
        db.session.add(t)
        db.session.commit()

        flash(
            f"Triagem realizada: {t.classificacao.value.upper()} — "
            f"{atendimento.paciente.nome_exibicao}",
            "success"
        )
        return redirect(url_for("emergencia.fila"))

    return render_template(
        "emergencia/triagem.html",
        form=form,
        atendimento=atendimento
    )


@bp.route("/atendimento/<int:id>", methods=["GET", "POST"])
@login_required
@requer_permissao("emergencia.atender")
def atendimento(id: int):
    """Atendimento médico."""
    atendimento = db.get_or_404(AtendimentoEmergencia, id)
    form = AtendimentoMedicoForm(obj=atendimento)

    if form.validate_on_submit():
        if not atendimento.inicio_atendimento_em:
            atendimento.inicio_atendimento_em = datetime.now(timezone.utc)
        atendimento.medico_id = current_user.id
        atendimento.status = StatusAtendimentoEmergencia.EM_ATENDIMENTO
        atendimento.anamnese = form.anamnese.data
        atendimento.exame_fisico = form.exame_fisico.data
        atendimento.hipotese_diagnostica = form.hipotese_diagnostica.data
        atendimento.cid10_principal = form.cid10_principal.data
        atendimento.conduta = form.conduta.data
        db.session.commit()
        flash("Registro salvo.", "success")
        return redirect(url_for("emergencia.atendimento", id=id))

    return render_template(
        "emergencia/atendimento.html",
        form=form,
        atendimento=atendimento
    )


@bp.route("/atendimento/<int:id>/saida", methods=["GET", "POST"])
@login_required
@requer_permissao("emergencia.atender")
def saida(id: int):
    """Registra saída / encerramento do atendimento."""
    atendimento = db.get_or_404(AtendimentoEmergencia, id)
    form = SaidaForm()

    if form.validate_on_submit():
        atendimento.saida_em = datetime.now(timezone.utc)
        atendimento.motivo_saida = MotivoSaidaEmergencia[form.motivo_saida.data]
        atendimento.destino_internacao = form.destino_internacao.data
        atendimento.destino_transferencia = form.destino_transferencia.data
        atendimento.status = StatusAtendimentoEmergencia.FINALIZADO
        db.session.commit()

        flash(
            f"Atendimento {atendimento.numero} encerrado: "
            f"{atendimento.motivo_saida.value}.",
            "success"
        )
        return redirect(url_for("emergencia.fila"))

    return render_template(
        "emergencia/saida.html",
        form=form,
        atendimento=atendimento
    )
