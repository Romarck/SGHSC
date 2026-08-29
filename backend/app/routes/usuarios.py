"""
routes/usuarios.py — Administração de usuários do sistema.

Somente para quem tem 'usuarios.gerir' (na prática, Administrador). Permite
listar, criar, editar, ativar/desativar e resetar a senha de usuários.

Reusa a política de senha (S-06) e registra o autor em criado_por_id (S-07).
"""

import secrets

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

from ..extensions import db
from ..models.usuario import Perfil, StatusUsuario, Usuario
from ..security.password_policy import validar_senha
from ..utils.authz import requer_permissao

bp = Blueprint("usuarios", __name__)


class UsuarioForm(FlaskForm):
    nome = StringField("Nome completo", validators=[DataRequired(), Length(max=150)])
    # check_deliverability=False: aceita domínios internos (ex.: @santacasa.local)
    # sem consultar DNS/MX — só valida o formato user@dominio.
    email = StringField(
        "E-mail",
        validators=[DataRequired(), Email(check_deliverability=False), Length(max=150)],
    )
    username = StringField("Usuário (login)", validators=[DataRequired(), Length(min=3, max=50)])
    perfil_id = SelectField("Perfil de acesso", validators=[DataRequired()], coerce=int)
    cpf = StringField("CPF", validators=[Optional(), Length(max=14)])
    conselho_tipo = StringField("Conselho (CRM/COREN...)", validators=[Optional(), Length(max=10)])
    conselho_numero = StringField("Nº do conselho", validators=[Optional(), Length(max=30)])
    conselho_uf = StringField("UF do conselho", validators=[Optional(), Length(max=2)])
    especialidade = StringField("Especialidade", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Salvar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.perfil_id.choices = [
            (p.id, p.nome) for p in Perfil.query.filter_by(ativo=True).order_by(Perfil.nome)
        ]


def _senha_temporaria() -> str:
    """Gera uma senha temporária forte que satisfaz a política (S-06)."""
    # token_urlsafe garante comprimento/complexidade; garantimos os tipos.
    return "Tmp!" + secrets.token_urlsafe(9)


@bp.route("/")
@login_required
@requer_permissao("usuarios.gerir")
def listar():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template("usuarios/lista.html", usuarios=usuarios, StatusUsuario=StatusUsuario)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("usuarios.gerir")
def novo():
    form = UsuarioForm()
    if form.validate_on_submit():
        # Unicidade
        if Usuario.query.filter_by(username=form.username.data.strip()).first():
            flash("Já existe um usuário com esse login.", "danger")
            return render_template("usuarios/form.html", form=form, titulo="Novo Usuário", senha_temp=None)
        if Usuario.query.filter_by(email=form.email.data.strip().lower()).first():
            flash("Já existe um usuário com esse e-mail.", "danger")
            return render_template("usuarios/form.html", form=form, titulo="Novo Usuário", senha_temp=None)

        senha_temp = _senha_temporaria()
        u = Usuario(
            nome=form.nome.data.strip(),
            email=form.email.data.strip().lower(),
            username=form.username.data.strip(),
            perfil_id=form.perfil_id.data,
            cpf=form.cpf.data or None,
            conselho_tipo=form.conselho_tipo.data or None,
            conselho_numero=form.conselho_numero.data or None,
            conselho_uf=(form.conselho_uf.data or None),
            especialidade=form.especialidade.data or None,
            status=StatusUsuario.ATIVO,
            deve_trocar_senha=True,           # troca obrigatória no 1º acesso (S-06)
            criado_por_id=current_user.id,    # trilha de escrita (S-07)
        )
        u.senha = senha_temp
        db.session.add(u)
        db.session.commit()
        # Mostra a senha temporária UMA vez para o admin repassar ao usuário.
        flash(
            f"Usuário '{u.username}' criado. Senha temporária: {senha_temp} "
            f"(será trocada no primeiro acesso). Anote e repasse com segurança.",
            "success",
        )
        return redirect(url_for("usuarios.listar"))

    return render_template("usuarios/form.html", form=form, titulo="Novo Usuário", senha_temp=None)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@requer_permissao("usuarios.gerir")
def editar(id: int):
    u = db.get_or_404(Usuario, id)
    form = UsuarioForm(obj=u)
    if request.method == "GET":
        form.perfil_id.data = u.perfil_id

    if form.validate_on_submit():
        # Unicidade (ignorando o próprio registro)
        dup_user = Usuario.query.filter(Usuario.username == form.username.data.strip(), Usuario.id != u.id).first()
        dup_mail = Usuario.query.filter(Usuario.email == form.email.data.strip().lower(), Usuario.id != u.id).first()
        if dup_user:
            flash("Já existe outro usuário com esse login.", "danger")
            return render_template("usuarios/form.html", form=form, titulo="Editar Usuário", senha_temp=None)
        if dup_mail:
            flash("Já existe outro usuário com esse e-mail.", "danger")
            return render_template("usuarios/form.html", form=form, titulo="Editar Usuário", senha_temp=None)

        u.nome = form.nome.data.strip()
        u.email = form.email.data.strip().lower()
        u.username = form.username.data.strip()
        u.perfil_id = form.perfil_id.data
        u.cpf = form.cpf.data or None
        u.conselho_tipo = form.conselho_tipo.data or None
        u.conselho_numero = form.conselho_numero.data or None
        u.conselho_uf = form.conselho_uf.data or None
        u.especialidade = form.especialidade.data or None
        db.session.commit()
        flash("Usuário atualizado.", "success")
        return redirect(url_for("usuarios.listar"))

    return render_template("usuarios/form.html", form=form, titulo="Editar Usuário", senha_temp=None)


@bp.route("/<int:id>/status", methods=["POST"])
@login_required
@requer_permissao("usuarios.gerir")
def alternar_status(id: int):
    u = db.get_or_404(Usuario, id)
    if u.id == current_user.id:
        flash("Você não pode desativar o próprio usuário.", "warning")
        return redirect(url_for("usuarios.listar"))
    if u.status == StatusUsuario.ATIVO:
        u.status = StatusUsuario.INATIVO
        flash(f"Usuário '{u.username}' desativado.", "info")
    else:
        u.status = StatusUsuario.ATIVO
        u.tentativas_login = 0
        u.bloqueado_ate = None
        flash(f"Usuário '{u.username}' reativado.", "success")
    db.session.commit()
    return redirect(url_for("usuarios.listar"))


@bp.route("/<int:id>/resetar-senha", methods=["POST"])
@login_required
@requer_permissao("usuarios.gerir")
def resetar_senha(id: int):
    u = db.get_or_404(Usuario, id)
    senha_temp = _senha_temporaria()
    # Garantia extra: valida contra a política (deve sempre passar).
    if validar_senha(senha_temp, username=u.username):
        senha_temp = "Tmp!" + secrets.token_urlsafe(12)
    u.senha = senha_temp
    u.deve_trocar_senha = True
    u.tentativas_login = 0
    u.bloqueado_ate = None
    if u.status == StatusUsuario.BLOQUEADO:
        u.status = StatusUsuario.ATIVO
    db.session.commit()
    flash(
        f"Senha de '{u.username}' redefinida. Nova senha temporária: {senha_temp} "
        f"(troca obrigatória no próximo acesso).",
        "success",
    )
    return redirect(url_for("usuarios.listar"))
