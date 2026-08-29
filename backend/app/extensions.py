"""
extensions.py — Instâncias das extensões Flask.

Todas as extensões são criadas aqui sem app binding (padrão Application Factory).
O binding com o app ocorre em app/__init__.py via extension.init_app(app).
"""

from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# ORM — banco de dados relacional
db = SQLAlchemy()

# Migrações de schema
migrate = Migrate()

# Autenticação de sessão
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"

# Hash de senhas
bcrypt = Bcrypt()

# Proteção CSRF global
csrf = CSRFProtect()

# Rate limiting (S-09). Sem limites default globais — aplicados por rota via
# decorator @limiter.limit. Chaveado por IP (get_remote_address respeita o
# ProxyFix em produção). Storage configurável por RATELIMIT_STORAGE_URI
# (memória por padrão; use Redis em produção multi-worker).
limiter = Limiter(key_func=get_remote_address)
