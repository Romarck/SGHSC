"""
models/compras.py — Módulo de Compras.

Fluxo: solicitação → cotação → pedido de compra → recebimento (alimenta estoque).
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class StatusSolicitacaoCompra(enum.Enum):
    ABERTA = "aberta"
    EM_COTACAO = "em cotação"
    APROVADA = "aprovada"
    PEDIDO_EMITIDO = "pedido emitido"
    RECEBIDA = "recebida"
    CANCELADA = "cancelada"


class StatusPedido(enum.Enum):
    EMITIDO = "emitido"
    PARCIAL = "recebido parcial"
    RECEBIDO = "recebido"
    CANCELADO = "cancelado"


class Fornecedor(db.Model):
    """Fornecedor de produtos/serviços."""
    __tablename__ = "fornecedores"

    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(200), nullable=False, index=True)
    nome_fantasia = db.Column(db.String(200), nullable=True)
    cnpj = db.Column(db.String(18), unique=True, nullable=True, index=True)
    contato = db.Column(db.String(150), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Fornecedor {self.razao_social}>"


class SolicitacaoCompra(db.Model):
    """Solicitação de compra (originada por falta de estoque ou demanda)."""
    __tablename__ = "solicitacoes_compra"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    solicitante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    justificativa = db.Column(db.String(500), nullable=True)
    status = db.Column(db.Enum(StatusSolicitacaoCompra), default=StatusSolicitacaoCompra.ABERTA, nullable=False, index=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    solicitante = db.relationship("Usuario", foreign_keys=[solicitante_id])
    itens = db.relationship("ItemSolicitacaoCompra", back_populates="solicitacao", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SolicitacaoCompra {self.numero} — {self.status.value}>"


class ItemSolicitacaoCompra(db.Model):
    __tablename__ = "itens_solicitacao_compra"

    id = db.Column(db.Integer, primary_key=True)
    solicitacao_id = db.Column(db.Integer, db.ForeignKey("solicitacoes_compra.id"), nullable=False, index=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos_estoque.id"), nullable=True)
    descricao = db.Column(db.String(300), nullable=False)   # snapshot / item avulso
    quantidade = db.Column(db.Integer, nullable=False)

    solicitacao = db.relationship("SolicitacaoCompra", back_populates="itens")
    produto = db.relationship("ProdutoEstoque", foreign_keys=[produto_id])


class Cotacao(db.Model):
    """Cotação de preços de uma solicitação junto a um fornecedor."""
    __tablename__ = "cotacoes"

    id = db.Column(db.Integer, primary_key=True)
    solicitacao_id = db.Column(db.Integer, db.ForeignKey("solicitacoes_compra.id"), nullable=False, index=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("fornecedores.id"), nullable=False)
    valor_total = db.Column(db.Numeric(12, 2), nullable=True)
    prazo_entrega_dias = db.Column(db.Integer, nullable=True)
    condicao_pagamento = db.Column(db.String(100), nullable=True)
    vencedora = db.Column(db.Boolean, default=False)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    solicitacao = db.relationship("SolicitacaoCompra", foreign_keys=[solicitacao_id])
    fornecedor = db.relationship("Fornecedor", foreign_keys=[fornecedor_id])

    def __repr__(self):
        return f"<Cotacao solic={self.solicitacao_id} forn={self.fornecedor_id}>"


class PedidoCompra(db.Model):
    """Pedido de compra emitido para um fornecedor."""
    __tablename__ = "pedidos_compra"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    solicitacao_id = db.Column(db.Integer, db.ForeignKey("solicitacoes_compra.id"), nullable=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("fornecedores.id"), nullable=False)
    cotacao_id = db.Column(db.Integer, db.ForeignKey("cotacoes.id"), nullable=True)

    valor_total = db.Column(db.Numeric(12, 2), nullable=True)
    status = db.Column(db.Enum(StatusPedido), default=StatusPedido.EMITIDO, nullable=False, index=True)
    emitido_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    fornecedor = db.relationship("Fornecedor", foreign_keys=[fornecedor_id])
    itens = db.relationship("ItemPedidoCompra", back_populates="pedido", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PedidoCompra {self.numero} — {self.status.value}>"


class ItemPedidoCompra(db.Model):
    __tablename__ = "itens_pedido_compra"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos_compra.id"), nullable=False, index=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos_estoque.id"), nullable=True)
    descricao = db.Column(db.String(300), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    quantidade_recebida = db.Column(db.Integer, default=0)
    valor_unitario = db.Column(db.Numeric(12, 2), nullable=True)

    pedido = db.relationship("PedidoCompra", back_populates="itens")
    produto = db.relationship("ProdutoEstoque", foreign_keys=[produto_id])


class Recebimento(db.Model):
    """Recebimento de mercadoria de um pedido (alimenta o estoque)."""
    __tablename__ = "recebimentos"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos_compra.id"), nullable=False, index=True)
    nota_fiscal = db.Column(db.String(50), nullable=True)
    local_id = db.Column(db.Integer, db.ForeignKey("locais_estoque.id"), nullable=True)
    recebido_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    recebido_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    pedido = db.relationship("PedidoCompra", foreign_keys=[pedido_id])
    recebido_por = db.relationship("Usuario", foreign_keys=[recebido_por_id])

    def __repr__(self):
        return f"<Recebimento pedido={self.pedido_id} NF={self.nota_fiscal}>"
