"""
tests/test_auditoria_lgpd.py — Story S-07 (trilha de auditoria de acesso LGPD).

Cobre:
- Visualização de dados de paciente gera LogAcesso (usuário, paciente, ação, IP).
- Consulta da trilha por paciente (relatório) — protegida por permissão.
- Trilha por usuário.
- Serviço de auditoria é resiliente (não quebra o request).
- criado_por_id de Paciente é NOT NULL.
"""

from datetime import date

import pytest

from app.extensions import db
from app.models.auditoria import AcaoAuditoria, LogAcesso
from app.models.paciente import Paciente, Sexo
from app.models.usuario import Usuario
from app.services.auditoria_service import registrar_acesso, trilha_por_paciente

SENHA = "Senha@123"


def _criar_paciente(criado_por_username="admin"):
    autor = Usuario.query.filter_by(username=criado_por_username).first()
    p = Paciente(
        nome="PACIENTE TESTE",
        data_nascimento=date(1990, 1, 1),
        sexo=Sexo.MASCULINO,
        criado_por_id=autor.id,
    )
    db.session.add(p)
    db.session.commit()
    return p


# ---------------------------------------------------------------------------
# Registro de acesso em visualização
# ---------------------------------------------------------------------------

def test_visualizar_paciente_gera_log(client, login):
    p = _criar_paciente()
    login("recep")  # recepcionista tem pacientes.ver
    assert LogAcesso.query.count() == 0

    resp = client.get(f"/pacientes/{p.id}")
    assert resp.status_code == 200

    logs = LogAcesso.query.all()
    assert len(logs) == 1
    log = logs[0]
    assert log.paciente_id == p.id
    assert log.acao == AcaoAuditoria.VISUALIZAR
    assert log.recurso == "pacientes.detalhe"
    assert log.usuario_username == "recep"
    assert log.ip is not None  # cliente de teste envia 127.0.0.1


def test_multiplos_acessos_geram_multiplos_logs(client, login):
    p = _criar_paciente()
    login("recep")
    client.get(f"/pacientes/{p.id}")
    client.get(f"/pacientes/{p.id}")
    assert LogAcesso.query.filter_by(paciente_id=p.id).count() == 2


# ---------------------------------------------------------------------------
# Consulta da trilha (relatório) — permissão
# ---------------------------------------------------------------------------

def test_trilha_por_paciente_admin_ve(client, login):
    p = _criar_paciente()
    login("recep")
    client.get(f"/pacientes/{p.id}")  # gera um acesso da recep

    client.get("/auth/logout")  # troca de sessão: sai da recep antes de entrar como admin
    login("admin")  # admin tem acesso total
    resp = client.get(f"/auditoria/?paciente_id={p.id}")
    assert resp.status_code == 200
    corpo = resp.get_data(as_text=True)
    assert "recep" in corpo  # o acesso da recepcionista aparece na trilha


def test_trilha_negada_sem_permissao(client, login):
    # recepcionista NÃO tem auditoria.ver → 403
    login("recep")
    resp = client.get("/auditoria/")
    assert resp.status_code == 403


def test_trilha_anonimo_redireciona_login(client):
    resp = client.get("/auditoria/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers.get("Location", "")


# ---------------------------------------------------------------------------
# Consulta por serviço
# ---------------------------------------------------------------------------

def test_trilha_por_paciente_service(client, login):
    p = _criar_paciente()
    login("medico")
    client.get(f"/pacientes/{p.id}")
    logs = trilha_por_paciente(p.id)
    assert len(logs) == 1 and logs[0].usuario_username == "medico"


# ---------------------------------------------------------------------------
# Resiliência: auditoria não pode quebrar o request
# ---------------------------------------------------------------------------

def test_registrar_acesso_resiliente(app):
    """Mesmo com erro interno, registrar_acesso não levanta para o chamador."""
    with app.test_request_context("/"):
        # Sem usuário autenticado no contexto → simplesmente não grava, sem erro.
        registrar_acesso(AcaoAuditoria.VISUALIZAR, paciente_id=1, recurso="x")
    # Se chegou aqui, não levantou exceção.
    assert True


# ---------------------------------------------------------------------------
# criado_por_id NOT NULL
# ---------------------------------------------------------------------------

def test_paciente_criado_por_id_not_null(app):
    coluna = Paciente.__table__.c.criado_por_id
    assert coluna.nullable is False
