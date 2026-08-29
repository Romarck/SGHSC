"""
routes/pacientes.py — CRUD de pacientes com busca HTMX.
"""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    EmailField,
    SelectField,
    StringField,
    SubmitField,
    TelField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional

from ..extensions import db
from ..models.auditoria import AcaoAuditoria
from ..models.paciente import (
    EstadoCivil,
    Paciente,
    RacaCor,
    Sexo,
    StatusPaciente,
    TipoLogradouro,
    TipoSanguineo,
)
from ..models.prontuario import Prontuario
from ..services.auditoria_service import registrar_acesso
from ..utils.authz import requer_permissao

bp = Blueprint("pacientes", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gerar_numero_prontuario() -> str:
    """Gera número de prontuário sequencial no formato ANO-NNNNNN."""
    ano = datetime.now().year
    ultimo = db.session.query(db.func.max(Prontuario.id)).scalar() or 0
    return f"{ano}-{(ultimo + 1):06d}"


def _choices_enum(enum_class, vazio="Selecione..."):
    """Gera lista de choices para SelectField a partir de um Enum."""
    choices = [("", vazio)]
    choices += [(e.name, e.value) for e in enum_class]
    return choices


# ---------------------------------------------------------------------------
# Formulário de Paciente
# ---------------------------------------------------------------------------

class PacienteForm(FlaskForm):
    # Identificação
    nome = StringField("Nome completo *", validators=[DataRequired(), Length(max=200)])
    nome_social = StringField("Nome social", validators=[Optional(), Length(max=200)])
    data_nascimento = DateField("Data de nascimento *", validators=[DataRequired()])
    sexo = SelectField("Sexo *", validators=[DataRequired()],
                       choices=[("", "Selecione..."), ("MASCULINO", "Masculino"),
                                 ("FEMININO", "Feminino"), ("INDEFINIDO", "Não informado")])
    raca_cor = SelectField("Raça/Cor", choices=[], validators=[Optional()])
    estado_civil = SelectField("Estado civil", choices=[], validators=[Optional()])
    tipo_sanguineo = SelectField("Tipo sanguíneo", choices=[], validators=[Optional()])
    naturalidade = StringField("Naturalidade", validators=[Optional(), Length(max=100)])
    nacionalidade = StringField("Nacionalidade", validators=[Optional(), Length(max=60)])

    # Documentos
    cpf = StringField("CPF", validators=[Optional(), Length(max=14)])
    rg = StringField("RG", validators=[Optional(), Length(max=20)])
    rg_orgao_emissor = StringField("Órgão emissor", validators=[Optional(), Length(max=20)])
    rg_uf = StringField("UF", validators=[Optional(), Length(max=2)])
    cns = StringField("CNS (Cartão Nacional de Saúde)", validators=[Optional(), Length(max=20)])

    # Dados de saúde
    plano_saude = StringField("Plano de saúde", validators=[Optional(), Length(max=100)])
    numero_carteirinha = StringField("Nº carteirinha", validators=[Optional(), Length(max=50)])
    alergias = TextAreaField("Alergias conhecidas", validators=[Optional()])
    observacoes_clinicas = TextAreaField("Observações clínicas", validators=[Optional()])

    # Dados sociais
    escolaridade = SelectField("Escolaridade", choices=[
        ("", "Selecione..."), ("sem_instrucao", "Sem instrução"),
        ("fundamental_incompleto", "Fundamental incompleto"),
        ("fundamental_completo", "Fundamental completo"),
        ("medio_incompleto", "Médio incompleto"),
        ("medio_completo", "Médio completo"),
        ("superior_incompleto", "Superior incompleto"),
        ("superior_completo", "Superior completo"),
        ("pos_graduacao", "Pós-graduação"),
    ], validators=[Optional()])
    ocupacao = StringField("Ocupação", validators=[Optional(), Length(max=100)])

    # Endereço
    cep = StringField("CEP", validators=[Optional(), Length(max=9)])
    tipo_logradouro = SelectField("Tipo", choices=[], validators=[Optional()])
    logradouro = StringField("Logradouro", validators=[Optional(), Length(max=200)])
    numero = StringField("Número", validators=[Optional(), Length(max=10)])
    complemento = StringField("Complemento", validators=[Optional(), Length(max=80)])
    bairro = StringField("Bairro", validators=[Optional(), Length(max=100)])
    cidade = StringField("Cidade", validators=[Optional(), Length(max=100)])
    uf = SelectField("UF", choices=[("", "UF")] + [
        (u, u) for u in ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT",
                          "MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO",
                          "RR","SC","SP","SE","TO"]
    ], validators=[Optional()])
    zona = SelectField("Zona", choices=[
        ("", "Selecione..."), ("urbana", "Urbana"), ("rural", "Rural")
    ], validators=[Optional()])

    # Contato
    telefone = TelField("Telefone principal", validators=[Optional(), Length(max=20)])
    telefone2 = TelField("Telefone secundário", validators=[Optional(), Length(max=20)])
    email = EmailField("E-mail", validators=[Optional(), Length(max=150)])

    # Filiação
    nome_mae = StringField("Nome da mãe", validators=[Optional(), Length(max=200)])
    nome_pai = StringField("Nome do pai", validators=[Optional(), Length(max=200)])

    # Responsável
    responsavel_nome = StringField("Nome do responsável", validators=[Optional(), Length(max=200)])
    responsavel_grau = StringField("Grau de parentesco", validators=[Optional(), Length(max=50)])
    responsavel_cpf = StringField("CPF do responsável", validators=[Optional(), Length(max=14)])
    responsavel_telefone = TelField("Telefone do responsável", validators=[Optional(), Length(max=20)])

    submit = SubmitField("Salvar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raca_cor.choices = _choices_enum(RacaCor)
        self.estado_civil.choices = _choices_enum(EstadoCivil)
        self.tipo_sanguineo.choices = _choices_enum(TipoSanguineo)
        self.tipo_logradouro.choices = _choices_enum(TipoLogradouro)


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@bp.route("/")
@login_required
@requer_permissao("pacientes.ver")
def listar():
    """Lista de pacientes com paginação e busca."""
    busca = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Paciente.query.filter(
        Paciente.status != StatusPaciente.INATIVO
    )

    if busca:
        like = f"%{busca}%"
        query = query.filter(
            db.or_(
                Paciente.nome.ilike(like),
                Paciente.cpf.ilike(like),
                Paciente.cns.ilike(like),
            )
        )

    pacientes = query.order_by(Paciente.nome).paginate(
        page=page,
        per_page=20,
        error_out=False
    )

    # Resposta parcial para HTMX (só a tabela)
    if request.headers.get("HX-Request"):
        return render_template(
            "pacientes/_tabela.html",
            pacientes=pacientes,
            busca=busca
        )

    return render_template(
        "pacientes/lista.html",
        pacientes=pacientes,
        busca=busca
    )


@bp.route("/busca")
@login_required
@requer_permissao("pacientes.ver")
def busca_htmx():
    """Endpoint HTMX para busca em tempo real (usado em outros módulos)."""
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return "<p class='text-muted p-2'>Digite pelo menos 2 caracteres.</p>"

    like = f"%{q}%"
    pacientes = Paciente.query.filter(
        Paciente.status == StatusPaciente.ATIVO,
        db.or_(
            Paciente.nome.ilike(like),
            Paciente.cpf.ilike(like),
            Paciente.cns.ilike(like),
        )
    ).order_by(Paciente.nome).limit(10).all()

    return render_template("pacientes/_resultado_busca.html", pacientes=pacientes, q=q)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("pacientes.criar")
def novo():
    """Cadastro de novo paciente."""
    form = PacienteForm()

    if form.validate_on_submit():
        # Verifica duplicidade de CPF
        if form.cpf.data:
            cpf_limpo = form.cpf.data.replace(".", "").replace("-", "").strip()
            if Paciente.query.filter_by(cpf=cpf_limpo).first():
                flash("Já existe um paciente cadastrado com este CPF.", "danger")
                return render_template("pacientes/form.html", form=form, titulo="Novo Paciente")

        paciente = Paciente(
            nome=form.nome.data.strip().upper(),
            nome_social=form.nome_social.data.strip() if form.nome_social.data else None,
            data_nascimento=form.data_nascimento.data,
            sexo=Sexo[form.sexo.data] if form.sexo.data else None,
            raca_cor=RacaCor[form.raca_cor.data] if form.raca_cor.data else RacaCor.NAO_DECLARADO,
            estado_civil=EstadoCivil[form.estado_civil.data] if form.estado_civil.data else EstadoCivil.NAO_INFORMADO,
            tipo_sanguineo=TipoSanguineo[form.tipo_sanguineo.data] if form.tipo_sanguineo.data else TipoSanguineo.DESCONHECIDO,
            naturalidade=form.naturalidade.data,
            nacionalidade=form.nacionalidade.data or "Brasileira",
            cpf=form.cpf.data.replace(".", "").replace("-", "").strip() if form.cpf.data else None,
            rg=form.rg.data,
            rg_orgao_emissor=form.rg_orgao_emissor.data,
            rg_uf=form.rg_uf.data,
            cns=form.cns.data,
            plano_saude=form.plano_saude.data,
            numero_carteirinha=form.numero_carteirinha.data,
            alergias=form.alergias.data,
            observacoes_clinicas=form.observacoes_clinicas.data,
            escolaridade=form.escolaridade.data,
            ocupacao=form.ocupacao.data,
            cep=form.cep.data,
            tipo_logradouro=TipoLogradouro[form.tipo_logradouro.data] if form.tipo_logradouro.data else TipoLogradouro.RUA,
            logradouro=form.logradouro.data,
            numero=form.numero.data,
            complemento=form.complemento.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            uf=form.uf.data,
            zona=form.zona.data,
            telefone=form.telefone.data,
            telefone2=form.telefone2.data,
            email=form.email.data,
            nome_mae=form.nome_mae.data.strip().upper() if form.nome_mae.data else None,
            nome_pai=form.nome_pai.data.strip().upper() if form.nome_pai.data else None,
            responsavel_nome=form.responsavel_nome.data,
            responsavel_grau=form.responsavel_grau.data,
            responsavel_cpf=form.responsavel_cpf.data,
            responsavel_telefone=form.responsavel_telefone.data,
            criado_por_id=current_user.id,
        )
        db.session.add(paciente)
        db.session.flush()  # gera paciente.id

        # Abre prontuário automaticamente
        prontuario = Prontuario(
            numero=_gerar_numero_prontuario(),
            paciente_id=paciente.id,
            aberto_por_id=current_user.id,
        )
        db.session.add(prontuario)
        db.session.commit()

        flash(f"Paciente {paciente.nome} cadastrado com sucesso. Prontuário {prontuario.numero} aberto.", "success")
        return redirect(url_for("pacientes.detalhe", id=paciente.id))

    return render_template("pacientes/form.html", form=form, titulo="Novo Paciente")


@bp.route("/<int:id>")
@login_required
@requer_permissao("pacientes.ver")
def detalhe(id: int):
    """Detalhe do paciente + resumo do prontuário."""
    from ..models.ambulatorio import ConsultaAmbulatorial
    from ..models.emergencia import AtendimentoEmergencia

    paciente = db.get_or_404(Paciente, id)

    # Trilha de auditoria LGPD: registra a visualização dos dados do paciente (S-07)
    registrar_acesso(
        AcaoAuditoria.VISUALIZAR,
        paciente_id=paciente.id,
        recurso="pacientes.detalhe",
        recurso_id=paciente.id,
        detalhe="Detalhe do paciente + resumo do prontuário",
    )

    # Resumos ordenados (feitos aqui, não no template — SQLAlchemy 2 não aceita
    # order_by com string literal)
    atendimentos = paciente.atendimentos_emergencia.order_by(
        AtendimentoEmergencia.chegada_em.desc()
    ).limit(5).all()
    consultas = paciente.consultas_ambulatoriais.order_by(
        ConsultaAmbulatorial.data.desc()
    ).limit(5).all()

    return render_template(
        "pacientes/detalhe.html",
        paciente=paciente,
        atendimentos=atendimentos,
        consultas=consultas,
    )


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@requer_permissao("pacientes.criar")
def editar(id: int):
    """Edição de dados cadastrais do paciente."""
    paciente = db.get_or_404(Paciente, id)
    form = PacienteForm(obj=paciente)

    # Preenche campos de enum como string do nome
    if request.method == "GET":
        form.sexo.data = paciente.sexo.name if paciente.sexo else ""
        form.raca_cor.data = paciente.raca_cor.name if paciente.raca_cor else ""
        form.estado_civil.data = paciente.estado_civil.name if paciente.estado_civil else ""
        form.tipo_sanguineo.data = paciente.tipo_sanguineo.name if paciente.tipo_sanguineo else ""
        form.tipo_logradouro.data = paciente.tipo_logradouro.name if paciente.tipo_logradouro else ""

    if form.validate_on_submit():
        paciente.nome = form.nome.data.strip().upper()
        paciente.nome_social = form.nome_social.data.strip() if form.nome_social.data else None
        paciente.data_nascimento = form.data_nascimento.data
        paciente.sexo = Sexo[form.sexo.data] if form.sexo.data else paciente.sexo
        paciente.raca_cor = RacaCor[form.raca_cor.data] if form.raca_cor.data else paciente.raca_cor
        paciente.estado_civil = EstadoCivil[form.estado_civil.data] if form.estado_civil.data else paciente.estado_civil
        paciente.tipo_sanguineo = TipoSanguineo[form.tipo_sanguineo.data] if form.tipo_sanguineo.data else paciente.tipo_sanguineo
        paciente.naturalidade = form.naturalidade.data
        paciente.nacionalidade = form.nacionalidade.data or "Brasileira"
        paciente.cpf = form.cpf.data.replace(".", "").replace("-", "").strip() if form.cpf.data else None
        paciente.rg = form.rg.data
        paciente.rg_orgao_emissor = form.rg_orgao_emissor.data
        paciente.rg_uf = form.rg_uf.data
        paciente.cns = form.cns.data
        paciente.plano_saude = form.plano_saude.data
        paciente.numero_carteirinha = form.numero_carteirinha.data
        paciente.alergias = form.alergias.data
        paciente.observacoes_clinicas = form.observacoes_clinicas.data
        paciente.escolaridade = form.escolaridade.data
        paciente.ocupacao = form.ocupacao.data
        paciente.cep = form.cep.data
        paciente.tipo_logradouro = TipoLogradouro[form.tipo_logradouro.data] if form.tipo_logradouro.data else paciente.tipo_logradouro
        paciente.logradouro = form.logradouro.data
        paciente.numero = form.numero.data
        paciente.complemento = form.complemento.data
        paciente.bairro = form.bairro.data
        paciente.cidade = form.cidade.data
        paciente.uf = form.uf.data
        paciente.zona = form.zona.data
        paciente.telefone = form.telefone.data
        paciente.telefone2 = form.telefone2.data
        paciente.email = form.email.data
        paciente.nome_mae = form.nome_mae.data.strip().upper() if form.nome_mae.data else None
        paciente.nome_pai = form.nome_pai.data.strip().upper() if form.nome_pai.data else None
        paciente.responsavel_nome = form.responsavel_nome.data
        paciente.responsavel_grau = form.responsavel_grau.data
        paciente.responsavel_cpf = form.responsavel_cpf.data
        paciente.responsavel_telefone = form.responsavel_telefone.data

        db.session.commit()
        flash("Dados do paciente atualizados com sucesso.", "success")
        return redirect(url_for("pacientes.detalhe", id=paciente.id))

    return render_template("pacientes/form.html", form=form, titulo="Editar Paciente", paciente=paciente)
