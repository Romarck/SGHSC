"""
models/emergencia.py — Módulo de Pronto-Atendimento / Emergência.

Fluxo: chegada → triagem Manchester → atendimento médico → saída (alta/internação/óbito/transferência)
"""

import enum
from datetime import datetime, timezone

from ..extensions import db

# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------

class ClassificacaoManchester(enum.Enum):
    """
    Classificação de Risco pelo Protocolo de Manchester.
    Ordem de prioridade decrescente (vermelho = mais urgente).
    """
    VERMELHO = "vermelho"      # Emergência — atendimento imediato
    LARANJA = "laranja"        # Muito urgente — ≤ 10 min
    AMARELO = "amarelo"        # Urgente — ≤ 60 min
    VERDE = "verde"            # Pouco urgente — ≤ 120 min
    AZUL = "azul"              # Não urgente — ≤ 240 min


TEMPO_ALVO_MANCHESTER = {
    ClassificacaoManchester.VERMELHO: 0,
    ClassificacaoManchester.LARANJA: 10,
    ClassificacaoManchester.AMARELO: 60,
    ClassificacaoManchester.VERDE: 120,
    ClassificacaoManchester.AZUL: 240,
}


class MotivoSaidaEmergencia(enum.Enum):
    ALTA_MEDICA = "alta médica"
    INTERNACAO = "internação"
    TRANSFERENCIA = "transferência"
    OBITO = "óbito"
    EVASAO = "evasão"
    RECUSA_ATENDIMENTO = "recusa de atendimento"


class StatusAtendimentoEmergencia(enum.Enum):
    AGUARDANDO_TRIAGEM = "aguardando triagem"
    TRIADO = "triado"
    EM_ATENDIMENTO = "em atendimento"
    AGUARDANDO_RESULTADO = "aguardando resultado"
    FINALIZADO = "finalizado"


# ---------------------------------------------------------------------------
# Modelo: TriagemManchester
# ---------------------------------------------------------------------------

class TriagemManchester(db.Model):
    """
    Registro da Triagem de Risco pelo Protocolo de Manchester.
    Realizada pelo enfermeiro na chegada do paciente ao PA/Emergência.
    """
    __tablename__ = "triagens_manchester"

    id = db.Column(db.Integer, primary_key=True)
    atendimento_id = db.Column(
        db.Integer, db.ForeignKey("atendimentos_emergencia.id"), nullable=False, index=True
    )

    # Queixa principal e discriminador Manchester
    queixa_principal = db.Column(db.String(500), nullable=False)
    discriminador = db.Column(db.String(200), nullable=True)  # Ex: "Dor torácica moderada"
    classificacao = db.Column(db.Enum(ClassificacaoManchester), nullable=False)

    # Sinais vitais na triagem
    pressao_sistolica = db.Column(db.Integer, nullable=True)
    pressao_diastolica = db.Column(db.Integer, nullable=True)
    frequencia_cardiaca = db.Column(db.Integer, nullable=True)
    frequencia_respiratoria = db.Column(db.Integer, nullable=True)
    temperatura = db.Column(db.Numeric(4, 1), nullable=True)
    saturacao_o2 = db.Column(db.Integer, nullable=True)
    glicemia_capilar = db.Column(db.Integer, nullable=True)
    peso = db.Column(db.Numeric(5, 2), nullable=True)
    altura = db.Column(db.Numeric(4, 2), nullable=True)
    escala_dor = db.Column(db.Integer, nullable=True)  # 0–10

    # Registro
    realizada_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    realizada_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)

    # Relacionamentos
    atendimento = db.relationship(
        "AtendimentoEmergencia", back_populates="triagem", uselist=False
    )
    realizada_por = db.relationship("Usuario", foreign_keys=[realizada_por_id])

    @property
    def pressao_arterial(self) -> str:
        if self.pressao_sistolica and self.pressao_diastolica:
            return f"{self.pressao_sistolica}/{self.pressao_diastolica} mmHg"
        return "—"

    @property
    def cor_badge(self) -> str:
        """Retorna classe Bootstrap para o badge de cor Manchester."""
        cores = {
            ClassificacaoManchester.VERMELHO: "danger",
            ClassificacaoManchester.LARANJA: "warning",
            ClassificacaoManchester.AMARELO: "warning",
            ClassificacaoManchester.VERDE: "success",
            ClassificacaoManchester.AZUL: "info",
        }
        return cores.get(self.classificacao, "secondary")

    def __repr__(self):
        return f"<Triagem {self.classificacao.value} — {self.realizada_em}>"


# ---------------------------------------------------------------------------
# Modelo: AtendimentoEmergencia
# ---------------------------------------------------------------------------

class AtendimentoEmergencia(db.Model):
    """
    Atendimento no Pronto-Atendimento / Emergência.
    Cobre desde a chegada do paciente até a saída (alta, internação, óbito, etc.).
    """
    __tablename__ = "atendimentos_emergencia"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    paciente_id = db.Column(
        db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True
    )

    # Chegada
    chegada_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True
    )
    registrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    modo_chegada = db.Column(db.String(50), nullable=True)  # ambulância, próprios meios, SAMU

    # Atendimento
    status = db.Column(
        db.Enum(StatusAtendimentoEmergencia),
        default=StatusAtendimentoEmergencia.AGUARDANDO_TRIAGEM,
        nullable=False, index=True
    )
    medico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    inicio_atendimento_em = db.Column(db.DateTime(timezone=True), nullable=True)

    # Diagnóstico e conduta
    hipotese_diagnostica = db.Column(db.String(500), nullable=True)
    cid10_principal = db.Column(db.String(10), nullable=True)
    conduta = db.Column(db.Text, nullable=True)
    anamnese = db.Column(db.Text, nullable=True)
    exame_fisico = db.Column(db.Text, nullable=True)

    # Saída
    saida_em = db.Column(db.DateTime(timezone=True), nullable=True)
    motivo_saida = db.Column(db.Enum(MotivoSaidaEmergencia), nullable=True)
    destino_internacao = db.Column(db.String(100), nullable=True)  # leito/enfermaria destino
    destino_transferencia = db.Column(db.String(200), nullable=True)

    # Relacionamentos
    paciente = db.relationship("Paciente", back_populates="atendimentos_emergencia")
    triagem = db.relationship(
        "TriagemManchester", back_populates="atendimento", uselist=False,
        cascade="all, delete-orphan"
    )
    registrado_por = db.relationship("Usuario", foreign_keys=[registrado_por_id])
    medico = db.relationship("Usuario", foreign_keys=[medico_id])

    @property
    def tempo_espera_minutos(self) -> int | None:
        """Tempo entre chegada e início do atendimento médico."""
        if self.inicio_atendimento_em and self.chegada_em:
            delta = self.inicio_atendimento_em - self.chegada_em
            return int(delta.total_seconds() / 60)
        return None

    @property
    def em_espera(self) -> bool:
        return self.status in (
            StatusAtendimentoEmergencia.AGUARDANDO_TRIAGEM,
            StatusAtendimentoEmergencia.TRIADO,
        )

    def __repr__(self):
        return f"<AtendimentoEmergencia {self.numero}>"
