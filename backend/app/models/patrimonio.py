"""
models/patrimonio.py — Gestão de Patrimônio.

Inventário de bens/equipamentos, localização e movimentações.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class SituacaoBem(enum.Enum):
    ATIVO = "ativo"
    EM_MANUTENCAO = "em manutenção"
    BAIXADO = "baixado"
    EMPRESTADO = "emprestado"
    INSERVIVEL = "inservível"


class EstadoConservacao(enum.Enum):
    NOVO = "novo"
    BOM = "bom"
    REGULAR = "regular"
    RUIM = "ruim"
    PESSIMO = "péssimo"


class BemPatrimonial(db.Model):
    """Bem patrimonial (equipamento, mobiliário, etc.)."""
    __tablename__ = "bens_patrimoniais"

    id = db.Column(db.Integer, primary_key=True)
    numero_patrimonio = db.Column(db.String(30), unique=True, nullable=False, index=True)
    descricao = db.Column(db.String(300), nullable=False)
    categoria = db.Column(db.String(100), nullable=True)   # equipamento médico, mobiliário...
    marca = db.Column(db.String(100), nullable=True)
    modelo = db.Column(db.String(100), nullable=True)
    numero_serie = db.Column(db.String(100), nullable=True)

    localizacao = db.Column(db.String(150), nullable=True)   # setor/sala atual
    situacao = db.Column(db.Enum(SituacaoBem), default=SituacaoBem.ATIVO, nullable=False, index=True)
    estado = db.Column(db.Enum(EstadoConservacao), default=EstadoConservacao.BOM, nullable=True)

    valor_aquisicao = db.Column(db.Numeric(12, 2), nullable=True)
    data_aquisicao = db.Column(db.Date, nullable=True)
    vida_util_anos = db.Column(db.Integer, nullable=True)   # para depreciação linear

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    movimentacoes = db.relationship("MovimentacaoBem", back_populates="bem",
                                    cascade="all, delete-orphan",
                                    order_by="MovimentacaoBem.data.desc()")

    @property
    def depreciacao_anual(self):
        """Depreciação linear anual (se vida útil e valor informados)."""
        if self.valor_aquisicao and self.vida_util_anos:
            return float(self.valor_aquisicao) / self.vida_util_anos
        return None

    @property
    def valor_atual_estimado(self):
        """Valor contábil estimado pela depreciação linear."""
        if not self.valor_aquisicao or not self.vida_util_anos or not self.data_aquisicao:
            return self.valor_aquisicao
        from datetime import date
        anos = (date.today() - self.data_aquisicao).days / 365.25
        dep = self.depreciacao_anual * anos
        restante = float(self.valor_aquisicao) - dep
        return max(0.0, round(restante, 2))

    def __repr__(self):
        return f"<BemPatrimonial {self.numero_patrimonio} — {self.descricao[:30]}>"


class MovimentacaoBem(db.Model):
    """Movimentação/transferência de localização de um bem."""
    __tablename__ = "movimentacoes_bem"

    id = db.Column(db.Integer, primary_key=True)
    bem_id = db.Column(db.Integer, db.ForeignKey("bens_patrimoniais.id"), nullable=False, index=True)
    localizacao_origem = db.Column(db.String(150), nullable=True)
    localizacao_destino = db.Column(db.String(150), nullable=False)
    motivo = db.Column(db.String(300), nullable=True)
    responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    bem = db.relationship("BemPatrimonial", back_populates="movimentacoes")
    responsavel = db.relationship("Usuario", foreign_keys=[responsavel_id])
