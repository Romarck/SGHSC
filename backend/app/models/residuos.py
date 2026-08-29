"""
models/residuos.py — PGRSS (Plano de Gerenciamento de Resíduos de Serviços de Saúde).

Classificação por grupos da RDC ANVISA nº 222/2018 e resolução CONAMA 358/2005:
  A - infectantes (biológicos)
  B - químicos
  C - rejeitos radioativos
  D - comuns (recicláveis / não recicláveis)
  E - perfurocortantes
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class GrupoResiduo(enum.Enum):
    A = "A — Infectante (biológico)"
    B = "B — Químico"
    C = "C — Rejeito radioativo"
    D = "D — Comum"
    E = "E — Perfurocortante"


class StatusColeta(enum.Enum):
    ARMAZENADO = "armazenado"
    COLETADO = "coletado"
    DESTINADO = "destinado (destinação final)"


class RegistroResiduo(db.Model):
    """
    Registro de geração de resíduo (pesagem por grupo/origem).
    Alimenta os indicadores do PGRSS e o manifesto de transporte.
    """
    __tablename__ = "registros_residuo"

    id = db.Column(db.Integer, primary_key=True)
    grupo = db.Column(db.Enum(GrupoResiduo), nullable=False, index=True)
    origem_setor = db.Column(db.String(100), nullable=True)   # setor gerador
    peso_kg = db.Column(db.Numeric(8, 3), nullable=False)      # pesagem
    descricao = db.Column(db.String(300), nullable=True)
    acondicionamento = db.Column(db.String(100), nullable=True)  # saco branco leitoso, caixa perfurocortante...

    status = db.Column(db.Enum(StatusColeta), default=StatusColeta.ARMAZENADO, nullable=False, index=True)
    coleta_id = db.Column(db.Integer, db.ForeignKey("coletas_residuo.id"), nullable=True)

    registrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    gerado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    registrado_por = db.relationship("Usuario", foreign_keys=[registrado_por_id])
    coleta = db.relationship("ColetaResiduo", back_populates="registros")

    @property
    def cor_grupo(self) -> str:
        cores = {
            GrupoResiduo.A: "danger",
            GrupoResiduo.B: "warning",
            GrupoResiduo.C: "dark",
            GrupoResiduo.D: "secondary",
            GrupoResiduo.E: "primary",
        }
        return cores.get(self.grupo, "secondary")

    def __repr__(self):
        return f"<RegistroResiduo {self.grupo.name} {self.peso_kg}kg>"


class ColetaResiduo(db.Model):
    """
    Coleta externa de resíduos (transporte para destinação final).
    Consolida os registros armazenados; gera o manifesto de transporte.
    """
    __tablename__ = "coletas_residuo"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    empresa_coletora = db.Column(db.String(200), nullable=False)
    numero_manifesto = db.Column(db.String(50), nullable=True)   # MTR (Manifesto de Transporte de Resíduos)
    peso_total_kg = db.Column(db.Numeric(10, 3), default=0)
    destinacao_final = db.Column(db.String(200), nullable=True)  # incineração, aterro, autoclave...
    observacoes = db.Column(db.Text, nullable=True)

    responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    coletado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    responsavel = db.relationship("Usuario", foreign_keys=[responsavel_id])
    registros = db.relationship("RegistroResiduo", back_populates="coleta")

    def __repr__(self):
        return f"<ColetaResiduo {self.numero} — {self.peso_total_kg}kg>"
