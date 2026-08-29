"""
models/financeiro.py — Módulo Financeiro.

Contas a pagar/receber, fluxo de caixa e categorias financeiras.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoConta(enum.Enum):
    PAGAR = "a pagar"
    RECEBER = "a receber"


class StatusConta(enum.Enum):
    ABERTA = "aberta"
    PAGA = "paga"
    RECEBIDA = "recebida"
    ATRASADA = "atrasada"
    CANCELADA = "cancelada"


class TipoLancamento(enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saída"


class CategoriaFinanceira(db.Model):
    """Categoria/plano de contas financeiro."""
    __tablename__ = "categorias_financeiras"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    tipo = db.Column(db.Enum(TipoLancamento), nullable=True)   # receita ou despesa
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<CategoriaFinanceira {self.nome}>"


class Conta(db.Model):
    """Conta a pagar ou a receber."""
    __tablename__ = "contas"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(300), nullable=False)
    tipo = db.Column(db.Enum(TipoConta), nullable=False, index=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    vencimento = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.Enum(StatusConta), default=StatusConta.ABERTA, nullable=False, index=True)

    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias_financeiras.id"), nullable=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("fornecedores.id"), nullable=True)
    pedido_compra_id = db.Column(db.Integer, db.ForeignKey("pedidos_compra.id"), nullable=True)
    convenio = db.Column(db.String(100), nullable=True)   # para contas a receber

    data_pagamento = db.Column(db.Date, nullable=True)
    valor_pago = db.Column(db.Numeric(12, 2), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    categoria = db.relationship("CategoriaFinanceira", foreign_keys=[categoria_id])
    fornecedor = db.relationship("Fornecedor", foreign_keys=[fornecedor_id])

    @property
    def atrasada(self) -> bool:
        from datetime import date
        return self.status == StatusConta.ABERTA and self.vencimento < date.today()

    def __repr__(self):
        return f"<Conta {self.tipo.value} R${self.valor} — {self.status.value}>"


class LancamentoCaixa(db.Model):
    """Lançamento no fluxo de caixa (entrada/saída efetiva)."""
    __tablename__ = "lancamentos_caixa"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(300), nullable=False)
    tipo = db.Column(db.Enum(TipoLancamento), nullable=False, index=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    data = db.Column(db.Date, nullable=False, index=True)

    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias_financeiras.id"), nullable=True)
    conta_id = db.Column(db.Integer, db.ForeignKey("contas.id"), nullable=True)

    registrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    categoria = db.relationship("CategoriaFinanceira", foreign_keys=[categoria_id])
    registrado_por = db.relationship("Usuario", foreign_keys=[registrado_por_id])

    def __repr__(self):
        return f"<LancamentoCaixa {self.tipo.value} R${self.valor}>"
