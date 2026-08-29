"""
wsgi.py — Ponto de entrada WSGI para produção (Gunicorn).
"""

import os

from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run()
