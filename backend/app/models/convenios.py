"""
models/convenios.py — Faturamento de convênios (saúde suplementar).

Convênios, tabela CBHPM/TUSS e guias de consulta/internação (padrão TISS).
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoGuia(enum.Enum):
    CONSULTA = "consulta"
    SP_SADT = "SP/SADT"          # serviços profissionais / apoio diagnóstico
    INTERNACAO = "internação"
    HONORARIO = "honorário"


class StatusGuia(enum.Enum):
    ABERTA = "aberta"
    ENVIADA = "enviada"
    AUTORIZADA = "autorizada"
    GLOSADA = "glosada"
    PAGA = "paga"
    NEGADA = "negada"


class Convenio(db.Model):
    """Convênio / operadora de saúde."""
    __tablename__ = "convenios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False, unique=True, index=True)
    registro_ans = db.Column(db.String(20), nullable=True)   # registro na ANS
    cnpj = db.Column(db.String(18), nullable=True)
    contato = db.Column(db.String(150), nullable=True)
    tabela_preco = db.Column(db.String(50), nullable=True)   # ex: CBHPM 2020
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Convenio {self.nome}>"


class ProcedimentoCBHPM(db.Model):
    """Procedimento da tabela CBHPM/TUSS (saúde suplementar)."""
    __tablename__ = "procedimentos_cbhpm"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(15), unique=True, nullable=False, index=True)  # código TUSS
    nome = db.Column(db.String(300), nullable=False)
    porte = db.Column(db.String(20), nullable=True)
    valor_referencia = db.Column(db.Numeric(12, 2), default=0)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<ProcedimentoCBHPM {self.codigo}>"


class GuiaConvenio(db.Model):
    """Guia de convênio (padrão TISS simplificado)."""
    __tablename__ = "guias_convenio"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    tipo = db.Column(db.Enum(TipoGuia), nullable=False, index=True)
    convenio_id = db.Column(db.Integer, db.ForeignKey("convenios.id"), nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)

    numero_carteirinha = db.Column(db.String(50), nullable=True)
    senha_autorizacao = db.Column(db.String(50), nullable=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey("consultas_ambulatoriais.id"), nullable=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=True)

    valor_total = db.Column(db.Numeric(12, 2), default=0)
    valor_glosado = db.Column(db.Numeric(12, 2), default=0)
    status = db.Column(db.Enum(StatusGuia), default=StatusGuia.ABERTA, nullable=False, index=True)
    observacoes = db.Column(db.Text, nullable=True)

    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    convenio = db.relationship("Convenio", foreign_keys=[convenio_id])
    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])
    itens = db.relationship("ItemGuiaConvenio", back_populates="guia", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GuiaConvenio {self.numero} — {self.status.value}>"


class ItemGuiaConvenio(db.Model):
    __tablename__ = "itens_guia_convenio"

    id = db.Column(db.Integer, primary_key=True)
    guia_id = db.Column(db.Integer, db.ForeignKey("guias_convenio.id"), nullable=False, index=True)
    procedimento_id = db.Column(db.Integer, db.ForeignKey("procedimentos_cbhpm.id"), nullable=True)
    codigo_procedimento = db.Column(db.String(15), nullable=False)
    descricao = db.Column(db.String(300), nullable=True)
    quantidade = db.Column(db.Integer, default=1)
    valor_unitario = db.Column(db.Numeric(12, 2), default=0)

    guia = db.relationship("GuiaConvenio", back_populates="itens")
    procedimento = db.relationship("ProcedimentoCBHPM", foreign_keys=[procedimento_id])

    @property
    def valor_total(self):
        return (self.valor_unitario or 0) * (self.quantidade or 0)
