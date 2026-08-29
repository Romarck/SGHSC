"""
routes/ambulatorio.py — Ambulatório (agenda + atendimento).
"""

from datetime import date, datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, NumberRange, Optional

from ..extensions import db
from ..models.ambulatorio import (
    AgendaAmbulatorio,
    ConsultaAmbulatorial,
    DiaSemana,
    StatusConsulta,
    TipoConsulta,
)
from ..models.paciente import Paciente
from ..models.usuario import TipoPerfil, Usuario
from ..utils.authz import requer_permissao

bp = Blueprint("ambulatorio", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gerar_numero_consulta() -> str:
    agora = datetime.now()
    ultimo = db.session.query(db.func.max(ConsultaAmbulatorial.id)).scalar() or 0
    return f"AMB{agora.strftime('%Y%m%d')}{(ultimo + 1):04d}"


def _medicos_choices():
    medicos = Usuario.query.join(Usuario.perfil).filter(
        Usuario.perfil.has(tipo=TipoPerfil.MEDICO)
    ).order_by(Usuario.nome).all()
    return [("", "Selecione o médico...")] + [(str(m.id), m.nome) for m in medicos]


# ---------------------------------------------------------------------------
# Formulários
# ---------------------------------------------------------------------------

class AgendaForm(FlaskForm):
    medico_id = SelectField("Médico *", validators=[DataRequired()], choices=[])
    especialidade = StringField("Especialidade *", validators=[DataRequired()])
    dia_semana = SelectField("Dia da semana *", validators=[DataRequired()], choices=[
        ("", "Selecione..."),
        ("SEGUNDA", "Segunda-feira"), ("TERCA", "Terça-feira"),
        ("QUARTA", "Quarta-feira"), ("QUINTA", "Quinta-feira"),
        ("SEXTA", "Sexta-feira"), ("SABADO", "Sábado"), ("DOMINGO", "Domingo"),
    ])
    hora_inicio = TimeField("Início *", validators=[DataRequired()])
    hora_fim = TimeField("Fim *", validators=[DataRequired()])
    duracao_consulta_min = IntegerField(
        "Duração por consulta (min) *",
        default=20,
        validators=[DataRequired(), NumberRange(min=5, max=120)]
    )
    vagas_total = IntegerField(
        "Total de vagas *",
        default=10,
        validators=[DataRequired(), NumberRange(min=1, max=100)]
    )
    vagas_reserva = IntegerField(
        "Vagas de reserva (urgência)",
        default=2,
        validators=[Optional(), NumberRange(min=0, max=20)]
    )
    local = StringField("Local / consultório", validators=[Optional()])
    observacoes = StringField("Observações", validators=[Optional()])
    submit = SubmitField("Salvar agenda")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.medico_id.choices = _medicos_choices()


class AgendamentoForm(FlaskForm):
    paciente_id = HiddenField("Paciente", validators=[DataRequired()])
    medico_id = SelectField("Médico *", validators=[DataRequired()], choices=[])
    especialidade = StringField("Especialidade *", validators=[DataRequired()])
    data = DateField("Data *", validators=[DataRequired()])
    horario = TimeField("Horário *", validators=[DataRequired()])
    tipo = SelectField("Tipo de consulta", choices=[
        ("PRIMEIRA_VEZ", "Primeira vez"),
        ("RETORNO", "Retorno"),
        ("URGENCIA", "Urgência"),
        ("PROCEDIMENTO", "Procedimento"),
    ], validators=[DataRequired()])
    observacoes_agendamento = StringField("Observações", validators=[Optional()])
    submit = SubmitField("Confirmar agendamento")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.medico_id.choices = _medicos_choices()


class ConsultaForm(FlaskForm):
    anamnese = TextAreaField("Anamnese", validators=[Optional()])
    exame_fisico = TextAreaField("Exame físico", validators=[Optional()])
    hipotese_diagnostica = StringField("Hipótese diagnóstica", validators=[Optional()])
    cid10_principal = StringField("CID-10 principal", validators=[Optional()])
    cid10_secundario = StringField("CID-10 secundário", validators=[Optional()])
    conduta = TextAreaField("Conduta", validators=[Optional()])
    prescricao = TextAreaField("Receituário / Prescrição", validators=[Optional()])

    # Sinais vitais
    pressao_sistolica = IntegerField("PAS (mmHg)", validators=[Optional(), NumberRange(0, 300)])
    pressao_diastolica = IntegerField("PAD (mmHg)", validators=[Optional(), NumberRange(0, 200)])
    frequencia_cardiaca = IntegerField("FC (bpm)", validators=[Optional(), NumberRange(0, 300)])
    temperatura = DecimalField("Temperatura (°C)", validators=[Optional()], places=1)
    peso = DecimalField("Peso (kg)", validators=[Optional()], places=1)
    altura = DecimalField("Altura (m)", validators=[Optional()], places=2)

    retorno_dias = IntegerField(
        "Retorno em (dias)",
        validators=[Optional(), NumberRange(min=1, max=365)]
    )
    submit = SubmitField("Finalizar consulta")


# ---------------------------------------------------------------------------
# Rotas — Agenda
# ---------------------------------------------------------------------------

@bp.route("/")
@login_required
@requer_permissao("ambulatorio.ver")
def agenda():
    """Painel da agenda — consultas do dia."""
    hoje = date.today()
    data_str = request.args.get("data", hoje.isoformat())
    try:
        data_sel = date.fromisoformat(data_str)
    except ValueError:
        data_sel = hoje

    consultas = ConsultaAmbulatorial.query.filter(
        ConsultaAmbulatorial.data == data_sel,
        ConsultaAmbulatorial.status != StatusConsulta.CANCELADA,
    ).order_by(ConsultaAmbulatorial.horario).all()

    return render_template(
        "ambulatorio/agenda.html",
        consultas=consultas,
        data_sel=data_sel,
        hoje=hoje,
    )


@bp.route("/agendas")
@login_required
@requer_permissao("ambulatorio.ver")
def listar_agendas():
    """Lista de grades de agenda configuradas."""
    agendas = AgendaAmbulatorio.query.filter_by(ativo=True).order_by(
        AgendaAmbulatorio.dia_semana, AgendaAmbulatorio.hora_inicio
    ).all()
    return render_template("ambulatorio/agendas.html", agendas=agendas)


@bp.route("/agendas/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("ambulatorio.agendar")
def nova_agenda():
    form = AgendaForm()
    if form.validate_on_submit():
        agenda = AgendaAmbulatorio(
            medico_id=int(form.medico_id.data),
            especialidade=form.especialidade.data,
            dia_semana=DiaSemana[form.dia_semana.data],
            hora_inicio=form.hora_inicio.data,
            hora_fim=form.hora_fim.data,
            duracao_consulta_min=form.duracao_consulta_min.data,
            vagas_total=form.vagas_total.data,
            vagas_reserva=form.vagas_reserva.data or 0,
            local=form.local.data,
            observacoes=form.observacoes.data,
        )
        db.session.add(agenda)
        db.session.commit()
        flash("Agenda configurada com sucesso.", "success")
        return redirect(url_for("ambulatorio.listar_agendas"))

    return render_template("ambulatorio/form_agenda.html", form=form)


# ---------------------------------------------------------------------------
# Rotas — Consultas
# ---------------------------------------------------------------------------

@bp.route("/agendar", methods=["GET", "POST"])
@login_required
@requer_permissao("ambulatorio.agendar")
def agendar():
    """Agendamento de nova consulta."""
    form = AgendamentoForm()

    # Pre-preenche paciente via GET
    paciente_id = request.args.get("paciente_id")
    paciente = None
    if paciente_id:
        paciente = Paciente.query.get(int(paciente_id))
        if paciente:
            form.paciente_id.data = str(paciente.id)

    if form.validate_on_submit():
        paciente = db.get_or_404(Paciente, int(form.paciente_id.data))
        consulta = ConsultaAmbulatorial(
            numero=_gerar_numero_consulta(),
            paciente_id=paciente.id,
            medico_id=int(form.medico_id.data),
            especialidade=form.especialidade.data,
            data=form.data.data,
            horario=form.horario.data,
            tipo=TipoConsulta[form.tipo.data],
            status=StatusConsulta.AGENDADA,
            agendado_por_id=current_user.id,
            observacoes_agendamento=form.observacoes_agendamento.data,
        )
        db.session.add(consulta)
        db.session.commit()

        flash(
            f"Consulta {consulta.numero} agendada para "
            f"{paciente.nome_exibicao} em {consulta.data.strftime('%d/%m/%Y')} às "
            f"{consulta.horario.strftime('%H:%M')}.",
            "success"
        )
        return redirect(url_for("ambulatorio.agenda"))

    return render_template(
        "ambulatorio/agendar.html",
        form=form,
        paciente=paciente
    )


@bp.route("/consulta/<int:id>", methods=["GET", "POST"])
@login_required
@requer_permissao("ambulatorio.atender")
def consulta(id: int):
    """Atendimento da consulta pelo médico."""
    c = db.get_or_404(ConsultaAmbulatorial, id)
    form = ConsultaForm(obj=c)

    if form.validate_on_submit():
        if not c.inicio_atendimento_em:
            c.inicio_atendimento_em = datetime.now(timezone.utc)
        c.medico_id = current_user.id
        c.status = StatusConsulta.EM_ATENDIMENTO
        c.anamnese = form.anamnese.data
        c.exame_fisico = form.exame_fisico.data
        c.hipotese_diagnostica = form.hipotese_diagnostica.data
        c.cid10_principal = form.cid10_principal.data
        c.cid10_secundario = form.cid10_secundario.data
        c.conduta = form.conduta.data
        c.prescricao = form.prescricao.data
        c.pressao_sistolica = form.pressao_sistolica.data
        c.pressao_diastolica = form.pressao_diastolica.data
        c.frequencia_cardiaca = form.frequencia_cardiaca.data
        c.temperatura = form.temperatura.data
        c.peso = form.peso.data
        c.altura = form.altura.data
        c.retorno_dias = form.retorno_dias.data
        db.session.commit()
        flash("Consulta salva.", "success")
        return redirect(url_for("ambulatorio.consulta", id=id))

    return render_template("ambulatorio/consulta.html", form=form, consulta=c)


@bp.route("/consulta/<int:id>/finalizar", methods=["POST"])
@login_required
@requer_permissao("ambulatorio.atender")
def finalizar_consulta(id: int):
    """Finaliza (encerra) o atendimento da consulta."""
    c = db.get_or_404(ConsultaAmbulatorial, id)
    c.fim_atendimento_em = datetime.now(timezone.utc)
    c.status = StatusConsulta.REALIZADA
    db.session.commit()
    flash(f"Consulta {c.numero} finalizada.", "success")
    return redirect(url_for("ambulatorio.agenda"))


@bp.route("/consulta/<int:id>/cancelar", methods=["POST"])
@login_required
@requer_permissao("ambulatorio.agendar")
def cancelar_consulta(id: int):
    """Cancela uma consulta agendada."""
    c = db.get_or_404(ConsultaAmbulatorial, id)
    c.status = StatusConsulta.CANCELADA
    db.session.commit()
    flash(f"Consulta {c.numero} cancelada.", "warning")
    return redirect(url_for("ambulatorio.agenda"))
