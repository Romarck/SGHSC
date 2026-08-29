"""
tests/conftest.py — Fixtures base para os testes do SGHSC.

Usa TestingConfig (SQLite in-memory, CSRF desabilitado).
"""

import pytest

from app import create_app
from app.extensions import db as _db
from app.models.usuario import Perfil, StatusUsuario, TipoPerfil, Usuario
from app.security.permissoes import seed_permissoes


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        _seed_perfis_e_usuarios()
        seed_permissoes()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _criar_perfil(tipo: TipoPerfil, nome: str) -> Perfil:
    perfil = Perfil(nome=nome, tipo=tipo, descricao=nome)
    _db.session.add(perfil)
    _db.session.flush()
    return perfil


def _criar_usuario(username: str, perfil: Perfil) -> Usuario:
    u = Usuario(
        nome=username.title(),
        email=f"{username}@sghsc.local",
        username=username,
        perfil=perfil,
        deve_trocar_senha=False,
        status=StatusUsuario.ATIVO,
    )
    u.senha = "Senha@123"
    _db.session.add(u)
    _db.session.flush()
    return u


def _seed_perfis_e_usuarios():
    """Cria um usuário por perfil relevante para os testes de RBAC."""
    admin_p = _criar_perfil(TipoPerfil.ADMINISTRADOR, "Administrador")
    medico_p = _criar_perfil(TipoPerfil.MEDICO, "Médico")
    recep_p = _criar_perfil(TipoPerfil.RECEPCIONISTA, "Recepcionista")

    _criar_usuario("admin", admin_p)
    _criar_usuario("medico", medico_p)
    _criar_usuario("recep", recep_p)
    _db.session.commit()


def _login(client, username, senha="Senha@123"):
    return client.post(
        "/auth/login",
        data={"username": username, "senha": senha},
        follow_redirects=False,
    )


@pytest.fixture()
def login(client):
    """Retorna uma função para autenticar um usuário por username."""
    def _do(username):
        return _login(client, username)
    return _do
