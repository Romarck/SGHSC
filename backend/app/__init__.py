"""
app/__init__.py — Application Factory do SGHSC.

Sistema de Gestão Hospitalar para Santas Casas
Santa Casa de Misericórdia de Pedralva - MG
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask

from .config import config
from .extensions import bcrypt, csrf, db, limiter, login_manager, migrate


def create_app(config_name: str = None) -> Flask:
    """
    Cria e configura a instância da aplicação Flask.

    Args:
        config_name: 'development', 'testing' ou 'production'.
                     Usa FLASK_ENV do ambiente se não informado.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, template_folder="templates", static_folder="static")

    # --- Configuração ---
    app.config.from_object(config[config_name])

    # Reresolve segredos a partir do ambiente. As classes de Config congelam os
    # valores no momento do import; se o módulo foi importado antes das variáveis
    # existirem, app.config carregaria o fallback default. Reler aqui garante que
    # o valor EFETIVO usado pela app é o do ambiente atual.
    if os.environ.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

    # --- Validação de configuração em produção (falha rápido) ---
    # Recusa-se a subir sem os segredos obrigatórios ou com SECRET_KEY default.
    if config_name == "production":
        from .config import ProductionConfig
        ProductionConfig.validate(app.config)

    # --- Proxy reverso (TLS terminado no nginx) ---
    # Em produção o nginx encaminha X-Forwarded-Proto=https. Sem ProxyFix o
    # Flask enxergaria o esquema http (Gunicorn interno) e geraria URLs/redirects
    # http:// mesmo sob HTTPS. Confia em 1 proxy à frente (nginx).
    if config_name == "production":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1
        )

    # --- Extensões ---
    _init_extensions(app)

    # --- Blueprints ---
    _register_blueprints(app)

    # --- Handlers de erro ---
    _register_error_handlers(app)

    # --- Hooks de requisição (ex.: troca de senha obrigatória) ---
    _register_before_requests(app)

    # --- Logging ---
    _configure_logging(app)

    # --- Context processors (variáveis globais nos templates) ---
    _register_context_processors(app)

    # --- Comandos CLI ---
    _register_cli(app)

    app.logger.info(
        f"SGHSC iniciado — ambiente: {config_name} | "
        f"Instituição: {app.config.get('INSTITUICAO_NOME')}"
    )

    return app


def _init_extensions(app: Flask) -> None:
    """Inicializa todas as extensões com o app."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Registra user_loader do Flask-Login
    from .models.usuario import Usuario

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(Usuario, int(user_id))

    # Cria pastas necessárias em runtime
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)
    os.makedirs(app.config.get("CERT_STORAGE_PATH", "certs"), exist_ok=True)
    os.makedirs("logs", exist_ok=True)


def _register_blueprints(app: Flask) -> None:
    """Registra todos os blueprints da aplicação."""

    # Autenticação
    from .routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Painel principal
    from .routes.main import bp as main_bp
    app.register_blueprint(main_bp, url_prefix="/")

    # --- Fase 2: Porta de entrada ---
    from .routes.pacientes import bp as pacientes_bp
    app.register_blueprint(pacientes_bp, url_prefix="/pacientes")

    from .routes.emergencia import bp as emergencia_bp
    app.register_blueprint(emergencia_bp, url_prefix="/emergencia")

    from .routes.ambulatorio import bp as ambulatorio_bp
    app.register_blueprint(ambulatorio_bp, url_prefix="/ambulatorio")

    # --- Fase 3: Internação ---
    from .routes.internacao import bp as internacao_bp
    app.register_blueprint(internacao_bp, url_prefix="/internacao")

    # --- Fase 4: Apoio Clínico ---
    from .routes.certificado import bp as certificado_bp
    app.register_blueprint(certificado_bp, url_prefix="/certificado")

    from .routes.exames import bp as exames_bp
    app.register_blueprint(exames_bp, url_prefix="/exames")

    from .routes.farmacia import bp as farmacia_bp
    app.register_blueprint(farmacia_bp, url_prefix="/farmacia")

    from .routes.nutricao import bp as nutricao_bp
    app.register_blueprint(nutricao_bp, url_prefix="/nutricao")

    from .routes.ccih import bp as ccih_bp
    app.register_blueprint(ccih_bp, url_prefix="/ccih")

    from .routes.cirurgias import bp as cirurgias_bp
    app.register_blueprint(cirurgias_bp, url_prefix="/cirurgias")

    from .routes.maternidade import bp as maternidade_bp
    app.register_blueprint(maternidade_bp, url_prefix="/maternidade")

    # --- Fase 5: Administrativo ---
    from .routes.estoque import bp as estoque_bp
    app.register_blueprint(estoque_bp, url_prefix="/estoque")

    from .routes.compras import bp as compras_bp
    app.register_blueprint(compras_bp, url_prefix="/compras")

    from .routes.financeiro import bp as financeiro_bp
    app.register_blueprint(financeiro_bp, url_prefix="/financeiro")

    from .routes.faturamento import bp as faturamento_bp
    app.register_blueprint(faturamento_bp, url_prefix="/faturamento")

    from .routes.convenios import bp as convenios_bp
    app.register_blueprint(convenios_bp, url_prefix="/convenios")

    from .routes.patrimonio import bp as patrimonio_bp
    app.register_blueprint(patrimonio_bp, url_prefix="/patrimonio")

    from .routes.rh import bp as rh_bp
    app.register_blueprint(rh_bp, url_prefix="/rh")

    from .routes.manutencao import bp as manutencao_bp
    app.register_blueprint(manutencao_bp, url_prefix="/manutencao")

    # --- Fase 6: Gestão e Compliance ---
    from .routes.relatorios import bp as relatorios_bp
    app.register_blueprint(relatorios_bp, url_prefix="/relatorios")

    from .routes.auditoria import bp as auditoria_bp
    app.register_blueprint(auditoria_bp, url_prefix="/auditoria")

    from .routes.residuos import bp as residuos_bp
    app.register_blueprint(residuos_bp, url_prefix="/residuos")

    from .routes.rnds import bp as rnds_bp
    app.register_blueprint(rnds_bp, url_prefix="/rnds")


def _register_error_handlers(app: Flask) -> None:
    """Registra handlers para erros HTTP."""
    from flask import render_template

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html", error=e), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html", error=e), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html", error=e), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html", error=e), 500


def _register_before_requests(app: Flask) -> None:
    """Hooks executados antes de cada requisição."""
    from flask import redirect, request, url_for
    from flask_login import current_user

    # Endpoints acessíveis mesmo com troca de senha pendente (evita loop de redirect).
    _isentos_troca_senha = {"auth.trocar_senha", "auth.logout", "static"}

    @app.before_request
    def _forcar_troca_de_senha():
        """
        Enquanto `deve_trocar_senha=True`, redireciona o usuário autenticado para a
        troca de senha — inclusive se a flag foi ligada durante uma sessão ativa
        (não apenas no login). Story S-06.
        """
        if not current_user.is_authenticated:
            return None
        if not getattr(current_user, "deve_trocar_senha", False):
            return None
        if request.endpoint in _isentos_troca_senha:
            return None
        # Não interfere em chamadas a arquivos estáticos/rota de troca/logout.
        return redirect(url_for("auth.trocar_senha"))


def _configure_logging(app: Flask) -> None:
    """Configura logging para arquivo rotativo + console."""
    if app.testing:
        return

    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)
    log_file = app.config.get("LOG_FILE", "logs/sghsc.log")

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    # Handler de arquivo (rotativo — máx 10MB, 5 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=10_485_760, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Handler de console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)


def _register_cli(app: Flask) -> None:
    """Comandos CLI utilitários."""

    @app.cli.command("seed-permissoes")
    def seed_permissoes_cmd():
        """Cria/atualiza as permissões RBAC e as associa aos perfis (idempotente)."""
        from .security.permissoes import seed_permissoes

        resumo = seed_permissoes()
        print(
            f"Permissões: {resumo['permissoes_totais']} no catálogo "
            f"({resumo['permissoes_criadas']} novas); "
            f"{resumo['perfis_atualizados']} perfis atualizados."
        )

    @app.cli.command("purgar-auditoria")
    def purgar_auditoria_cmd():
        """Remove logs de auditoria de acesso vencidos (política de retenção — S-07)."""
        from .services.auditoria_service import purgar_logs_vencidos

        dias = app.config.get("AUDITORIA_RETENCAO_DIAS")
        removidos = purgar_logs_vencidos(dias)
        print(f"Auditoria: {removidos} registro(s) além de {dias} dias removido(s).")


def _register_context_processors(app: Flask) -> None:
    """Injeta variáveis globais disponíveis em todos os templates Jinja2."""
    from flask_login import current_user

    @app.context_processor
    def inject_globals():
        # Helper de permissão para os templates (ex.: mostrar cards do dashboard
        # só para quem pode acessar). Reusa a MESMA regra do RBAC das rotas
        # (Administrador vê tudo; demais dependem de tem_permissao) — mantém a UI
        # coerente com o backend (S-01), sem prometer acesso que resultaria em 403.
        from .utils.authz import _usuario_autorizado

        def pode_acessar(codigo: str) -> bool:
            if not getattr(current_user, "is_authenticated", False):
                return False
            return _usuario_autorizado(current_user, codigo)

        return {
            "instituicao_nome": app.config.get("INSTITUICAO_NOME"),
            "instituicao_cnes": app.config.get("INSTITUICAO_CNES"),
            "current_user": current_user,
            "pode_acessar": pode_acessar,
        }
