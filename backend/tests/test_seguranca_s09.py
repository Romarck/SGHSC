"""
tests/test_seguranca_s09.py — Story S-09.

Cobre:
- Rate limiting no login (POST) e na validação pública → 429 ao exceder.
- Upload de certificado usa nome de arquivo gerado (uuid), não o original.
- Página pública de validação não expõe o título do documento (PII clínica).
"""

import os
import re

import pytest

from app import create_app
from app.extensions import db, limiter
from app.models.usuario import Perfil, StatusUsuario, TipoPerfil, Usuario
from app.security.permissoes import seed_permissoes

# ---------------------------------------------------------------------------
# App dedicado com rate limiting HABILITADO e limites baixos p/ o teste
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_rl():
    app = create_app("testing")
    app.config.update(
        RATELIMIT_ENABLED=True,
        RATELIMIT_STORAGE_URI="memory://",
        RATELIMIT_LOGIN="3 per minute",
        RATELIMIT_VALIDACAO_PUBLICA="3 per minute",
    )
    # Reinicializa o limiter para reler RATELIMIT_ENABLED/STORAGE atualizados
    # (o create_app inicializou com o default do TestingConfig = desabilitado).
    limiter.init_app(app)
    with app.app_context():
        db.create_all()
        # usuário mínimo para o login
        perfil = Perfil(nome="Administrador", tipo=TipoPerfil.ADMINISTRADOR, descricao="Admin")
        db.session.add(perfil)
        db.session.flush()
        u = Usuario(nome="Admin", email="a@sghsc.local", username="admin",
                    perfil=perfil, deve_trocar_senha=False, status=StatusUsuario.ATIVO)
        u.senha = "Senha@123"
        db.session.add(u)
        seed_permissoes()
        db.session.commit()
        try:
            limiter.reset()
        except Exception:
            pass
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client_rl(app_rl):
    return app_rl.test_client()


def test_rate_limit_login_429(client_rl):
    """Após exceder o limite de POSTs de login, retorna 429."""
    codigos = []
    for _ in range(6):
        r = client_rl.post("/auth/login",
                           data={"username": "x", "senha": "y"},
                           follow_redirects=False)
        codigos.append(r.status_code)
    assert 429 in codigos, f"esperava 429 na sequência, obtive {codigos}"


def test_rate_limit_validacao_publica_429(client_rl):
    """A rota pública de validação também é limitada."""
    codigos = [client_rl.get("/certificado/validar").status_code for _ in range(6)]
    assert 429 in codigos, f"esperava 429, obtive {codigos}"


def test_get_login_nao_e_limitado_como_post(client_rl):
    """O GET da tela de login não deve ser bloqueado pelo limite de POST."""
    # Vários GETs seguidos continuam 200 (limite aplica a POST)
    for _ in range(6):
        assert client_rl.get("/auth/login").status_code == 200


# ---------------------------------------------------------------------------
# Upload de certificado: nome uuid (usa a suíte padrão, sem rate limit)
# ---------------------------------------------------------------------------

def test_upload_usa_nome_uuid(client, login, app, tmp_path):
    """O arquivo persistido tem nome uuid.<ext>, sem o nome original."""
    from app.models.certificado import CertificadoDigital
    from app.services import cert_service

    # Gera um .p12 de teste válido para enviar
    p12 = os.path.join(str(tmp_path), "MEU_CERTIFICADO_PESSOAL.p12")
    cert_service.gerar_certificado_teste(p12, senha="sghsc-teste")

    login("admin")
    with open(p12, "rb") as f:
        resp = client.post(
            "/certificado/upload",
            data={"certificado": (f, "MEU_CERTIFICADO_PESSOAL.p12"), "senha": "sghsc-teste"},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
    assert resp.status_code in (302, 200)

    cert = CertificadoDigital.query.order_by(CertificadoDigital.id.desc()).first()
    assert cert is not None
    nome = os.path.basename(cert.arquivo_path)
    # Nome é uuid hex (32 chars) + .p12 e NÃO contém o nome original
    assert re.fullmatch(r"[0-9a-f]{32}\.p12", nome), f"nome inesperado: {nome}"
    assert "CERTIFICADO" not in nome.upper()
    # Limpa o arquivo persistido
    if os.path.exists(cert.arquivo_path):
        os.remove(cert.arquivo_path)


def test_validacao_publica_nao_expoe_titulo(client, app):
    """A página pública não deve renderizar o título do documento (PII)."""
    from app.models.certificado import DocumentoAssinado, TipoDocumentoAssinado

    with app.app_context():
        admin = Usuario.query.filter_by(username="admin").first()
        doc = DocumentoAssinado(
            codigo_validacao="pub123", tipo=TipoDocumentoAssinado.PRESCRICAO_MEDICA,
            titulo="PRESCRICAO DE JOAO DA SILVA CID X",  # contém PII
            hash_documento="abc", pdf_path="/inexistente.pdf", assinante_id=admin.id,
        )
        db.session.add(doc)
        db.session.commit()

    resp = client.get("/certificado/validar/pub123")
    corpo = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "JOAO DA SILVA" not in corpo  # título com PII NÃO aparece
