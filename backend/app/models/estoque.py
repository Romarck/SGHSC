"""
models/estoque.py — Almoxarifado / Estoque de materiais e medicamentos.

Controle de produtos, saldos por local, requisições, movimentações e inventário.
Distinto da farmácia (dispensação clínica): aqui é o estoque geral da instituição.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class CategoriaProduto(enum.Enum):
    MEDICAMENTO = "medicamento"
    MATERIAL_MEDICO = "material médico-hospitalar"
    MATERIAL_LIMPEZA = "material de limpeza"
    GENERO_ALIMENTICIO = "gênero alimentício"
    EXPEDIENTE = "material de expediente"
    ROUPARIA = "rouparia"
    OUTRO = "outro"


class UnidadeMedida(enum.Enum):
    UNIDADE = "UN"
    CAIXA = "CX"
    FRASCO = "FR"
    AMPOLA = "AMP"
    PACOTE = "PCT"
    LITRO = "L"
    MILILITRO = "mL"
    GRAMA = "g"
    QUILO = "KG"
    METRO = "M"
    PAR = "PAR"


class TipoMovimento(enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saída"
    TRANSFERENCIA = "transferência"
    AJUSTE = "ajuste"
    PERDA = "perda"
    INVENTARIO = "inventário"


class StatusRequisicao(enum.Enum):
    PENDENTE = "pendente"
    ATENDIDA = "atendida"
    PARCIAL = "parcial"
    CANCELADA = "cancelada"


class StatusInventario(enum.Enum):
    ABERTO = "aberto"
    EM_CONTAGEM = "em contagem"
    FECHADO = "fechado"


class LocalEstoque(db.Model):
    """Local físico de estoque (almoxarifado central, subalmoxarifados, setores)."""
    __tablename__ = "locais_estoque"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.String(200), nullable=True)
    principal = db.Column(db.Boolean, default=False)   # almoxarifado central
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<LocalEstoque {self.nome}>"


class ProdutoEstoque(db.Model):
    """Produto cadastrado no almoxarifado."""
    __tablename__ = "produtos_estoque"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(200), nullable=False, index=True)
    descricao = db.Column(db.String(300), nullable=True)
    categoria = db.Column(db.Enum(CategoriaProduto), nullable=False)
    unidade = db.Column(db.Enum(UnidadeMedida), default=UnidadeMedida.UNIDADE, nullable=False)

    estoque_minimo = db.Column(db.Integer, default=0)   # ponto de pedido
    estoque_maximo = db.Column(db.Integer, nullable=True)
    valor_medio = db.Column(db.Numeric(12, 2), default=0)  # custo médio

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    saldos = db.relationship("SaldoEstoque", back_populates="produto", cascade="all, delete-orphan")

    @property
    def estoque_total(self) -> int:
        return sum(s.quantidade for s in self.saldos)

    @property
    def abaixo_minimo(self) -> bool:
        return self.estoque_total <= (self.estoque_minimo or 0)

    def __repr__(self):
        return f"<ProdutoEstoque {self.codigo} — {self.nome}>"


class SaldoEstoque(db.Model):
    """Saldo de um produto em um local específico."""
    __tablename__ = "saldos_estoque"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos_estoque.id"), nullable=False, index=True)
    local_id = db.Column(db.Integer, db.ForeignKey("locais_estoque.id"), nullable=False, index=True)
    quantidade = db.Column(db.Integer, default=0, nullable=False)

    produto = db.relationship("ProdutoEstoque", back_populates="saldos")
    local = db.relationship("LocalEstoque", foreign_keys=[local_id])

    __table_args__ = (db.UniqueConstraint("produto_id", "local_id", name="uq_saldo_produto_local"),)


class MovimentoEstoqueAlmox(db.Model):
    """Movimentação de estoque do almoxarifado (auditoria completa)."""
    __tablename__ = "movimentos_estoque_almox"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos_estoque.id"), nullable=False, index=True)
    local_id = db.Column(db.Integer, db.ForeignKey("locais_estoque.id"), nullable=False)
    local_destino_id = db.Column(db.Integer, db.ForeignKey("locais_estoque.id"), nullable=True)
    tipo = db.Column(db.Enum(TipoMovimento), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)   # +entrada / -saída
    valor_unitario = db.Column(db.Numeric(12, 2), nullable=True)
    motivo = db.Column(db.String(300), nullable=True)
    requisicao_id = db.Column(db.Integer, db.ForeignKey("requisicoes_material.id"), nullable=True)

    responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    registrado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    produto = db.relationship("ProdutoEstoque", foreign_keys=[produto_id])
    local = db.relationship("LocalEstoque", foreign_keys=[local_id])
    responsavel = db.relationship("Usuario", foreign_keys=[responsavel_id])

    def __repr__(self):
        return f"<MovimentoEstoqueAlmox {self.tipo.value} {self.quantidade}>"


class RequisicaoMaterial(db.Model):
    """Requisição de material de um setor ao almoxarifado."""
    __tablename__ = "requisicoes_material"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    setor_solicitante = db.Column(db.String(100), nullable=True)
    solicitante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    local_atendimento_id = db.Column(db.Integer, db.ForeignKey("locais_estoque.id"), nullable=True)

    status = db.Column(db.Enum(StatusRequisicao), default=StatusRequisicao.PENDENTE, nullable=False, index=True)
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    atendida_em = db.Column(db.DateTime(timezone=True), nullable=True)
    atendida_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    solicitante = db.relationship("Usuario", foreign_keys=[solicitante_id])
    itens = db.relationship("ItemRequisicao", back_populates="requisicao", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RequisicaoMaterial {self.numero} — {self.status.value}>"


class ItemRequisicao(db.Model):
    """Item de uma requisição de material."""
    __tablename__ = "itens_requisicao"

    id = db.Column(db.Integer, primary_key=True)
    requisicao_id = db.Column(db.Integer, db.ForeignKey("requisicoes_material.id"), nullable=False, index=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos_estoque.id"), nullable=False)
    quantidade_solicitada = db.Column(db.Integer, nullable=False)
    quantidade_atendida = db.Column(db.Integer, default=0)

    requisicao = db.relationship("RequisicaoMaterial", back_populates="itens")
    produto = db.relationship("ProdutoEstoque", foreign_keys=[produto_id])


class Inventario(db.Model):
    """Inventário de estoque (contagem física por local)."""
    __tablename__ = "inventarios"

    id = db.Column(db.Integer, primary_key=True)
    local_id = db.Column(db.Integer, db.ForeignKey("locais_estoque.id"), nullable=False)
    status = db.Column(db.Enum(StatusInventario), default=StatusInventario.ABERTO, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    fechado_em = db.Column(db.DateTime(timezone=True), nullable=True)

    local = db.relationship("LocalEstoque", foreign_keys=[local_id])
    responsavel = db.relationship("Usuario", foreign_keys=[responsavel_id])
    itens = db.relationship("ItemInventario", back_populates="inventario", cascade="all, delete-orphan")


class ItemInventario(db.Model):
    """Item contado num inventário (saldo do sistema x contagem física)."""
    __tablename__ = "itens_inventario"

    id = db.Column(db.Integer, primary_key=True)
    inventario_id = db.Column(db.Integer, db.ForeignKey("inventarios.id"), nullable=False, index=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos_estoque.id"), nullable=False)
    saldo_sistema = db.Column(db.Integer, default=0)
    contagem_fisica = db.Column(db.Integer, nullable=True)

    inventario = db.relationship("Inventario", back_populates="itens")
    produto = db.relationship("ProdutoEstoque", foreign_keys=[produto_id])

    @property
    def divergencia(self):
        if self.contagem_fisica is None:
            return None
        return self.contagem_fisica - self.saldo_sistema
