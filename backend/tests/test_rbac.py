"""
tests/test_rbac.py — Testes do RBAC efetivo (Story S-01).

Verifica:
- Usuário sem permissão recebe 403 em rota sensível.
- Usuário com a permissão do perfil acessa (não recebe 403).
- Administrador tem acesso total.
- Rota que exige login redireciona anônimo para o login (não 403).
"""


def _segue_login(client, username):
    resp = client.post(
        "/auth/login",
        data={"username": username, "senha": "Senha@123"},
        follow_redirects=False,
    )
    # 302 = login aceito (redireciona para dashboard)
    assert resp.status_code in (302, 200)


def test_recepcionista_sem_permissao_recebe_403(client):
    """Recepção não tem 'financeiro.ver' → 403 ao acessar financeiro."""
    _segue_login(client, "recep")
    resp = client.get("/financeiro/contas")
    assert resp.status_code == 403


def test_recepcionista_nao_prescreve(client):
    """Recepção não tem 'internacao.prescrever' → 403 na nova prescrição."""
    _segue_login(client, "recep")
    resp = client.get("/internacao/1/prescricao/nova")
    assert resp.status_code == 403


def test_medico_acessa_prescricao(client):
    """Médico tem 'internacao.prescrever' → não recebe 403 (404 se a internação não existir)."""
    _segue_login(client, "medico")
    resp = client.get("/internacao/1/prescricao/nova")
    assert resp.status_code != 403


def test_medico_sem_permissao_financeiro(client):
    """Médico não tem 'financeiro.ver' → 403."""
    _segue_login(client, "medico")
    resp = client.get("/financeiro/contas")
    assert resp.status_code == 403


def test_admin_acesso_total(client):
    """Administrador acessa qualquer módulo (financeiro, RH) sem 403."""
    _segue_login(client, "admin")
    assert client.get("/financeiro/contas").status_code != 403
    assert client.get("/rh/funcionarios").status_code != 403
    assert client.get("/faturamento/guias").status_code != 403


def test_anonimo_redireciona_para_login(client):
    """Usuário não autenticado é redirecionado ao login (302), não recebe 403."""
    resp = client.get("/financeiro/contas", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers.get("Location", "")


def test_recepcionista_acessa_pacientes(client):
    """Recepção tem 'pacientes.ver' → lista de pacientes acessível."""
    _segue_login(client, "recep")
    resp = client.get("/pacientes/")
    assert resp.status_code == 200
