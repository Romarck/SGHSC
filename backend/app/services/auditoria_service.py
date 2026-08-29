"""
services/auditoria_service.py — Serviço de trilha de auditoria LGPD (Story S-07).

Uso nas rotas de leitura de dados sensíveis:

    from ..services.auditoria_service import registrar_acesso
    from ..models.auditoria import AcaoAuditoria
    ...
    registrar_acesso(AcaoAuditoria.VISUALIZAR, paciente_id=p.id,
                     recurso="pacientes.detalhe", recurso_id=p.id)

Princípios:
- **Resiliente:** uma falha ao gravar auditoria NUNCA deve quebrar o request
  principal. Erros são capturados e apenas logados.
- **Confiável:** registra o usuário autenticado, IP e user-agent do request.
"""

from datetime import datetime, timedelta, timezone

from flask import current_app, request
from flask_login import current_user

from ..extensions import db
from ..models.auditoria import AcaoAuditoria, LogAcesso


def _client_ip() -> str | None:
    """
    IP do cliente. Com ProxyFix ativo (produção), request.remote_addr já reflete
    o X-Forwarded-For confiável. Mantemos um fallback defensivo ao header.
    """
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        # primeiro IP da cadeia é o cliente original
        return fwd.split(",")[0].strip()[:64]
    return (request.remote_addr or None)


def registrar_acesso(
    acao: AcaoAuditoria,
    *,
    paciente_id: int = None,
    recurso: str = None,
    recurso_id=None,
    detalhe: str = None,
) -> None:
    """
    Grava um evento de auditoria de acesso. Nunca levanta exceção para o chamador.

    Args:
        acao: tipo de ação (AcaoAuditoria).
        paciente_id: paciente cujos dados foram acessados (se aplicável).
        recurso: identificador do recurso/rota (ex.: "internacao.prontuario").
        recurso_id: id do objeto acessado.
        detalhe: informação extra opcional.
    """
    try:
        if not getattr(current_user, "is_authenticated", False):
            return  # sem usuário autenticado não há o que atribuir

        recurso = recurso or (request.endpoint or "desconhecido")

        log = LogAcesso(
            usuario_id=current_user.id,
            usuario_username=getattr(current_user, "username", None),
            paciente_id=paciente_id,
            acao=acao,
            recurso=recurso[:120],
            recurso_id=(str(recurso_id)[:60] if recurso_id is not None else None),
            detalhe=(detalhe[:255] if detalhe else None),
            ip=_client_ip(),
            user_agent=(request.headers.get("User-Agent", "")[:300] or None),
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:  # resiliência: auditoria não pode derrubar o request
        try:
            db.session.rollback()
        except Exception:
            pass
        current_app.logger.error(f"Falha ao registrar auditoria de acesso: {e}")


# ---------------------------------------------------------------------------
# Consultas da trilha (para o relatório)
# ---------------------------------------------------------------------------

def trilha_por_paciente(paciente_id: int, limite: int = 200):
    """Retorna os acessos ao prontuário/dados de um paciente (mais recentes primeiro)."""
    return (
        LogAcesso.query
        .filter_by(paciente_id=paciente_id)
        .order_by(LogAcesso.registrado_em.desc())
        .limit(limite)
        .all()
    )


def trilha_por_usuario(usuario_id: int, limite: int = 200):
    """Retorna os acessos feitos por um usuário (mais recentes primeiro)."""
    return (
        LogAcesso.query
        .filter_by(usuario_id=usuario_id)
        .order_by(LogAcesso.registrado_em.desc())
        .limit(limite)
        .all()
    )


# ---------------------------------------------------------------------------
# Retenção (política): remoção em bloco de registros vencidos
# ---------------------------------------------------------------------------

def purgar_logs_vencidos(dias_retencao: int = None) -> int:
    """
    Remove logs de auditoria mais antigos que o prazo de retenção.

    Prazo padrão vem de config `AUDITORIA_RETENCAO_DIAS`. Retorna a contagem
    removida. Destinado a ser chamado por rotina/CLI, não pela aplicação comum.
    """
    if dias_retencao is None:
        dias_retencao = current_app.config.get("AUDITORIA_RETENCAO_DIAS", 1825)
    limite = datetime.now(timezone.utc) - timedelta(days=dias_retencao)
    removidos = (
        LogAcesso.query
        .filter(LogAcesso.registrado_em < limite)
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return removidos
