"""
models/nutricao.py — Módulo de Nutrição.

Prescrição dietética da nutricionista e mapa de dietas por enfermaria/andar.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoDieta(enum.Enum):
    LIVRE = "livre"
    BRANDA = "branda"
    PASTOSA = "pastosa"
    LIQUIDA = "líquida"
    LIQUIDA_RESTRITA = "líquida restrita"
    LEVE = "leve"
    ZERO_JEJUM = "zero / jejum"
    ENTERAL = "enteral"
    PARENTERAL = "parenteral"
    HIPOSSODICA = "hipossódica"
    DIABETICO = "para diabético"
    HIPOPROTEICA = "hipoproteica"
    HIPERPROTEICA = "hiperproteica"
    INFANTIL = "infantil"
    OUTRA = "outra"


class ConsistenciaDieta(enum.Enum):
    NORMAL = "normal"
    BRANDA = "branda"
    PASTOSA = "pastosa"
    LIQUIDA = "líquida"
    LIQUIDA_COMPLETA = "líquida completa"


class ViaAlimentacao(enum.Enum):
    ORAL = "oral"
    SONDA_NASOGASTRICA = "sonda nasogástrica"
    SONDA_NASOENTERAL = "sonda nasoenteral"
    GASTROSTOMIA = "gastrostomia"
    JEJUNOSTOMIA = "jejunostomia"
    PARENTERAL = "parenteral"


class StatusPrescricaoDieta(enum.Enum):
    ATIVA = "ativa"
    SUSPENSA = "suspensa"
    ENCERRADA = "encerrada"


class PrescricaoDietetica(db.Model):
    """
    Prescrição dietética para um paciente internado.
    Feita pela nutricionista; alimenta o mapa de dietas.
    """
    __tablename__ = "prescricoes_dieteticas"

    id = db.Column(db.Integer, primary_key=True)
    internacao_id = db.Column(
        db.Integer, db.ForeignKey("internacoes.id"), nullable=False, index=True
    )
    nutricionista_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    data_prescricao = db.Column(db.Date, nullable=False)
    tipo_dieta = db.Column(db.Enum(TipoDieta), nullable=False)
    consistencia = db.Column(db.Enum(ConsistenciaDieta), nullable=True)
    via = db.Column(db.Enum(ViaAlimentacao), default=ViaAlimentacao.ORAL, nullable=False)

    valor_calorico = db.Column(db.Integer, nullable=True)     # kcal/dia
    fracionamento = db.Column(db.String(100), nullable=True)  # nº de refeições/dia
    restricoes = db.Column(db.String(300), nullable=True)     # ex: sem lactose, sem glúten
    suplementos = db.Column(db.String(300), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    status = db.Column(
        db.Enum(StatusPrescricaoDieta),
        default=StatusPrescricaoDieta.ATIVA, nullable=False
    )

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    internacao = db.relationship("Internacao", foreign_keys=[internacao_id])
    nutricionista = db.relationship("Usuario", foreign_keys=[nutricionista_id])

    def __repr__(self):
        return f"<PrescricaoDietetica internacao={self.internacao_id} — {self.tipo_dieta.value}>"
