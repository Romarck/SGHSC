"""
models/cirurgia.py — Módulo de Centro Cirúrgico.

Fluxo: solicitação cirúrgica → agendamento/escala → sala (fluxo do paciente)
       → descrição cirúrgica (nota de sala).
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoCirurgia(enum.Enum):
    ELETIVA = "eletiva"
    URGENCIA = "urgência"
    EMERGENCIA = "emergência"


class PorteCirurgico(enum.Enum):
    PEQUENO = "pequeno"
    MEDIO = "médio"
    GRANDE = "grande"
    ESPECIAL = "especial"


class TipoAnestesia(enum.Enum):
    GERAL = "geral"
    RAQUIDIANA = "raquidiana"
    PERIDURAL = "peridural"
    LOCAL = "local"
    SEDACAO = "sedação"
    BLOQUEIO = "bloqueio regional"


class StatusCirurgia(enum.Enum):
    SOLICITADA = "solicitada"
    AGENDADA = "agendada"
    CONFIRMADA = "confirmada"
    EM_PREPARO = "em preparo"
    EM_ANDAMENTO = "em andamento"
    RECUPERACAO = "recuperação"
    CONCLUIDA = "concluída"
    CANCELADA = "cancelada"
    SUSPENSA = "suspensa"


class SalaCirurgica(db.Model):
    """Sala do centro cirúrgico."""
    __tablename__ = "salas_cirurgicas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(200), nullable=True)
    ativa = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<SalaCirurgica {self.nome}>"


class Cirurgia(db.Model):
    """
    Procedimento cirúrgico — cobre da solicitação à conclusão.
    Consolida solicitação, agendamento e descrição num único ciclo.
    """
    __tablename__ = "cirurgias"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=True)
    cirurgiao_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    solicitante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    # Solicitação
    procedimento = db.Column(db.String(300), nullable=False)
    codigo_procedimento = db.Column(db.String(20), nullable=True)   # SIGTAP/TUSS
    tipo = db.Column(db.Enum(TipoCirurgia), default=TipoCirurgia.ELETIVA, nullable=False)
    porte = db.Column(db.Enum(PorteCirurgico), nullable=True)
    tipo_anestesia = db.Column(db.Enum(TipoAnestesia), nullable=True)
    cid10 = db.Column(db.String(10), nullable=True)
    indicacao = db.Column(db.String(500), nullable=True)
    lateralidade = db.Column(db.String(20), nullable=True)          # direito/esquerdo/bilateral

    # Agendamento
    sala_id = db.Column(db.Integer, db.ForeignKey("salas_cirurgicas.id"), nullable=True)
    data_agendada = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    duracao_estimada_min = db.Column(db.Integer, nullable=True)
    anestesista_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    status = db.Column(
        db.Enum(StatusCirurgia), default=StatusCirurgia.SOLICITADA, nullable=False, index=True
    )

    # Execução / fluxo de sala
    entrada_sala_em = db.Column(db.DateTime(timezone=True), nullable=True)
    inicio_cirurgia_em = db.Column(db.DateTime(timezone=True), nullable=True)
    fim_cirurgia_em = db.Column(db.DateTime(timezone=True), nullable=True)
    saida_sala_em = db.Column(db.DateTime(timezone=True), nullable=True)

    # Descrição cirúrgica (nota de sala)
    descricao_cirurgica = db.Column(db.Text, nullable=True)
    achados = db.Column(db.Text, nullable=True)
    procedimento_realizado = db.Column(db.Text, nullable=True)
    intercorrencias = db.Column(db.Text, nullable=True)
    equipe = db.Column(db.Text, nullable=True)          # instrumentador, auxiliares...
    material_utilizado = db.Column(db.Text, nullable=True)

    motivo_cancelamento = db.Column(db.String(300), nullable=True)

    # Assinatura da descrição cirúrgica
    descricao_assinada = db.Column(db.Boolean, default=False)
    documento_assinado_id = db.Column(
        db.Integer, db.ForeignKey("documentos_assinados.id"), nullable=True
    )

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])
    internacao = db.relationship("Internacao", foreign_keys=[internacao_id])
    cirurgiao = db.relationship("Usuario", foreign_keys=[cirurgiao_id])
    solicitante = db.relationship("Usuario", foreign_keys=[solicitante_id])
    anestesista = db.relationship("Usuario", foreign_keys=[anestesista_id])
    sala = db.relationship("SalaCirurgica", foreign_keys=[sala_id])

    @property
    def duracao_real_min(self):
        if self.inicio_cirurgia_em and self.fim_cirurgia_em:
            return int((self.fim_cirurgia_em - self.inicio_cirurgia_em).total_seconds() // 60)
        return None

    @property
    def cor_status(self) -> str:
        cores = {
            StatusCirurgia.SOLICITADA: "secondary",
            StatusCirurgia.AGENDADA: "info",
            StatusCirurgia.CONFIRMADA: "primary",
            StatusCirurgia.EM_PREPARO: "warning",
            StatusCirurgia.EM_ANDAMENTO: "danger",
            StatusCirurgia.RECUPERACAO: "warning",
            StatusCirurgia.CONCLUIDA: "success",
            StatusCirurgia.CANCELADA: "dark",
            StatusCirurgia.SUSPENSA: "dark",
        }
        return cores.get(self.status, "secondary")

    def __repr__(self):
        return f"<Cirurgia {self.numero} — {self.procedimento[:30]}>"
