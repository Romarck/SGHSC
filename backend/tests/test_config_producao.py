"""
tests/test_config_producao.py — Story S-04.

Garante que a aplicação valida a configuração de produção no boot:
- Falha rápido se faltar SECRET_KEY / DATABASE_URL / POSTGRES_PASSWORD.
- Falha se SECRET_KEY for o fallback default/placeholder.
- Sobe normalmente quando os segredos válidos estão presentes.
- Dev/test continuam funcionando com defaults.
"""

import pytest

from app import create_app

# Conjunto mínimo de segredos válidos para produção
VALID_ENV = {
    "SECRET_KEY": "a" * 64,  # valor forte (não é o default)
    "DATABASE_URL": "postgresql://u:p@db:5432/sghsc",
    "POSTGRES_PASSWORD": "senha-forte-de-teste",
}


@pytest.fixture()
def prod_env(monkeypatch):
    """Aplica um ambiente de produção limpo e configurável por teste."""
    monkeypatch.setenv("FLASK_ENV", "production")
    # Garante estado conhecido (remove qualquer resíduo do ambiente real)
    for key in VALID_ENV:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_producao_falha_sem_segredos(prod_env):
    """Sem SECRET_KEY/DATABASE_URL/POSTGRES_PASSWORD deve falhar no boot."""
    with pytest.raises(RuntimeError) as exc:
        create_app("production")
    msg = str(exc.value)
    assert "SECRET_KEY" in msg
    assert "DATABASE_URL" in msg
    assert "POSTGRES_PASSWORD" in msg


def test_producao_falha_com_secret_key_default(prod_env):
    """SECRET_KEY com o valor default hardcoded deve ser rejeitado."""
    for key, value in VALID_ENV.items():
        prod_env.setenv(key, value)
    prod_env.setenv("SECRET_KEY", "troque-antes-de-produção")

    with pytest.raises(RuntimeError) as exc:
        create_app("production")
    assert "SECRET_KEY" in str(exc.value)
    assert "default" in str(exc.value) or "previsível" in str(exc.value)


def test_producao_falha_com_placeholder_env_example(prod_env):
    """O placeholder do .env.example também é proibido."""
    for key, value in VALID_ENV.items():
        prod_env.setenv(key, value)
    prod_env.setenv("SECRET_KEY", "TROQUE_PARA_UM_VALOR_SECRETO_FORTE")

    with pytest.raises(RuntimeError):
        create_app("production")


def test_producao_sobe_com_segredos_validos(prod_env):
    """Com segredos válidos, a aplicação deve subir e ser segura."""
    for key, value in VALID_ENV.items():
        prod_env.setenv(key, value)

    app = create_app("production")
    assert app is not None
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SECRET_KEY"] == VALID_ENV["SECRET_KEY"]


def test_dev_sobe_sem_segredos(monkeypatch):
    """Dev continua funcionando com defaults (sem validação estrita)."""
    for key in VALID_ENV:
        monkeypatch.delenv(key, raising=False)
    app = create_app("development")
    assert app is not None
    assert app.config["SESSION_COOKIE_SECURE"] is False
