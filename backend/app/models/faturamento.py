"""
models/faturamento.py — Faturamento SUS.

AIH (internação), APAC (alta complexidade) e BPA (produção ambulatorial).

NOTA: a geração dos arquivos magnéticos no layout oficial do DATASUS (SISAIH01,
BPA-MAG, etc.) depende das tabelas SIGTAP e de layout binário específico. Aqui
registramos os dados estruturados; a exportação oficial é um stub documentado
a ser completado com as tabelas oficiais do DATASUS.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoProducao(enum.Enum):
    AIH = "AIH"       # internação
    APAC = "APAC"     # procedimento de alta complexidade
    BPA_I = "BPA-I"   # boletim individualizado
    BPA_C = "BPA-C"   # boletim consolidado


class StatusFaturamento(enum.Enum):
    ABERTA = "aberta"
    FECHADA = "fechada"
    EXPORTADA = "exportada"
    GLOSADA = "glosada"
    PAGA = "paga"


class ProcedimentoSIGTAP(db.Model):
    """
    Procedimento da tabela SIGTAP (SUS).
    Tabela de referência — importada periodicamente do DATASUS.
    """
    __tablename__ = "procedimentos_sigtap"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(15), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(300), nullable=False)
    complexidade = db.Column(db.String(50), nullable=True)   # baixa/média/alta
    valor_sus = db.Column(db.Numeric(12, 2), default=0)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<ProcedimentoSIGTAP {self.codigo}>"


class GuiaFaturamento(db.Model):
    """
    Guia de faturamento SUS (AIH/APAC/BPA).
    Consolida os dados estruturados para posterior exportação DATASUS.
    """
    __tablename__ = "guias_faturamento"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    tipo = db.Column(db.Enum(TipoProducao), nullable=False, index=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=True, index=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey("consultas_ambulatoriais.id"), nullable=True)

    competencia = db.Column(db.String(6), nullable=False, index=True)  # AAAAMM
    cid_principal = db.Column(db.String(10), nullable=True)
    procedimento_principal = db.Column(db.String(15), nullable=True)   # código SIGTAP
    valor_total = db.Column(db.Numeric(12, 2), default=0)

    numero_aih_apac = db.Column(db.String(20), nullable=True)  # nº AIH/APAC do SUS
    status = db.Column(db.Enum(StatusFaturamento), default=StatusFaturamento.ABERTA, nullable=False, index=True)
    observacoes = db.Column(db.Text, nullable=True)

    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])
    internacao = db.relationship("Internacao", foreign_keys=[internacao_id])
    itens = db.relationship("ItemGuiaFaturamento", back_populates="guia", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GuiaFaturamento {self.numero} — {self.tipo.value}>"


class ItemGuiaFaturamento(db.Model):
    """Procedimento lançado numa guia de faturamento."""
    __tablename__ = "itens_guia_faturamento"

    id = db.Column(db.Integer, primary_key=True)
    guia_id = db.Column(db.Integer, db.ForeignKey("guias_faturamento.id"), nullable=False, index=True)
    procedimento_id = db.Column(db.Integer, db.ForeignKey("procedimentos_sigtap.id"), nullable=True)
    codigo_procedimento = db.Column(db.String(15), nullable=False)   # snapshot
    descricao = db.Column(db.String(300), nullable=True)
    quantidade = db.Column(db.Integer, default=1)
    valor_unitario = db.Column(db.Numeric(12, 2), default=0)

    guia = db.relationship("GuiaFaturamento", back_populates="itens")
    procedimento = db.relationship("ProcedimentoSIGTAP", foreign_keys=[procedimento_id])

    @property
    def valor_total(self):
        return (self.valor_unitario or 0) * (self.quantidade or 0)
