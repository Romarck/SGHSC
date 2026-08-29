"""
models/certificado.py — Certificação digital e documentos assinados (ICP-Brasil).

Registra os certificados A1 dos profissionais e cada documento assinado,
com hash SHA-256 para validação pública via QR Code.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoCertificado(enum.Enum):
    A1 = "A1"            # arquivo .p12/.pfx (servidor)
    A3 = "A3"            # token/smartcard
    TESTE = "teste"      # autoassinado — sem valor jurídico


class TipoDocumentoAssinado(enum.Enum):
    PRESCRICAO_MEDICA = "prescrição médica"
    EVOLUCAO_MEDICA = "evolução médica"
    LAUDO_ALTA = "laudo de alta"
    LAUDO_EXAME = "laudo de exame"
    DESCRICAO_CIRURGICA = "descrição cirúrgica"
    RECEITUARIO = "receituário"
    ATESTADO = "atestado"
    OUTRO = "outro"


class StatusDocumento(enum.Enum):
    ASSINADO = "assinado"
    INVALIDADO = "invalidado"
    REVOGADO = "revogado"


# ---------------------------------------------------------------------------
# Modelo: CertificadoDigital
# ---------------------------------------------------------------------------

class CertificadoDigital(db.Model):
    """
    Certificado digital de um profissional (ou da instituição).
    O arquivo .p12/.pfx é armazenado em CERT_STORAGE_PATH; aqui guardamos
    apenas os metadados. A senha NÃO é persistida em texto puro.
    """
    __tablename__ = "certificados_digitais"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)

    tipo = db.Column(db.Enum(TipoCertificado), default=TipoCertificado.A1, nullable=False)
    titular = db.Column(db.String(300), nullable=True)   # subject do certificado
    emissor = db.Column(db.String(300), nullable=True)   # issuer (AC)
    numero_serie = db.Column(db.String(100), nullable=True)
    arquivo_path = db.Column(db.String(500), nullable=False)

    valido_de = db.Column(db.DateTime(timezone=True), nullable=True)
    valido_ate = db.Column(db.DateTime(timezone=True), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    usuario = db.relationship("Usuario", foreign_keys=[usuario_id])

    @property
    def vigente(self) -> bool:
        """Certificado está dentro do período de validade e ativo?"""
        if not self.ativo or not self.valido_ate:
            return False
        return self.valido_ate > datetime.now(timezone.utc)

    @property
    def dias_para_expirar(self) -> int:
        if not self.valido_ate:
            return 0
        delta = self.valido_ate - datetime.now(timezone.utc)
        return max(0, delta.days)

    def __repr__(self):
        return f"<CertificadoDigital {self.tipo.value} — usuário {self.usuario_id}>"


# ---------------------------------------------------------------------------
# Modelo: DocumentoAssinado
# ---------------------------------------------------------------------------

class DocumentoAssinado(db.Model):
    """
    Registro de um documento assinado digitalmente.
    O hash SHA-256 permite validação pública: qualquer pessoa que tenha o
    documento pode conferir o hash na URL pública apontada pelo QR Code.
    """
    __tablename__ = "documentos_assinados"

    id = db.Column(db.Integer, primary_key=True)

    # Código público de validação (curto, usado na URL do QR)
    codigo_validacao = db.Column(db.String(32), unique=True, nullable=False, index=True)

    tipo = db.Column(db.Enum(TipoDocumentoAssinado), nullable=False)
    titulo = db.Column(db.String(300), nullable=False)
    hash_documento = db.Column(db.String(128), nullable=False, index=True)  # SHA-256
    pdf_path = db.Column(db.String(500), nullable=False)
    qrcode_path = db.Column(db.String(500), nullable=True)

    # Quem assinou
    assinante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    assinante_nome = db.Column(db.String(300), nullable=True)   # do certificado
    certificado_id = db.Column(
        db.Integer, db.ForeignKey("certificados_digitais.id"), nullable=True
    )

    # Vínculo opcional com paciente/internação (rastreabilidade)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=True, index=True)

    # Referência polimórfica leve ao objeto de origem (ex: "prescricao_medica:42")
    origem_tipo = db.Column(db.String(50), nullable=True)
    origem_id = db.Column(db.Integer, nullable=True)

    status = db.Column(db.Enum(StatusDocumento), default=StatusDocumento.ASSINADO, nullable=False)
    assinado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True
    )

    assinante = db.relationship("Usuario", foreign_keys=[assinante_id])
    certificado = db.relationship("CertificadoDigital", foreign_keys=[certificado_id])
    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])

    def __repr__(self):
        return f"<DocumentoAssinado {self.codigo_validacao} — {self.tipo.value}>"
