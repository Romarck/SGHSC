"""
models/rh.py — Recursos Humanos.

Funcionários (vinculados opcionalmente a Usuario), setores e escalas de plantão.
"""

import enum
from datetime import datetime, timezone

from ..extensions import db


class TipoVinculo(enum.Enum):
    CLT = "CLT"
    ESTATUTARIO = "estatutário"
    PJ = "pessoa jurídica"
    TEMPORARIO = "temporário"
    ESTAGIARIO = "estagiário"
    VOLUNTARIO = "voluntário"


class StatusFuncionario(enum.Enum):
    ATIVO = "ativo"
    FERIAS = "férias"
    AFASTADO = "afastado"
    DESLIGADO = "desligado"


class TurnoPlantao(enum.Enum):
    MANHA = "manhã"
    TARDE = "tarde"
    NOITE = "noite"
    DIURNO_12 = "diurno 12h"
    NOTURNO_12 = "noturno 12h"
    PLANTAO_24 = "plantão 24h"


class Setor(db.Model):
    """Setor/departamento da instituição."""
    __tablename__ = "setores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Setor {self.nome}>"


class Funcionario(db.Model):
    """Funcionário da instituição. Pode estar vinculado a um Usuario do sistema."""
    __tablename__ = "funcionarios"

    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(150), nullable=False, index=True)
    cpf = db.Column(db.String(14), unique=True, nullable=True)
    cargo = db.Column(db.String(100), nullable=True)
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"), nullable=True)

    vinculo = db.Column(db.Enum(TipoVinculo), default=TipoVinculo.CLT, nullable=True)
    status = db.Column(db.Enum(StatusFuncionario), default=StatusFuncionario.ATIVO, nullable=False, index=True)
    conselho_tipo = db.Column(db.String(10), nullable=True)   # CRM, COREN...
    conselho_numero = db.Column(db.String(30), nullable=True)

    telefone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    data_admissao = db.Column(db.Date, nullable=True)
    data_desligamento = db.Column(db.Date, nullable=True)

    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    setor = db.relationship("Setor", foreign_keys=[setor_id])
    usuario = db.relationship("Usuario", foreign_keys=[usuario_id])

    def __repr__(self):
        return f"<Funcionario {self.matricula} — {self.nome}>"


class EscalaPlantao(db.Model):
    """Escala de plantão de um funcionário."""
    __tablename__ = "escalas_plantao"

    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey("funcionarios.id"), nullable=False, index=True)
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"), nullable=True)
    data = db.Column(db.Date, nullable=False, index=True)
    turno = db.Column(db.Enum(TurnoPlantao), nullable=False)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fim = db.Column(db.Time, nullable=True)
    observacoes = db.Column(db.String(300), nullable=True)

    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    funcionario = db.relationship("Funcionario", foreign_keys=[funcionario_id])
    setor = db.relationship("Setor", foreign_keys=[setor_id])

    def __repr__(self):
        return f"<EscalaPlantao {self.funcionario_id} — {self.data} {self.turno.value}>"
