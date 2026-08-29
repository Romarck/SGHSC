"""
models/farmacia.py — Módulo de Farmácia Hospitalar.

Dispensação vinculada à prescrição médica da internação, com controle de
estoque de farmácia e movimentações.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class FormaFarmaceutica(enum.Enum):
    COMPRIMIDO = "comprimido"
    CAPSULA = "cápsula"
    AMPOLA = "ampola"
    FRASCO = "frasco"
    FRASCO_AMPOLA = "frasco-ampola"
    BOLSA = "bolsa"
    TUBO = "tubo"
    SACHE = "sachê"
    SOLUCAO = "solução"
    POMADA = "pomada"
    SUPOSITORIO = "supositório"
    OUTRO = "outro"


class TipoMovimentoEstoque(enum.Enum):
    ENTRADA = "entrada"
    DISPENSACAO = "dispensação"
    AJUSTE = "ajuste"
    DEVOLUCAO = "devolução"
    PERDA = "perda"
    VENCIMENTO = "vencimento"
    TRANSFERENCIA = "transferência"


class StatusDispensacao(enum.Enum):
    PENDENTE = "pendente"
    DISPENSADO = "dispensado"
    PARCIAL = "parcial"
    CANCELADO = "cancelado"


# ---------------------------------------------------------------------------
# Medicamento (cadastro na farmácia)
# ---------------------------------------------------------------------------

class MedicamentoFarmacia(db.Model):
    """Medicamento/item cadastrado na farmácia hospitalar."""
    __tablename__ = "medicamentos_farmacia"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(200), nullable=False, index=True)          # nome comercial
    principio_ativo = db.Column(db.String(200), nullable=True, index=True)
    concentracao = db.Column(db.String(100), nullable=True)               # ex: 500mg
    forma = db.Column(db.Enum(FormaFarmaceutica), nullable=True)
    unidade_dispensacao = db.Column(db.String(50), nullable=True)         # comprimido, mL...

    controlado = db.Column(db.Boolean, default=False)                     # Portaria 344/98
    tipo_receituario = db.Column(db.String(50), nullable=True)            # A, B, C...
    codigo_sus = db.Column(db.String(20), nullable=True)                  # BR/DATASUS

    estoque_minimo = db.Column(db.Integer, default=0)                     # ponto de pedido
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lotes = db.relationship(
        "LoteEstoque", back_populates="medicamento",
        cascade="all, delete-orphan", order_by="LoteEstoque.validade"
    )

    @property
    def estoque_total(self) -> int:
        """Soma da quantidade de todos os lotes vigentes."""
        return sum(l.quantidade for l in self.lotes if l.quantidade > 0)

    @property
    def abaixo_minimo(self) -> bool:
        return self.estoque_total <= (self.estoque_minimo or 0)

    @property
    def descricao_completa(self) -> str:
        partes = [self.nome]
        if self.concentracao:
            partes.append(self.concentracao)
        if self.forma:
            partes.append(f"({self.forma.value})")
        return " ".join(partes)

    def __repr__(self):
        return f"<MedicamentoFarmacia {self.codigo} — {self.nome}>"


class LoteEstoque(db.Model):
    """Lote de um medicamento em estoque (controle por lote/validade)."""
    __tablename__ = "lotes_estoque"

    id = db.Column(db.Integer, primary_key=True)
    medicamento_id = db.Column(
        db.Integer, db.ForeignKey("medicamentos_farmacia.id"), nullable=False, index=True
    )
    numero_lote = db.Column(db.String(50), nullable=True)
    validade = db.Column(db.Date, nullable=True, index=True)
    quantidade = db.Column(db.Integer, default=0, nullable=False)
    fabricante = db.Column(db.String(150), nullable=True)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    medicamento = db.relationship("MedicamentoFarmacia", back_populates="lotes")

    @property
    def vencido(self) -> bool:
        if not self.validade:
            return False
        from datetime import date
        return self.validade < date.today()

    def __repr__(self):
        return f"<LoteEstoque med={self.medicamento_id} lote={self.numero_lote} qtd={self.quantidade}>"


# ---------------------------------------------------------------------------
# Dispensação
# ---------------------------------------------------------------------------

class Dispensacao(db.Model):
    """
    Dispensação de medicamentos. Pode estar vinculada a uma prescrição médica
    de internação (dispensação hospitalar) ou ser avulsa.
    """
    __tablename__ = "dispensacoes"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=True, index=True)
    prescricao_id = db.Column(
        db.Integer, db.ForeignKey("prescricoes_medicas.id"), nullable=True, index=True
    )
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=True)

    status = db.Column(db.Enum(StatusDispensacao), default=StatusDispensacao.PENDENTE, nullable=False)
    farmaceutico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)

    dispensado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])
    prescricao = db.relationship("PrescricaoMedica", foreign_keys=[prescricao_id])
    farmaceutico = db.relationship("Usuario", foreign_keys=[farmaceutico_id])
    itens = db.relationship(
        "ItemDispensacao", back_populates="dispensacao",
        cascade="all, delete-orphan", order_by="ItemDispensacao.id"
    )

    def __repr__(self):
        return f"<Dispensacao {self.numero} — {self.status.value}>"


class ItemDispensacao(db.Model):
    """Item dispensado (medicamento + quantidade + lote)."""
    __tablename__ = "itens_dispensacao"

    id = db.Column(db.Integer, primary_key=True)
    dispensacao_id = db.Column(
        db.Integer, db.ForeignKey("dispensacoes.id"), nullable=False, index=True
    )
    medicamento_id = db.Column(
        db.Integer, db.ForeignKey("medicamentos_farmacia.id"), nullable=False
    )
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes_estoque.id"), nullable=True)
    quantidade = db.Column(db.Integer, nullable=False)
    # Vínculo opcional ao item da prescrição que originou a dispensação
    item_prescricao_id = db.Column(
        db.Integer, db.ForeignKey("itens_prescricao.id"), nullable=True
    )

    dispensacao = db.relationship("Dispensacao", back_populates="itens")
    medicamento = db.relationship("MedicamentoFarmacia", foreign_keys=[medicamento_id])
    lote = db.relationship("LoteEstoque", foreign_keys=[lote_id])

    def __repr__(self):
        return f"<ItemDispensacao med={self.medicamento_id} qtd={self.quantidade}>"


class MovimentoEstoque(db.Model):
    """Registro de toda movimentação de estoque da farmácia (auditoria)."""
    __tablename__ = "movimentos_estoque"

    id = db.Column(db.Integer, primary_key=True)
    medicamento_id = db.Column(
        db.Integer, db.ForeignKey("medicamentos_farmacia.id"), nullable=False, index=True
    )
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes_estoque.id"), nullable=True)
    tipo = db.Column(db.Enum(TipoMovimentoEstoque), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)   # positivo=entrada, negativo=saída
    saldo_apos = db.Column(db.Integer, nullable=True)
    motivo = db.Column(db.String(300), nullable=True)
    dispensacao_id = db.Column(db.Integer, db.ForeignKey("dispensacoes.id"), nullable=True)

    responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    registrado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    medicamento = db.relationship("MedicamentoFarmacia", foreign_keys=[medicamento_id])
    responsavel = db.relationship("Usuario", foreign_keys=[responsavel_id])

    def __repr__(self):
        return f"<MovimentoEstoque {self.tipo.value} {self.quantidade}>"
