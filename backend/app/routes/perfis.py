"""
routes/perfis.py — Administração de perfis de acesso e suas permissões (RBAC).

Somente para 'usuarios.gerir' (Administrador). Permite criar/editar perfis e
marcar, por checkbox, quais permissões cada perfil possui (RBAC dinâmico).

Travas de segurança:
  - O perfil ADMINISTRADOR não é editável/excluível (tem acesso total via decorator).
  - Não exclui perfil com usuários vinculados.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models.usuario import Perfil, Permissao, TipoPerfil
from ..security.permissoes import CATALOGO
from ..utils.authz import requer_permissao

bp = Blueprint("perfis", __name__)


def _permissoes_por_modulo():
    """Agrupa o catálogo de permissões por módulo, para montar os checkboxes."""
    grupos: dict[str, list[tuple[str, str]]] = {}
    for codigo, descricao in CATALOGO.items():
        modulo = codigo.split(".", 1)[0]
        grupos.setdefault(modulo, []).append((codigo, descricao))
    return dict(sorted(grupos.items()))


def _is_admin_perfil(perfil: Perfil) -> bool:
    return perfil.tipo == TipoPerfil.ADMINISTRADOR


@bp.route("/")
@login_required
@requer_permissao("usuarios.gerir")
def listar():
    perfis = Perfil.query.order_by(Perfil.nome).all()
    # contagem de usuários por perfil (para exibir e travar exclusão)
    dados = [(p, p.usuarios.count(), len(p.permissoes)) for p in perfis]
    return render_template("perfis/lista.html", dados=dados, TipoPerfil=TipoPerfil)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("usuarios.gerir")
def novo():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        descricao = (request.form.get("descricao") or "").strip()
        codigos = request.form.getlist("permissoes")

        if not nome:
            flash("Informe o nome do perfil.", "danger")
            return render_template("perfis/form.html", perfil=None,
                                   grupos=_permissoes_por_modulo(), marcadas=set(codigos),
                                   titulo="Novo Perfil")
        if Perfil.query.filter_by(nome=nome).first():
            flash("Já existe um perfil com esse nome.", "danger")
            return render_template("perfis/form.html", perfil=None,
                                   grupos=_permissoes_por_modulo(), marcadas=set(codigos),
                                   titulo="Novo Perfil")

        perfil = Perfil(nome=nome, descricao=descricao, tipo=None, ativo=True)
        # tipo=None: perfil customizado (não é um dos padrão do enum)
        validos = [c for c in codigos if c in CATALOGO]
        perfil.permissoes = Permissao.query.filter(Permissao.codigo.in_(validos)).all()
        db.session.add(perfil)
        db.session.commit()
        flash(f"Perfil '{perfil.nome}' criado com {len(perfil.permissoes)} permissão(ões).", "success")
        return redirect(url_for("perfis.listar"))

    return render_template("perfis/form.html", perfil=None,
                           grupos=_permissoes_por_modulo(), marcadas=set(),
                           titulo="Novo Perfil")


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@requer_permissao("usuarios.gerir")
def editar(id: int):
    perfil = db.get_or_404(Perfil, id)

    if _is_admin_perfil(perfil):
        flash("O perfil Administrador tem acesso total e não é editável.", "info")
        return redirect(url_for("perfis.listar"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        descricao = (request.form.get("descricao") or "").strip()
        codigos = request.form.getlist("permissoes")

        dup = Perfil.query.filter(Perfil.nome == nome, Perfil.id != perfil.id).first()
        if not nome or dup:
            flash("Nome inválido ou já utilizado por outro perfil.", "danger")
            return render_template("perfis/form.html", perfil=perfil,
                                   grupos=_permissoes_por_modulo(), marcadas=set(codigos),
                                   titulo="Editar Perfil")

        perfil.nome = nome
        perfil.descricao = descricao
        validos = [c for c in codigos if c in CATALOGO]
        perfil.permissoes = Permissao.query.filter(Permissao.codigo.in_(validos)).all()
        db.session.commit()
        flash(f"Perfil '{perfil.nome}' atualizado ({len(perfil.permissoes)} permissões).", "success")
        return redirect(url_for("perfis.listar"))

    marcadas = {p.codigo for p in perfil.permissoes}
    return render_template("perfis/form.html", perfil=perfil,
                           grupos=_permissoes_por_modulo(), marcadas=marcadas,
                           titulo="Editar Perfil")


@bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
@requer_permissao("usuarios.gerir")
def excluir(id: int):
    perfil = db.get_or_404(Perfil, id)
    if _is_admin_perfil(perfil):
        flash("O perfil Administrador não pode ser excluído.", "warning")
        return redirect(url_for("perfis.listar"))
    if perfil.usuarios.count() > 0:
        flash(
            f"O perfil '{perfil.nome}' tem usuários vinculados. "
            "Migre-os para outro perfil antes de excluir.",
            "warning",
        )
        return redirect(url_for("perfis.listar"))
    db.session.delete(perfil)
    db.session.commit()
    flash(f"Perfil '{perfil.nome}' excluído.", "info")
    return redirect(url_for("perfis.listar"))
