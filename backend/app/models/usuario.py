"""
models/usuario.py — Modelos de autenticação e controle de acesso.

Modelo de permissão baseado em Perfis (RBAC - Role-Based Access Control).
Cada usuário tem um Perfil, cada Perfil tem um conjunto de Permissões por módulo.
"""

import enum
from datetime import datetime, timezone

from flask_login import UserMixin

from ..extensions import bcrypt, db

# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------

class StatusUsuario(enum.Enum):
    ATIVO = "ativo"
    INATIVO = "inativo"
    BLOQUEADO = "bloqueado"


class TipoPerfil(enum.Enum):
    ADMINISTRADOR = "administrador"       # Acesso total
    MEDICO = "medico"                     # Prescrição, PEP, evolução
    ENFERMEIRO = "enfermeiro"             # Prescrição enfermagem, controles
    TECNICO_ENFERMAGEM = "tecnico_enfermagem"
    FARMACEUTICO = "farmaceutico"         # Dispensação, estoque farmácia
    RECEPCIONISTA = "recepcionista"       # Cadastro, agenda, triagem básica
    FATURAMENTO = "faturamento"           # AIH, APAC, BPA
    FINANCEIRO = "financeiro"
    ALMOXARIFE = "almoxarife"
    NUTRICIONISTA = "nutricionista"
    FISIOTERAPEUTA = "fisioterapeuta"
    ASSISTENTE_SOCIAL = "assistente_social"
    LABORATORISTA = "laboratorista"
    RADIOLOGISTA = "radiologista"
    GESTOR = "gestor"                     # Relatórios gerenciais


# ---------------------------------------------------------------------------
# Tabela associativa Perfil <-> Permissao
# ---------------------------------------------------------------------------

perfil_permissao = db.Table(
    "perfil_permissao",
    db.Column("perfil_id", db.Integer, db.ForeignKey("perfis.id"), primary_key=True),
    db.Column("permissao_id", db.Integer, db.ForeignKey("permissoes.id"), primary_key=True),
)


# ---------------------------------------------------------------------------
# Modelo: Permissao
# ---------------------------------------------------------------------------

class Permissao(db.Model):
    """
    Permissão granular por módulo/ação.
    Formato: modulo.acao (ex: pacientes.criar, internacao.alta, faturamento.aih)
    """
    __tablename__ = "permissoes"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(100), unique=True, nullable=False, index=True)
    descricao = db.Column(db.String(255), nullable=False)
    modulo = db.Column(db.String(50), nullable=False, index=True)

    def __repr__(self):
        return f"<Permissao {self.codigo}>"


# ---------------------------------------------------------------------------
# Modelo: Perfil
# ---------------------------------------------------------------------------

class Perfil(db.Model):
    """
    Perfil de acesso (Role). Agrupa permissões.
    Perfis padrão definidos em TipoPerfil, mas novos podem ser criados.
    """
    __tablename__ = "perfis"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    tipo = db.Column(db.Enum(TipoPerfil), nullable=True)
    descricao = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relacionamentos
    permissoes = db.relationship(
        "Permissao", secondary=perfil_permissao, lazy="subquery",
        backref=db.backref("perfis", lazy=True)
    )
    usuarios = db.relationship("Usuario", back_populates="perfil", lazy="dynamic")

    def tem_permissao(self, codigo: str) -> bool:
        return any(p.codigo == codigo for p in self.permissoes)

    def __repr__(self):
        return f"<Perfil {self.nome}>"


# ---------------------------------------------------------------------------
# Modelo: Usuario
# ---------------------------------------------------------------------------

class Usuario(UserMixin, db.Model):
    """
    Usuário do sistema. Representa qualquer profissional com acesso ao SGHSC.
    Vinculado a um Perfil de acesso.
    """
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)

    # Identificação
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    _senha_hash = db.Column("senha_hash", db.String(255), nullable=False)

    # Dados profissionais
    cpf = db.Column(db.String(14), unique=True, nullable=True)
    conselho_tipo = db.Column(db.String(10), nullable=True)   # CRM, COREN, CRF, etc.
    conselho_numero = db.Column(db.String(30), nullable=True)
    conselho_uf = db.Column(db.String(2), nullable=True)
    especialidade = db.Column(db.String(100), nullable=True)

    # Certificado digital (ICP-Brasil) — caminho do arquivo .p12/.pfx no servidor
    cert_digital_path = db.Column(db.String(500), nullable=True)
    cert_validade = db.Column(db.DateTime(timezone=True), nullable=True)

    # Controle de acesso
    perfil_id = db.Column(db.Integer, db.ForeignKey("perfis.id"), nullable=False)
    status = db.Column(db.Enum(StatusUsuario), default=StatusUsuario.ATIVO, nullable=False)

    # Controle de senha
    deve_trocar_senha = db.Column(db.Boolean, default=True, nullable=False)
    ultimo_login = db.Column(db.DateTime(timezone=True), nullable=True)
    tentativas_login = db.Column(db.Integer, default=0, nullable=False)
    bloqueado_ate = db.Column(db.DateTime(timezone=True), nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    # Relacionamentos
    perfil = db.relationship("Perfil", back_populates="usuarios")

    # ---------------------------------------------------------------------------
    # Propriedades de senha (hash automático)
    # ---------------------------------------------------------------------------

    @property
    def senha(self):
        raise AttributeError("Senha não é legível.")

    @senha.setter
    def senha(self, senha_plaintext: str) -> None:
        self._senha_hash = bcrypt.generate_password_hash(senha_plaintext).decode("utf-8")

    def verificar_senha(self, senha_plaintext: str) -> bool:
        return bcrypt.check_password_hash(self._senha_hash, senha_plaintext)

    # ---------------------------------------------------------------------------
    # Verificação de permissão
    # ---------------------------------------------------------------------------

    def tem_permissao(self, codigo: str) -> bool:
        """Verifica se o usuário tem a permissão pelo código (ex: 'pacientes.criar')."""
        if self.perfil is None:
            return False
        return self.perfil.tem_permissao(codigo)

    @property
    def is_active(self) -> bool:
        """Flask-Login: usuário está ativo?"""
        return self.status == StatusUsuario.ATIVO

    @property
    def tem_certificado_valido(self) -> bool:
        """Verifica se o usuário possui certificado digital vigente."""
        if not self.cert_digital_path or not self.cert_validade:
            return False
        return self.cert_validade > datetime.now(timezone.utc)

    def registrar_login(self) -> None:
        """Atualiza último login e zera tentativas."""
        self.ultimo_login = datetime.now(timezone.utc)
        self.tentativas_login = 0
        db.session.commit()

    def registrar_tentativa_falha(self) -> None:
        """Incrementa falhas e bloqueia após 5 tentativas."""
        from datetime import timedelta
        self.tentativas_login += 1
        if self.tentativas_login >= 5:
            self.status = StatusUsuario.BLOQUEADO
            self.bloqueado_ate = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.session.commit()

    def __repr__(self):
        return f"<Usuario {self.username} | {self.perfil.nome if self.perfil else 'sem perfil'}>"
