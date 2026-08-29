"""
models/rnds.py — Integração com a RNDS (Rede Nacional de Dados em Saúde).

A RNDS usa o padrão FHIR R4. Cada evento de saúde (atendimento, exame, etc.)
é mapeado para um recurso FHIR (Bundle) e enviado ao barramento nacional.

NOTA: o envio efetivo ao barramento de PRODUÇÃO exige certificado ICP-Brasil
credenciado, cadastro no DATASUS e conexão autenticada (X.509 + OAuth). Aqui
registramos a fila de envio, o payload FHIR gerado e o status. O envio real é
um stub documentado, a ser completado com as credenciais oficiais.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoRecursoFHIR(enum.Enum):
    PACIENTE = "Patient"
    ATENDIMENTO = "Encounter"
    RESULTADO_EXAME = "DiagnosticReport"
    IMUNIZACAO = "Immunization"
    PRESCRICAO = "MedicationRequest"
    CONDICAO = "Condition"


class StatusEnvioRNDS(enum.Enum):
    PENDENTE = "pendente"
    ENVIANDO = "enviando"
    ENVIADO = "enviado"
    ERRO = "erro"
    CANCELADO = "cancelado"


class RegistroRNDS(db.Model):
    """
    Registro de um evento a ser enviado (ou já enviado) à RNDS.
    Guarda o payload FHIR e o status do envio.
    """
    __tablename__ = "registros_rnds"

    id = db.Column(db.Integer, primary_key=True)
    tipo_recurso = db.Column(db.Enum(TipoRecursoFHIR), nullable=False, index=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=True, index=True)
    # Referência polimórfica leve ao objeto de origem (ex: "atendimento_emergencia:12")
    origem_tipo = db.Column(db.String(50), nullable=True)
    origem_id = db.Column(db.Integer, nullable=True)

    payload_fhir = db.Column(db.Text, nullable=True)     # JSON FHIR gerado
    status = db.Column(db.Enum(StatusEnvioRNDS), default=StatusEnvioRNDS.PENDENTE, nullable=False, index=True)

    # Retorno do barramento
    protocolo_rnds = db.Column(db.String(100), nullable=True)  # identificador retornado
    mensagem_retorno = db.Column(db.Text, nullable=True)
    tentativas = db.Column(db.Integer, default=0, nullable=False)

    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    enviado_em = db.Column(db.DateTime(timezone=True), nullable=True)

    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])

    @property
    def cor_status(self) -> str:
        cores = {
            StatusEnvioRNDS.PENDENTE: "secondary",
            StatusEnvioRNDS.ENVIANDO: "info",
            StatusEnvioRNDS.ENVIADO: "success",
            StatusEnvioRNDS.ERRO: "danger",
            StatusEnvioRNDS.CANCELADO: "dark",
        }
        return cores.get(self.status, "secondary")

    def __repr__(self):
        return f"<RegistroRNDS {self.tipo_recurso.value} — {self.status.value}>"
