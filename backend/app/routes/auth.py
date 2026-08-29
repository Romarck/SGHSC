"""
routes/auth.py — Blueprint de autenticação.

Rotas: login, logout, troca de senha obrigatória.
"""

from datetime import datetime, timezone

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length

from ..extensions import db, limiter
from ..models.usuario import StatusUsuario, Usuario
from ..security.password_policy import SenhaForte, validar_senha

bp = Blueprint("auth", __name__)

# Mensagem genérica única para qualquer falha de credencial (evita enumeração)
MSG_CREDENCIAL_INVALIDA = "Usuário ou senha inválidos."


# ---------------------------------------------------------------------------
# Formulários
# ---------------------------------------------------------------------------

class LoginForm(FlaskForm):
    username = StringField(
        "Usuário",
        validators=[DataRequired(message="Informe o usuário."), Length(min=3, max=50)]
    )
    senha = PasswordField(
        "Senha",
        validators=[DataRequired(message="Informe a senha.")]
    )
    lembrar = BooleanField("Manter conectado")
    submit = SubmitField("Entrar")


class TrocarSenhaForm(FlaskForm):
    senha_atual = PasswordField(
        "Senha atual",
        validators=[DataRequired()]
    )
    nova_senha = PasswordField(
        "Nova senha",
        validators=[
            DataRequired(),
            SenhaForte(),  # comprimento >=10 + complexidade + blocklist
        ]
    )
    confirmar_senha = PasswordField(
        "Confirmar nova senha",
        validators=[
            DataRequired(),
            EqualTo("nova_senha", message="As senhas não coincidem.")
        ]
    )
    submit = SubmitField("Alterar senha")


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
@limiter.limit(
    lambda: current_app.config.get("RATELIMIT_LOGIN", "10 per minute"),
    methods=["POST"],  # limita apenas as tentativas (POST), não o GET da tela
)
def login():
    """Tela de login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(username=form.username.data.strip()).first()

        # Usuário não encontrado — mesma resposta genérica de senha inválida,
        # para não permitir enumeração de usuários (M-01).
        if usuario is None:
            flash(MSG_CREDENCIAL_INVALIDA, "danger")
            current_app.logger.warning(
                f"Tentativa de login com usuário inexistente: {form.username.data}"
            )
            return render_template("auth/login.html", form=form)

        # Conta bloqueada por excesso de tentativas
        if usuario.status == StatusUsuario.BLOQUEADO:
            if usuario.bloqueado_ate and usuario.bloqueado_ate > datetime.now(timezone.utc):
                flash(
                    "Conta temporariamente bloqueada por excesso de tentativas. "
                    "Tente novamente mais tarde ou contate o administrador.",
                    "danger"
                )
                return render_template("auth/login.html", form=form)
            else:
                # Desbloqueio automático após o tempo
                usuario.status = StatusUsuario.ATIVO
                usuario.tentativas_login = 0
                db.session.commit()

        # Conta inativa
        if usuario.status == StatusUsuario.INATIVO:
            flash("Conta inativa. Contate o administrador.", "warning")
            return render_template("auth/login.html", form=form)

        # Senha incorreta — mensagem genérica, SEM contador de tentativas (M-01).
        # O bloqueio após 5 falhas continua ativo silenciosamente.
        if not usuario.verificar_senha(form.senha.data):
            usuario.registrar_tentativa_falha()
            current_app.logger.warning(
                f"Falha de senha para '{usuario.username}' "
                f"(tentativa {usuario.tentativas_login})."
            )
            flash(MSG_CREDENCIAL_INVALIDA, "danger")
            return render_template("auth/login.html", form=form)

        # Login bem-sucedido. "Manter conectado" só é honrado se habilitado em
        # config (desabilitado por padrão para estações compartilhadas — S-06/B-01).
        remember = bool(form.lembrar.data) and current_app.config.get(
            "LOGIN_REMEMBER_HABILITADO", False
        )
        login_user(usuario, remember=remember)
        usuario.registrar_login()

        current_app.logger.info(f"Login: {usuario.username} ({usuario.nome})")

        # Redireciona para troca de senha obrigatória
        if usuario.deve_trocar_senha:
            flash("Por segurança, troque sua senha antes de continuar.", "warning")
            return redirect(url_for("auth.trocar_senha"))

        # Redireciona para a página que o usuário tentou acessar, ou dashboard
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    """Encerra a sessão do usuário."""
    current_app.logger.info(f"Logout: {current_user.username}")
    logout_user()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/trocar-senha", methods=["GET", "POST"])
@login_required
def trocar_senha():
    """Troca de senha — obrigatória no primeiro acesso."""
    form = TrocarSenhaForm()

    if form.validate_on_submit():
        if not current_user.verificar_senha(form.senha_atual.data):
            flash("Senha atual incorreta.", "danger")
            return render_template("auth/trocar_senha.html", form=form)

        if form.senha_atual.data == form.nova_senha.data:
            flash("A nova senha não pode ser igual à senha atual.", "warning")
            return render_template("auth/trocar_senha.html", form=form)

        # Reforço server-side da política, incluindo o username do usuário logado
        # (o validador do form não tem acesso ao username no fluxo autenticado).
        erros_politica = validar_senha(
            form.nova_senha.data, username=current_user.username
        )
        if erros_politica:
            flash(erros_politica[0], "danger")
            return render_template("auth/trocar_senha.html", form=form)

        current_user.senha = form.nova_senha.data
        current_user.deve_trocar_senha = False
        db.session.commit()

        flash("Senha alterada com sucesso!", "success")
        current_app.logger.info(f"Senha alterada: {current_user.username}")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/trocar_senha.html", form=form)
