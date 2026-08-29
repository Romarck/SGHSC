"""
models/auditoria.py — Trilha de auditoria de acesso (Story S-07 / LGPD).

Registra QUEM acessou QUAL prontuário/dado de paciente, QUANDO e de ONDE.
Atende ao princípio da responsabilização (accountability) da LGPD para dados
sensíveis de saúde.

Tabela append-only por convenção: a aplicação apenas INSERE registros. Não há
rota/serviço para editar ou apagar (exceto a rotina de retenção via CLI, que
remove registros vencidos em bloco). Ver docs/security/auditoria-lgpd.md.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class AcaoAuditoria(enum.Enum):
    """Ação registrada na trilha."""
    VISUALIZAR = "visualizar"        # leitura de prontuário/dados do paciente
    BAIXAR_DOCUMENTO = "baixar_documento"  # download de PDF/documento clínico
    EXPORTAR = "exportar"            # exportação/relatório de dados do paciente


class LogAcesso(db.Model):
    """
    Evento de acesso a dado sensível de paciente.

    Um registro por evento (append-only). Indexado por paciente, usuário e data
    para consultas da trilha ("quem acessou o prontuário do paciente X").
    """
    __tablename__ = "logs_acesso"

    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)

    # Quem acessou
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True
    )
    usuario_username = db.Column(db.String(50), nullable=True)  # snapshot (resiliência)

    # Qual paciente (quando aplicável)
    paciente_id = db.Column(
        db.Integer, db.ForeignKey("pacientes.id"), nullable=True, index=True
    )

    # O que foi acessado
    acao = db.Column(db.Enum(AcaoAuditoria), nullable=False, index=True)
    recurso = db.Column(db.String(120), nullable=False)   # ex.: "internacao.prontuario"
    recurso_id = db.Column(db.String(60), nullable=True)  # id do objeto acessado
    detalhe = db.Column(db.String(255), nullable=True)

    # Contexto de rede
    ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(300), nullable=True)

    # Quando
    registrado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True
    )

    # Relacionamentos (somente leitura na prática)
    usuario = db.relationship("Usuario", foreign_keys=[usuario_id])
    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])

    def __repr__(self):
        return (
            f"<LogAcesso {self.registrado_em} "
            f"u={self.usuario_id} p={self.paciente_id} {self.acao.value}>"
        )
