"""
tests/test_idor.py — Testes de autorização ao nível do objeto (Story S-02).

Verifica que downloads de documento por id não são acessíveis via IDOR/BOLA:
- dono do documento acessa (mesmo sem permissão de módulo);
- usuário com permissão de certificação acessa;
- usuário sem vínculo nem permissão recebe 403 (não 404);
- anônimo é redirecionado ao login.
"""

import os

from app.extensions import db
from app.models.certificado import DocumentoAssinado, StatusDocumento, TipoDocumentoAssinado
from app.models.usuario import Usuario


def _login(client, username):
    return client.post(
        "/auth/login",
        data={"username": username, "senha": "Senha@123"},
        follow_redirects=False,
    )


def _criar_documento(app, assinante_username, pdf_existe=False):
    """Cria um DocumentoAssinado atribuído ao usuário informado."""
    with app.app_context():
        assinante = Usuario.query.filter_by(username=assinante_username).one()
        pdf_path = "/tmp/sghsc_doc_teste.pdf"
        if pdf_existe:
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 teste")
        doc = DocumentoAssinado(
            codigo_validacao="codigoteste123",
            tipo=TipoDocumentoAssinado.LAUDO_EXAME,
            titulo="Documento de teste",
            hash_documento="0" * 64,
            pdf_path=pdf_path,
            assinante_id=assinante.id,
            status=StatusDocumento.ASSINADO,
        )
        db.session.add(doc)
        db.session.commit()
        return doc.id


def test_recepcionista_sem_permissao_nao_baixa_documento_de_outro(app, client):
    """Recepção não é dona e não tem 'certificado.usar' → 403 (não 404)."""
    doc_id = _criar_documento(app, "medico", pdf_existe=True)
    _login(client, "recep")
    resp = client.get(f"/certificado/documento/{doc_id}/pdf")
    assert resp.status_code == 403


def test_403_antes_de_checar_existencia_do_arquivo(app, client):
    """Mesmo sem o arquivo em disco, usuário não autorizado recebe 403 (não 404),
    para não vazar a existência do documento."""
    doc_id = _criar_documento(app, "medico", pdf_existe=False)
    _login(client, "recep")
    resp = client.get(f"/certificado/documento/{doc_id}/pdf")
    assert resp.status_code == 403


def test_dono_baixa_proprio_documento(app, client):
    """A recepcionista é a assinante → acessa o próprio documento (não 403)."""
    doc_id = _criar_documento(app, "recep", pdf_existe=True)
    _login(client, "recep")
    resp = client.get(f"/certificado/documento/{doc_id}/pdf")
    assert resp.status_code != 403


def test_usuario_com_permissao_certificado_acessa(app, client):
    """Médico tem 'certificado.usar' → acessa documento de outro assinante (não 403)."""
    doc_id = _criar_documento(app, "recep", pdf_existe=True)
    _login(client, "medico")
    resp = client.get(f"/certificado/documento/{doc_id}/pdf")
    assert resp.status_code != 403


def test_admin_acessa_qualquer_documento(app, client):
    doc_id = _criar_documento(app, "recep", pdf_existe=True)
    _login(client, "admin")
    resp = client.get(f"/certificado/documento/{doc_id}/pdf")
    assert resp.status_code != 403


def test_anonimo_redireciona_login(app, client):
    doc_id = _criar_documento(app, "medico", pdf_existe=True)
    resp = client.get(f"/certificado/documento/{doc_id}/pdf", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers.get("Location", "")
