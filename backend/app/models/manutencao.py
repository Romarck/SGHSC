"""
models/manutencao.py — Manutenção predial e de equipamentos.

Ordens de serviço (abertura → execução → encerramento) e manutenções preventivas.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoManutencao(enum.Enum):
    CORRETIVA = "corretiva"
    PREVENTIVA = "preventiva"
    PREDITIVA = "preditiva"
    INSTALACAO = "instalação"


class PrioridadeOS(enum.Enum):
    BAIXA = "baixa"
    MEDIA = "média"
    ALTA = "alta"
    URGENTE = "urgente"


class StatusOS(enum.Enum):
    ABERTA = "aberta"
    EM_EXECUCAO = "em execução"
    AGUARDANDO_PECA = "aguardando peça"
    CONCLUIDA = "concluída"
    CANCELADA = "cancelada"


class OrdemServico(db.Model):
    """Ordem de serviço de manutenção."""
    __tablename__ = "ordens_servico"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)

    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.Enum(TipoManutencao), default=TipoManutencao.CORRETIVA, nullable=False)
    prioridade = db.Column(db.Enum(PrioridadeOS), default=PrioridadeOS.MEDIA, nullable=False, index=True)
    status = db.Column(db.Enum(StatusOS), default=StatusOS.ABERTA, nullable=False, index=True)

    local = db.Column(db.String(150), nullable=True)   # setor/sala
    bem_id = db.Column(db.Integer, db.ForeignKey("bens_patrimoniais.id"), nullable=True)

    solicitante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    executor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    aberta_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    iniciada_em = db.Column(db.DateTime(timezone=True), nullable=True)
    concluida_em = db.Column(db.DateTime(timezone=True), nullable=True)

    solucao = db.Column(db.Text, nullable=True)
    custo = db.Column(db.Numeric(12, 2), nullable=True)

    # Preventiva: recorrência
    preventiva_intervalo_dias = db.Column(db.Integer, nullable=True)
    proxima_preventiva = db.Column(db.Date, nullable=True)

    solicitante = db.relationship("Usuario", foreign_keys=[solicitante_id])
    executor = db.relationship("Usuario", foreign_keys=[executor_id])
    bem = db.relationship("BemPatrimonial", foreign_keys=[bem_id])

    @property
    def cor_status(self) -> str:
        cores = {
            StatusOS.ABERTA: "secondary",
            StatusOS.EM_EXECUCAO: "primary",
            StatusOS.AGUARDANDO_PECA: "warning",
            StatusOS.CONCLUIDA: "success",
            StatusOS.CANCELADA: "dark",
        }
        return cores.get(self.status, "secondary")

    def __repr__(self):
        return f"<OrdemServico {self.numero} — {self.status.value}>"
