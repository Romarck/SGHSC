"""
utils/authz.py — Autorização por permissão (RBAC efetivo).

Fornece o decorator `requer_permissao("modulo.acao")` que complementa o
`@login_required` do Flask-Login: além de autenticado, o usuário precisa ter a
permissão exigida no seu Perfil.

Story S-01 — @si C-01 / @architect S1.

Uso:
    from ..utils.authz import requer_permissao

    @bp.route("/contas/nova", methods=["GET", "POST"])
    @login_required
    @requer_permissao("financeiro.criar")
    def nova_conta():
        ...

Regras:
- O perfil ADMINISTRADOR tem acesso total (curto-circuito) — ver Usuario.tem_permissao
  não trata isso, então o decorator verifica explicitamente.
- Sem a permissão → HTTP 403 (renderiza templates/errors/403.html) e o evento é logado.
- Não substitui `@login_required`; deve vir logo abaixo dele.
"""

from functools import wraps

from flask import abort, current_app
from flask_login import current_user

from ..models.usuario import TipoPerfil


def requer_permissao(codigo: str):
    """
    Exige que o usuário autenticado possua a permissão `codigo` (formato
    'modulo.acao'). O perfil Administrador é sempre autorizado.
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            # Deve estar autenticado (garantido por @login_required, mas defendemos aqui também)
            if not current_user.is_authenticated:
                abort(401)

            if not _usuario_autorizado(current_user, codigo):
                current_app.logger.warning(
                    "Acesso negado (RBAC): usuário=%s perfil=%s permissão exigida=%s",
                    getattr(current_user, "username", "?"),
                    getattr(getattr(current_user, "perfil", None), "nome", "sem perfil"),
                    codigo,
                )
                abort(403)

            return view(*args, **kwargs)

        return wrapped

    return decorator


def _usuario_autorizado(usuario, codigo: str) -> bool:
    """Administrador tem acesso total; demais dependem de tem_permissao()."""
    perfil = getattr(usuario, "perfil", None)
    if perfil is not None and perfil.tipo == TipoPerfil.ADMINISTRADOR:
        return True
    return usuario.tem_permissao(codigo)


def _is_admin(usuario) -> bool:
    perfil = getattr(usuario, "perfil", None)
    return perfil is not None and perfil.tipo == TipoPerfil.ADMINISTRADOR


def autorizar_recurso(*, dono_id: int = None, permissoes: tuple[str, ...] = ()) -> None:
    """
    Autorização ao nível do OBJETO (evita IDOR/BOLA — Story S-02).

    Concede acesso ao recurso quando qualquer condição for verdadeira:
      - o usuário é ADMINISTRADOR; ou
      - o usuário é o "dono" do recurso (dono_id == current_user.id); ou
      - o usuário possui pelo menos uma das `permissoes` de módulo informadas.

    Caso contrário, aborta com **403** e registra o evento no log.

    Deve ser chamada dentro de uma view protegida por @login_required, antes de
    servir o recurso (ex.: send_file). Complementa a permissão de módulo do
    decorator: garante que apenas quem tem vínculo/permissão acesse o objeto.
    """
    if not current_user.is_authenticated:
        abort(401)

    if _is_admin(current_user):
        return

    if dono_id is not None and getattr(current_user, "id", None) == dono_id:
        return

    if permissoes and any(current_user.tem_permissao(p) for p in permissoes):
        return

    current_app.logger.warning(
        "Acesso negado a recurso (IDOR/RBAC): usuário=%s perfil=%s "
        "dono_id=%s permissões aceitas=%s",
        getattr(current_user, "username", "?"),
        getattr(getattr(current_user, "perfil", None), "nome", "sem perfil"),
        dono_id, permissoes,
    )
    abort(403)
