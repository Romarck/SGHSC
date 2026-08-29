"""
models/ambulatorio.py — Módulo de Ambulatório.

Fluxo: configuração de agenda → marcação de consulta → atendimento → alta/retorno
"""

import enum
from datetime import datetime, timezone

from ..extensions import db

# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------

class StatusConsulta(enum.Enum):
    AGENDADA = "agendada"
    CONFIRMADA = "confirmada"
    EM_ATENDIMENTO = "em atendimento"
    REALIZADA = "realizada"
    FALTA = "falta"
    CANCELADA = "cancelada"
    REMARCADA = "remarcada"


class TipoConsulta(enum.Enum):
    PRIMEIRA_VEZ = "primeira vez"
    RETORNO = "retorno"
    URGENCIA = "urgência"
    PROCEDIMENTO = "procedimento"


class DiaSemana(enum.Enum):
    SEGUNDA = 0
    TERCA = 1
    QUARTA = 2
    QUINTA = 3
    SEXTA = 4
    SABADO = 5
    DOMINGO = 6


# ---------------------------------------------------------------------------
# Modelo: AgendaAmbulatorio
# ---------------------------------------------------------------------------

class AgendaAmbulatorio(db.Model):
    """
    Grade de agenda ambulatorial de um médico/especialidade.
    Define os horários disponíveis em cada dia da semana.
    """
    __tablename__ = "agendas_ambulatorio"

    id = db.Column(db.Integer, primary_key=True)
    medico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    especialidade = db.Column(db.String(100), nullable=False)
    dia_semana = db.Column(db.Enum(DiaSemana), nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)
    duracao_consulta_min = db.Column(db.Integer, default=20, nullable=False)  # minutos por consulta
    vagas_total = db.Column(db.Integer, default=10, nullable=False)
    vagas_reserva = db.Column(db.Integer, default=2, nullable=False)  # para urgências
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    local = db.Column(db.String(100), nullable=True)   # Ex: "Consultório 1"
    observacoes = db.Column(db.String(300), nullable=True)

    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    medico = db.relationship("Usuario", foreign_keys=[medico_id])
    consultas = db.relationship("ConsultaAmbulatorial", back_populates="agenda", lazy="dynamic")

    @property
    def vagas_disponiveis_hoje(self) -> int:
        """Conta vagas livres para hoje nessa agenda."""
        from datetime import date
        hoje = date.today()
        ocupadas = self.consultas.filter(
            ConsultaAmbulatorial.data == hoje,
            ConsultaAmbulatorial.status.notin_([
                StatusConsulta.CANCELADA, StatusConsulta.FALTA
            ])
        ).count()
        return max(0, self.vagas_total - ocupadas)

    def __repr__(self):
        return f"<Agenda {self.medico_id} — {self.dia_semana.name} {self.hora_inicio}>"


# ---------------------------------------------------------------------------
# Modelo: ConsultaAmbulatorial
# ---------------------------------------------------------------------------

class ConsultaAmbulatorial(db.Model):
    """
    Consulta agendada e/ou realizada no Ambulatório.
    Vincula paciente, médico, agenda e todos os registros do atendimento.
    """
    __tablename__ = "consultas_ambulatoriais"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)

    # Vínculo
    paciente_id = db.Column(
        db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True
    )
    medico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    agenda_id = db.Column(db.Integer, db.ForeignKey("agendas_ambulatorio.id"), nullable=True)

    # Agendamento
    data = db.Column(db.Date, nullable=False, index=True)
    horario = db.Column(db.Time, nullable=False)
    tipo = db.Column(db.Enum(TipoConsulta), default=TipoConsulta.PRIMEIRA_VEZ, nullable=False)
    especialidade = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Enum(StatusConsulta), default=StatusConsulta.AGENDADA, nullable=False)
    agendado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    agendado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    observacoes_agendamento = db.Column(db.String(300), nullable=True)

    # Atendimento (preenchido pelo médico)
    inicio_atendimento_em = db.Column(db.DateTime(timezone=True), nullable=True)
    fim_atendimento_em = db.Column(db.DateTime(timezone=True), nullable=True)
    anamnese = db.Column(db.Text, nullable=True)
    exame_fisico = db.Column(db.Text, nullable=True)
    hipotese_diagnostica = db.Column(db.String(500), nullable=True)
    cid10_principal = db.Column(db.String(10), nullable=True)
    cid10_secundario = db.Column(db.String(10), nullable=True)
    conduta = db.Column(db.Text, nullable=True)
    prescricao = db.Column(db.Text, nullable=True)

    # Sinais vitais no atendimento
    pressao_sistolica = db.Column(db.Integer, nullable=True)
    pressao_diastolica = db.Column(db.Integer, nullable=True)
    frequencia_cardiaca = db.Column(db.Integer, nullable=True)
    temperatura = db.Column(db.Numeric(4, 1), nullable=True)
    peso = db.Column(db.Numeric(5, 2), nullable=True)
    altura = db.Column(db.Numeric(4, 2), nullable=True)

    # Retorno
    retorno_data = db.Column(db.Date, nullable=True)
    retorno_dias = db.Column(db.Integer, nullable=True)   # em quantos dias retornar

    # Faturamento (BPA)
    procedimento_sus = db.Column(db.String(10), nullable=True)   # Código SIGTAP
    cbo_medico = db.Column(db.String(10), nullable=True)

    # Relacionamentos
    paciente = db.relationship("Paciente", back_populates="consultas_ambulatoriais")
    medico = db.relationship("Usuario", foreign_keys=[medico_id])
    agenda = db.relationship("AgendaAmbulatorio", back_populates="consultas")
    agendado_por = db.relationship("Usuario", foreign_keys=[agendado_por_id])

    @property
    def duracao_minutos(self) -> int | None:
        if self.inicio_atendimento_em and self.fim_atendimento_em:
            delta = self.fim_atendimento_em - self.inicio_atendimento_em
            return int(delta.total_seconds() / 60)
        return None

    def __repr__(self):
        return f"<ConsultaAmbulatorial {self.numero} — {self.data}>"
