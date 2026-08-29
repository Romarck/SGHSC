"""
tests/test_auth_hardening.py — Story S-06 (endurecimento de autenticação).

Cobre:
- Mensagem de credencial genérica (sem contador, sem vazar existência do usuário).
- Política de senha (validador puro + fluxo de troca).
- before_request força troca de senha enquanto deve_trocar_senha=True.
- remember me desabilitado por padrão (sem cookie 'remember_token').
"""

from app.extensions import db
from app.models.usuario import Usuario
from app.security.password_policy import COMPRIMENTO_MINIMO, validar_senha

SENHA = "Senha@123"  # senha dos usuários semeados no conftest


# ---------------------------------------------------------------------------
# Mensagens genéricas de login (M-01)
# ---------------------------------------------------------------------------

def _post_login(client, username, senha):
    return client.post(
        "/auth/login",
        data={"username": username, "senha": senha},
        follow_redirects=True,
    )


def test_usuario_inexistente_mensagem_generica(client):
    resp = _post_login(client, "naoexiste", "qualquer")
    corpo = resp.get_data(as_text=True)
    assert "Usuário ou senha inválidos." in corpo
    assert "Tentativas restantes" not in corpo


def test_senha_errada_mensagem_generica_sem_contador(client):
    resp = _post_login(client, "medico", "senha-errada")
    corpo = resp.get_data(as_text=True)
    assert "Usuário ou senha inválidos." in corpo
    assert "Tentativas restantes" not in corpo


def test_inexistente_e_senha_errada_indistinguiveis(client):
    """As duas falhas devem produzir exatamente a mesma mensagem (anti-enumeração)."""
    r1 = _post_login(client, "naoexiste", "x").get_data(as_text=True)
    r2 = _post_login(client, "medico", "errada").get_data(as_text=True)
    assert ("Usuário ou senha inválidos." in r1) and ("Usuário ou senha inválidos." in r2)


# ---------------------------------------------------------------------------
# Política de senha (M-02) — validador puro
# ---------------------------------------------------------------------------

def test_politica_rejeita_curta():
    assert validar_senha("Ab1@x")  # < 10 chars → há erros

def test_politica_rejeita_sem_complexidade():
    # 10+ chars mas só uma classe (minúsculas)
    assert validar_senha("abcdefghij")

def test_politica_rejeita_senha_comum():
    assert validar_senha("senha123")  # está na blocklist (mesmo com classes)

def test_politica_rejeita_username_na_senha():
    erros = validar_senha("Medico#2026", username="medico")
    assert any("usuário" in e.lower() for e in erros)

def test_politica_aceita_senha_forte():
    assert validar_senha("Xk9!vLmq2R", username="medico") == []

def test_comprimento_minimo_e_dez():
    assert COMPRIMENTO_MINIMO >= 10


# ---------------------------------------------------------------------------
# Política de senha — fluxo de troca
# ---------------------------------------------------------------------------

def test_troca_rejeita_senha_fraca(client, login):
    login("admin")
    resp = client.post(
        "/auth/trocar-senha",
        data={"senha_atual": SENHA, "nova_senha": "fraca123", "confirmar_senha": "fraca123"},
        follow_redirects=True,
    )
    # Continua na tela de troca (senha não aceita)
    assert b"senha" in resp.get_data().lower()
    # A senha do usuário não mudou
    u = Usuario.query.filter_by(username="admin").first()
    assert u.verificar_senha(SENHA)

def test_troca_aceita_senha_forte(client, login):
    login("admin")
    nova = "Xk9!vLmq2R"
    resp = client.post(
        "/auth/trocar-senha",
        data={"senha_atual": SENHA, "nova_senha": nova, "confirmar_senha": nova},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    u = Usuario.query.filter_by(username="admin").first()
    assert u.verificar_senha(nova)
    assert u.deve_trocar_senha is False


# ---------------------------------------------------------------------------
# before_request força troca de senha (sessão ativa)
# ---------------------------------------------------------------------------

def test_forca_troca_de_senha_em_sessao_ativa(client, login):
    login("recep")
    # Liga a flag durante a sessão ativa
    u = Usuario.query.filter_by(username="recep").first()
    u.deve_trocar_senha = True
    db.session.commit()

    # Qualquer rota protegida deve redirecionar para a troca de senha
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/trocar-senha" in resp.headers.get("Location", "")

def test_rota_troca_senha_nao_entra_em_loop(client, login):
    login("recep")
    u = Usuario.query.filter_by(username="recep").first()
    u.deve_trocar_senha = True
    db.session.commit()
    # A própria rota de troca deve responder 200 (isenta do redirect)
    resp = client.get("/auth/trocar-senha")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# remember me desabilitado por padrão (B-01)
# ---------------------------------------------------------------------------

def test_remember_me_desabilitado_por_padrao(client, app):
    assert app.config.get("LOGIN_REMEMBER_HABILITADO") is False
    client.post(
        "/auth/login",
        data={"username": "admin", "senha": SENHA, "lembrar": "y"},
        follow_redirects=False,
    )
    # Não deve haver cookie persistente 'remember_token'
    cookies = client.get_cookie("remember_token")
    assert cookies is None
