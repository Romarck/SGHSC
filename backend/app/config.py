import os
from datetime import timedelta


class Config:
    """Configuração base — compartilhada por todos os ambientes."""

    # Segurança
    SECRET_KEY = os.environ.get("SECRET_KEY") or "troque-antes-de-produção"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hora

    # Banco de dados
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "postgresql://sghsc_user:sghsc_pass@localhost:5432/sghsc"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # turno hospitalar
    SESSION_COOKIE_SECURE = False   # True em produção (HTTPS)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # "Manter conectado" (remember me). Em estações compartilhadas do hospital,
    # um cookie persistente é risco (S-06 / B-01). Desabilitado por padrão —
    # a sessão dura o turno (PERMANENT_SESSION_LIFETIME) e cai ao fechar o browser.
    LOGIN_REMEMBER_HABILITADO = False
    # Se um dia for habilitado, limita a duração do cookie persistente.
    REMEMBER_COOKIE_DURATION = timedelta(hours=8)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = False  # True em produção (ver ProductionConfig)

    # Upload de arquivos
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "p12", "pfx"}

    # Certificado digital (ICP-Brasil)
    CERT_STORAGE_PATH = os.environ.get("CERT_STORAGE_PATH") or \
        os.path.join(os.path.dirname(__file__), "certs")
    CERT_TIMESTAMP_URL = os.environ.get("CERT_TIMESTAMP_URL") or \
        "http://timestamp.safeweb.org.br"  # AC do Governo Brasileiro

    # Informações da instituição
    INSTITUICAO_NOME = os.environ.get("INSTITUICAO_NOME") or \
        "Santa Casa de Misericórdia de Pedralva"
    INSTITUICAO_CNES = os.environ.get("INSTITUICAO_CNES") or ""
    INSTITUICAO_CNPJ = os.environ.get("INSTITUICAO_CNPJ") or ""
    INSTITUICAO_CIDADE = os.environ.get("INSTITUICAO_CIDADE") or "Pedralva"
    INSTITUICAO_UF = os.environ.get("INSTITUICAO_UF") or "MG"

    # Paginação padrão
    ITEMS_PER_PAGE = 20

    # Auditoria LGPD — retenção da trilha de acesso (S-07).
    # 5 anos (1825 dias) como padrão conservador para dado de saúde; ajuste
    # conforme a política de retenção definida pelo DPO/jurídico.
    AUDITORIA_RETENCAO_DIAS = 1825

    # Rate limiting (S-09). Storage em memória por padrão (dev/single-worker);
    # em produção multi-worker use Redis via RATELIMIT_STORAGE_URI.
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI") or "memory://"
    RATELIMIT_HEADERS_ENABLED = True
    # Limites por rota (usados nos decorators via config).
    RATELIMIT_LOGIN = "10 per minute"
    RATELIMIT_VALIDACAO_PUBLICA = "30 per minute"

    # Logs
    LOG_LEVEL = "INFO"
    LOG_FILE = os.environ.get("LOG_FILE") or "logs/sghsc.log"


class DevelopmentConfig(Config):
    """Ambiente de desenvolvimento local."""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = "DEBUG"
    FLASK_DEBUG_TOOLBAR = True
    SQLALCHEMY_ECHO = False  # True para ver SQL gerado


class TestingConfig(Config):
    """Ambiente de testes automatizados."""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False  # Desabilita CSRF nos testes
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    BCRYPT_LOG_ROUNDS = 4  # Mais rápido nos testes
    # Rate limiting desligado por padrão nos testes (evita flakiness); o teste
    # específico de rate limit reativa via app.config em runtime.
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Ambiente de produção (Cloud)."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"
    REMEMBER_COOKIE_SECURE = True
    LOG_LEVEL = "WARNING"

    # Valores de SECRET_KEY previsíveis que NUNCA podem ser usados em produção
    # (fallback hardcoded da Config base + placeholders do .env.example).
    FORBIDDEN_SECRET_KEYS = frozenset({
        "troque-antes-de-produção",
        "TROQUE_PARA_UM_VALOR_SECRETO_FORTE",
    })

    # Variáveis de ambiente obrigatórias em produção
    REQUIRED_ENV = ("SECRET_KEY", "DATABASE_URL", "POSTGRES_PASSWORD")

    @classmethod
    def validate(cls, app_config=None):
        """Falha rápido no boot se a configuração de produção for insegura.

        Rejeita variáveis obrigatórias ausentes e valores de SECRET_KEY
        previsíveis (fallback hardcoded / placeholders do .env.example).

        Args:
            app_config: mapping de configuração já resolvida (ex.: app.config).
                Quando fornecido, valida o SECRET_KEY EFETIVO que a aplicação
                usará — não apenas a variável de ambiente crua. Isso captura o
                caso em que o módulo foi importado antes de SECRET_KEY existir e
                a Config base congelou o fallback default.
        """
        missing = [v for v in cls.REQUIRED_ENV if not os.environ.get(v)]

        # SECRET_KEY efetivo: preferimos o valor já resolvido na app_config;
        # caso contrário, cai para a variável de ambiente.
        if app_config is not None:
            secret_key = app_config.get("SECRET_KEY")
        else:
            secret_key = os.environ.get("SECRET_KEY")

        problems = []
        if missing:
            problems.append(
                f"variáveis de ambiente obrigatórias ausentes: {missing}"
            )
        if secret_key and secret_key in cls.FORBIDDEN_SECRET_KEYS:
            problems.append(
                "SECRET_KEY está usando um valor default/previsível — "
                "gere um valor forte com: "
                'python -c "import secrets; print(secrets.token_hex(32))"'
            )

        if problems:
            raise RuntimeError(
                "Configuração de produção insegura — a aplicação não vai subir. "
                + "; ".join(problems)
            )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
