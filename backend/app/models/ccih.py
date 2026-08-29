"""
models/ccih.py — Comissão de Controle de Infecção Hospitalar (CCIH).

Notificações de infecção hospitalar e gestão de precauções/isolamento.
Base para relatórios de vigilância epidemiológica (SCIRAS/ANVISA).
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoInfeccao(enum.Enum):
    IRAS = "IRAS (relacionada à assistência)"
    COMUNITARIA = "comunitária"
    SITIO_CIRURGICO = "sítio cirúrgico"
    TRATO_URINARIO = "trato urinário"
    CORRENTE_SANGUINEA = "corrente sanguínea"
    PNEUMONIA = "pneumonia / respiratória"
    PELE_PARTES_MOLES = "pele e partes moles"
    OUTRA = "outra"


class TipoPrecaucao(enum.Enum):
    PADRAO = "padrão"
    CONTATO = "contato"
    GOTICULAS = "gotículas"
    AEROSSOIS = "aerossóis"
    PROTETORA = "protetora (imunossuprimido)"


class StatusNotificacao(enum.Enum):
    ABERTA = "aberta"
    EM_INVESTIGACAO = "em investigação"
    CONFIRMADA = "confirmada"
    DESCARTADA = "descartada"
    ENCERRADA = "encerrada"


class StatusIsolamento(enum.Enum):
    ATIVO = "ativo"
    SUSPENSO = "suspenso"
    ENCERRADO = "encerrado"


class NotificacaoInfeccao(db.Model):
    """Notificação de caso de infecção para acompanhamento pela CCIH."""
    __tablename__ = "notificacoes_infeccao"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=True)
    notificante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    tipo = db.Column(db.Enum(TipoInfeccao), nullable=False)
    topografia = db.Column(db.String(200), nullable=True)      # sítio da infecção
    microrganismo = db.Column(db.String(200), nullable=True)   # agente isolado
    antibiograma = db.Column(db.Text, nullable=True)
    cid10 = db.Column(db.String(10), nullable=True)

    status = db.Column(
        db.Enum(StatusNotificacao), default=StatusNotificacao.ABERTA, nullable=False, index=True
    )
    descricao = db.Column(db.Text, nullable=True)
    conduta = db.Column(db.Text, nullable=True)

    data_notificacao = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    data_encerramento = db.Column(db.DateTime(timezone=True), nullable=True)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])
    internacao = db.relationship("Internacao", foreign_keys=[internacao_id])
    notificante = db.relationship("Usuario", foreign_keys=[notificante_id])

    def __repr__(self):
        return f"<NotificacaoInfeccao {self.numero} — {self.status.value}>"


class IsolamentoPaciente(db.Model):
    """
    Registro de precaução/isolamento de um paciente internado.
    Vincula-se à internação/leito; marca o leito como isolamento.
    """
    __tablename__ = "isolamentos_paciente"

    id = db.Column(db.Integer, primary_key=True)
    internacao_id = db.Column(
        db.Integer, db.ForeignKey("internacoes.id"), nullable=False, index=True
    )
    notificacao_id = db.Column(
        db.Integer, db.ForeignKey("notificacoes_infeccao.id"), nullable=True
    )

    tipo_precaucao = db.Column(db.Enum(TipoPrecaucao), nullable=False)
    motivo = db.Column(db.String(300), nullable=True)
    microrganismo = db.Column(db.String(200), nullable=True)

    status = db.Column(
        db.Enum(StatusIsolamento), default=StatusIsolamento.ATIVO, nullable=False, index=True
    )
    iniciado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    encerrado_em = db.Column(db.DateTime(timezone=True), nullable=True)

    prescrito_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    internacao = db.relationship("Internacao", foreign_keys=[internacao_id])
    notificacao = db.relationship("NotificacaoInfeccao", foreign_keys=[notificacao_id])
    prescrito_por = db.relationship("Usuario", foreign_keys=[prescrito_por_id])

    @property
    def cor_precaucao(self) -> str:
        """Classe Bootstrap para sinalização visual da precaução."""
        cores = {
            TipoPrecaucao.PADRAO: "secondary",
            TipoPrecaucao.CONTATO: "warning",
            TipoPrecaucao.GOTICULAS: "info",
            TipoPrecaucao.AEROSSOIS: "danger",
            TipoPrecaucao.PROTETORA: "success",
        }
        return cores.get(self.tipo_precaucao, "secondary")

    def __repr__(self):
        return f"<IsolamentoPaciente internacao={self.internacao_id} — {self.tipo_precaucao.value}>"
