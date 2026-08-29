"""
models/exame.py — Módulo de Exames (laboratório e imagem).

Fluxo: solicitação (médico) → coleta/execução (laboratório) → resultado/laudo
       → visualização no prontuário.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class CategoriaExame(enum.Enum):
    LABORATORIAL = "laboratorial"
    IMAGEM = "imagem"
    ANATOMOPATOLOGICO = "anatomopatológico"
    CARDIOLOGICO = "cardiológico"
    ENDOSCOPICO = "endoscópico"
    OUTRO = "outro"


class PrioridadeExame(enum.Enum):
    ROTINA = "rotina"
    URGENTE = "urgente"
    EMERGENCIA = "emergência"


class StatusSolicitacaoExame(enum.Enum):
    SOLICITADO = "solicitado"
    COLETADO = "coletado"
    EM_ANALISE = "em análise"
    RESULTADO_DISPONIVEL = "resultado disponível"
    CANCELADO = "cancelado"


class OrigemExame(enum.Enum):
    AMBULATORIO = "ambulatório"
    EMERGENCIA = "emergência"
    INTERNACAO = "internação"


# ---------------------------------------------------------------------------
# Catálogo de exames
# ---------------------------------------------------------------------------

class ExameCatalogo(db.Model):
    """Catálogo de exames disponíveis na unidade (tabela de referência)."""
    __tablename__ = "exames_catalogo"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)  # ex: SIGTAP
    nome = db.Column(db.String(200), nullable=False, index=True)
    categoria = db.Column(db.Enum(CategoriaExame), nullable=False)
    material = db.Column(db.String(100), nullable=True)     # sangue, urina, etc.
    unidade_medida = db.Column(db.String(50), nullable=True)
    valor_referencia = db.Column(db.String(200), nullable=True)
    prazo_horas = db.Column(db.Integer, nullable=True)      # prazo padrão de resultado
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<ExameCatalogo {self.codigo} — {self.nome}>"


# ---------------------------------------------------------------------------
# Solicitação de exames
# ---------------------------------------------------------------------------

class SolicitacaoExame(db.Model):
    """Solicitação de um ou mais exames feita por um médico."""
    __tablename__ = "solicitacoes_exame"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    solicitante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    origem = db.Column(db.Enum(OrigemExame), nullable=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=True)
    atendimento_emergencia_id = db.Column(
        db.Integer, db.ForeignKey("atendimentos_emergencia.id"), nullable=True
    )
    consulta_id = db.Column(db.Integer, db.ForeignKey("consultas_ambulatoriais.id"), nullable=True)

    prioridade = db.Column(db.Enum(PrioridadeExame), default=PrioridadeExame.ROTINA, nullable=False)
    status = db.Column(
        db.Enum(StatusSolicitacaoExame),
        default=StatusSolicitacaoExame.SOLICITADO, nullable=False, index=True
    )
    indicacao_clinica = db.Column(db.String(500), nullable=True)
    cid10 = db.Column(db.String(10), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    solicitado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    coletado_em = db.Column(db.DateTime(timezone=True), nullable=True)
    coletado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])
    solicitante = db.relationship("Usuario", foreign_keys=[solicitante_id])
    coletado_por = db.relationship("Usuario", foreign_keys=[coletado_por_id])
    itens = db.relationship(
        "ItemExame", back_populates="solicitacao",
        cascade="all, delete-orphan", order_by="ItemExame.id"
    )

    @property
    def total_itens(self) -> int:
        return len(self.itens)

    @property
    def itens_com_resultado(self) -> int:
        return sum(1 for i in self.itens if i.resultado)

    def __repr__(self):
        return f"<SolicitacaoExame {self.numero} — {self.status.value}>"


class ItemExame(db.Model):
    """Um exame específico dentro de uma solicitação."""
    __tablename__ = "itens_exame"

    id = db.Column(db.Integer, primary_key=True)
    solicitacao_id = db.Column(
        db.Integer, db.ForeignKey("solicitacoes_exame.id"), nullable=False, index=True
    )
    exame_catalogo_id = db.Column(db.Integer, db.ForeignKey("exames_catalogo.id"), nullable=True)
    nome_exame = db.Column(db.String(200), nullable=False)  # snapshot do nome

    solicitacao = db.relationship("SolicitacaoExame", back_populates="itens")
    exame_catalogo = db.relationship("ExameCatalogo", foreign_keys=[exame_catalogo_id])
    resultado = db.relationship(
        "ResultadoExame", back_populates="item", uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ItemExame {self.nome_exame}>"


class ResultadoExame(db.Model):
    """Resultado/laudo de um item de exame."""
    __tablename__ = "resultados_exame"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("itens_exame.id"), nullable=False, unique=True)

    valor = db.Column(db.String(200), nullable=True)          # resultado numérico/textual
    unidade = db.Column(db.String(50), nullable=True)
    valor_referencia = db.Column(db.String(200), nullable=True)
    laudo = db.Column(db.Text, nullable=True)                 # laudo descritivo (imagem/anatomo)
    alterado = db.Column(db.Boolean, default=False)           # fora do valor de referência
    arquivo_path = db.Column(db.String(500), nullable=True)   # PDF/imagem anexado

    responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    liberado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Assinatura digital do laudo
    assinado = db.Column(db.Boolean, default=False)
    documento_assinado_id = db.Column(
        db.Integer, db.ForeignKey("documentos_assinados.id"), nullable=True
    )

    item = db.relationship("ItemExame", back_populates="resultado")
    responsavel = db.relationship("Usuario", foreign_keys=[responsavel_id])

    def __repr__(self):
        return f"<ResultadoExame item={self.item_id}>"
