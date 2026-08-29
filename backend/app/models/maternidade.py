"""
models/maternidade.py — Módulo de Maternidade.

Pré-natal, parto, registro do recém-nascido e intercorrências perinatais.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoParto(enum.Enum):
    NORMAL = "normal / vaginal"
    CESAREA = "cesárea"
    FORCEPS = "fórceps"
    VACUO = "vácuo-extração"


class ClassificacaoRisco(enum.Enum):
    HABITUAL = "risco habitual"
    ALTO_RISCO = "alto risco"


class SexoRN(enum.Enum):
    MASCULINO = "masculino"
    FEMININO = "feminino"
    INDETERMINADO = "indeterminado"


class CondicaoNascimento(enum.Enum):
    VIVO = "nascido vivo"
    NATIMORTO = "natimorto"
    OBITO_PERINATAL = "óbito perinatal"


# ---------------------------------------------------------------------------
# Pré-natal
# ---------------------------------------------------------------------------

class PreNatal(db.Model):
    """Acompanhamento de pré-natal de uma gestante."""
    __tablename__ = "prenatais"

    id = db.Column(db.Integer, primary_key=True)
    gestante_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)

    dum = db.Column(db.Date, nullable=True)             # data da última menstruação
    dpp = db.Column(db.Date, nullable=True)             # data provável do parto
    gestacoes = db.Column(db.Integer, default=0)        # G
    partos = db.Column(db.Integer, default=0)           # P
    abortos = db.Column(db.Integer, default=0)          # A
    cesareas = db.Column(db.Integer, default=0)
    classificacao_risco = db.Column(
        db.Enum(ClassificacaoRisco), default=ClassificacaoRisco.HABITUAL, nullable=False
    )
    tipo_sanguineo = db.Column(db.String(5), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    medico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    gestante = db.relationship("Paciente", foreign_keys=[gestante_id])
    medico = db.relationship("Usuario", foreign_keys=[medico_id])
    consultas = db.relationship(
        "ConsultaPreNatal", back_populates="prenatal",
        cascade="all, delete-orphan", order_by="ConsultaPreNatal.data_consulta"
    )

    def __repr__(self):
        return f"<PreNatal gestante={self.gestante_id}>"


class ConsultaPreNatal(db.Model):
    """Consulta de acompanhamento do pré-natal."""
    __tablename__ = "consultas_prenatal"

    id = db.Column(db.Integer, primary_key=True)
    prenatal_id = db.Column(db.Integer, db.ForeignKey("prenatais.id"), nullable=False, index=True)

    data_consulta = db.Column(db.Date, nullable=False)
    idade_gestacional_semanas = db.Column(db.Integer, nullable=True)
    peso = db.Column(db.Numeric(5, 2), nullable=True)
    pressao_arterial = db.Column(db.String(20), nullable=True)
    altura_uterina = db.Column(db.Integer, nullable=True)       # cm
    bcf = db.Column(db.Integer, nullable=True)                  # batimentos cardíacos fetais
    movimentacao_fetal = db.Column(db.Boolean, default=True)
    edema = db.Column(db.String(50), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    prenatal = db.relationship("PreNatal", back_populates="consultas")

    def __repr__(self):
        return f"<ConsultaPreNatal prenatal={self.prenatal_id} — {self.data_consulta}>"


# ---------------------------------------------------------------------------
# Parto e recém-nascido
# ---------------------------------------------------------------------------

class Parto(db.Model):
    """Registro do parto."""
    __tablename__ = "partos"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)

    gestante_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=True)
    prenatal_id = db.Column(db.Integer, db.ForeignKey("prenatais.id"), nullable=True)

    tipo = db.Column(db.Enum(TipoParto), nullable=False)
    data_parto = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    idade_gestacional_semanas = db.Column(db.Integer, nullable=True)
    medico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    tipo_anestesia = db.Column(db.String(50), nullable=True)

    intercorrencias = db.Column(db.Text, nullable=True)
    descricao = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    gestante = db.relationship("Paciente", foreign_keys=[gestante_id])
    internacao = db.relationship("Internacao", foreign_keys=[internacao_id])
    medico = db.relationship("Usuario", foreign_keys=[medico_id])
    recem_nascidos = db.relationship(
        "RecemNascido", back_populates="parto",
        cascade="all, delete-orphan", order_by="RecemNascido.id"
    )

    def __repr__(self):
        return f"<Parto {self.numero} — {self.tipo.value}>"


class RecemNascido(db.Model):
    """Registro do recém-nascido (RN)."""
    __tablename__ = "recem_nascidos"

    id = db.Column(db.Integer, primary_key=True)
    parto_id = db.Column(db.Integer, db.ForeignKey("partos.id"), nullable=False, index=True)

    # Se o RN for cadastrado como paciente próprio
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=True)

    sexo = db.Column(db.Enum(SexoRN), nullable=False)
    condicao = db.Column(
        db.Enum(CondicaoNascimento), default=CondicaoNascimento.VIVO, nullable=False
    )
    peso_gramas = db.Column(db.Integer, nullable=True)
    comprimento_cm = db.Column(db.Numeric(4, 1), nullable=True)
    perimetro_cefalico_cm = db.Column(db.Numeric(4, 1), nullable=True)
    apgar_1min = db.Column(db.Integer, nullable=True)          # 0–10
    apgar_5min = db.Column(db.Integer, nullable=True)          # 0–10

    hora_nascimento = db.Column(db.DateTime(timezone=True), nullable=True)
    reanimacao = db.Column(db.Boolean, default=False)
    intercorrencias = db.Column(db.Text, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    parto = db.relationship("Parto", back_populates="recem_nascidos")
    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])

    @property
    def apgar_resumo(self) -> str:
        a1 = self.apgar_1min if self.apgar_1min is not None else "—"
        a5 = self.apgar_5min if self.apgar_5min is not None else "—"
        return f"{a1}/{a5}"

    def __repr__(self):
        return f"<RecemNascido parto={self.parto_id} — {self.sexo.value}>"
