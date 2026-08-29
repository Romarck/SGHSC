"""
models/prontuario.py — Prontuário Eletrônico do Paciente (PEP).

O Prontuário é o agregador de todos os registros clínicos do paciente.
Cada paciente tem exatamente um prontuário; os atendimentos são vinculados a ele.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoEntradaProntuario(enum.Enum):
    ANAMNESE = "anamnese"
    EVOLUCAO_MEDICA = "evolução médica"
    EVOLUCAO_ENFERMAGEM = "evolução de enfermagem"
    PRESCRICAO_MEDICA = "prescrição médica"
    PRESCRICAO_ENFERMAGEM = "prescrição de enfermagem"
    RESULTADO_EXAME = "resultado de exame"
    LAUDO = "laudo"
    ALTA = "alta"
    TRANSFERENCIA = "transferência"
    OBITO = "óbito"
    NOTA_CIRURGICA = "nota cirúrgica"
    RECEITUARIO = "receituário"
    ATESTADO = "atestado"
    OUTRO = "outro"


class Prontuario(db.Model):
    """
    Cabeçalho do Prontuário Eletrônico do Paciente.

    Contém metadados e serve como âncora para todos os registros clínicos.
    O número do prontuário é gerado automaticamente e é único na instituição.
    """
    __tablename__ = "prontuarios"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    paciente_id = db.Column(
        db.Integer, db.ForeignKey("pacientes.id"), unique=True, nullable=False
    )
    aberto_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    aberto_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    # Relacionamentos
    paciente = db.relationship("Paciente", back_populates="prontuario")
    aberto_por = db.relationship("Usuario", foreign_keys=[aberto_por_id])
    entradas = db.relationship(
        "EntradaProntuario", back_populates="prontuario",
        order_by="EntradaProntuario.registrado_em.desc()", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Prontuario {self.numero}>"


class EntradaProntuario(db.Model):
    """
    Registro individual no prontuário (evolução, prescrição, laudo, etc.).
    Cada entrada pode ter assinatura digital ICP-Brasil.
    """
    __tablename__ = "entradas_prontuario"

    id = db.Column(db.Integer, primary_key=True)
    prontuario_id = db.Column(
        db.Integer, db.ForeignKey("prontuarios.id"), nullable=False, index=True
    )
    tipo = db.Column(db.Enum(TipoEntradaProntuario), nullable=False)
    titulo = db.Column(db.String(200), nullable=True)
    conteudo = db.Column(db.Text, nullable=False)

    # Registro da entrada
    registrado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True
    )
    registrado_por_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )

    # Assinatura digital (ICP-Brasil)
    assinado = db.Column(db.Boolean, default=False, nullable=False)
    assinado_em = db.Column(db.DateTime(timezone=True), nullable=True)
    assinado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    assinatura_hash = db.Column(db.String(512), nullable=True)   # Hash da assinatura digital
    pdf_path = db.Column(db.String(500), nullable=True)           # Caminho do PDF assinado

    # Relacionamentos
    prontuario = db.relationship("Prontuario", back_populates="entradas")
    registrado_por = db.relationship("Usuario", foreign_keys=[registrado_por_id])
    assinado_por = db.relationship("Usuario", foreign_keys=[assinado_por_id])

    def __repr__(self):
        return f"<EntradaProntuario {self.tipo.value} — {self.registrado_em}>"
