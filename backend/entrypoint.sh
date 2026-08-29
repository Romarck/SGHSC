#!/bin/bash
# entrypoint.sh — Script de inicialização do container SGHSC

set -e  # Aborta em caso de erro

echo "========================================="
echo " SGHSC — Sistema de Gestão Hospitalar"
echo " Santa Casa de Misericórdia de Pedralva"
echo "========================================="

# Aguarda banco de dados ficar disponível
echo "[1/4] Aguardando banco de dados..."
until python -c "
import psycopg2, os, sys
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('Banco de dados pronto.')
except Exception as e:
    print(f'Aguardando: {e}')
    sys.exit(1)
"; do
    sleep 2
done

# Aplica migrações de banco de dados (S-10)
# PRODUÇÃO: apenas APLICA migrações já revisadas/commitadas (flask db upgrade).
#   Nunca gera migração automática no boot — evita alteração de schema não
#   intencional em ambiente com dados reais.
# DEV/TEST: mantém a conveniência de autogerar + aplicar.
echo "[2/4] Aplicando migrações..."

if [ "$FLASK_ENV" = "production" ]; then
    echo "  → Produção: aplicando migrações revisadas (flask db upgrade)."
    echo "  → RECOMENDADO: faça backup do banco ANTES do deploy (ver README)."
    if ! flask db upgrade; then
        echo "  ✗ ERRO: 'flask db upgrade' falhou. Abortando o boot para NÃO subir" >&2
        echo "    a aplicação com schema inconsistente. Verifique as migrações e" >&2
        echo "    restaure o backup se necessário." >&2
        exit 1
    fi
    echo "  → Migrações aplicadas com sucesso."
else
    echo "  → Desenvolvimento: autogerando (se houver mudança) e aplicando."
    if [ ! -f "migrations/env.py" ]; then
        echo "  → Inicializando pasta de migrações pela primeira vez..."
        flask db init
    fi
    flask db migrate -m "auto" 2>/dev/null || true
    if ! flask db upgrade; then
        echo "  ✗ ERRO: 'flask db upgrade' falhou. Abortando o boot." >&2
        exit 1
    fi
fi

# Cria usuário administrador padrão se não existir
echo "[3/4] Verificando dados iniciais..."
python - <<'PYTHON'
from app import create_app
from app.extensions import db
from app.models.usuario import Usuario, Perfil, TipoPerfil, StatusUsuario

app = create_app()

with app.app_context():
    # Cria perfil de administrador se não existir
    perfil_admin = Perfil.query.filter_by(tipo=TipoPerfil.ADMINISTRADOR).first()
    if not perfil_admin:
        perfil_admin = Perfil(
            nome="Administrador",
            tipo=TipoPerfil.ADMINISTRADOR,
            descricao="Acesso total ao sistema"
        )
        db.session.add(perfil_admin)
        db.session.flush()
        print("  → Perfil 'Administrador' criado.")

    # Cria usuário admin padrão se não existir
    admin = Usuario.query.filter_by(username="admin").first()
    if not admin:
        admin = Usuario(
            nome="Administrador do Sistema",
            email="admin@sghsc.local",
            username="admin",
            perfil=perfil_admin,
            deve_trocar_senha=True,
            status=StatusUsuario.ATIVO
        )
        admin.senha = "Admin@123"  # Será trocada no primeiro acesso
        db.session.add(admin)
        db.session.commit()
        print("  → Usuário 'admin' criado (senha temporária: Admin@123).")
        print("  → ATENÇÃO: Troque a senha no primeiro acesso!")
    else:
        print("  → Usuário 'admin' já existe.")

    # Seed idempotente das permissões RBAC (Story S-01)
    from app.security.permissoes import seed_permissoes
    resumo = seed_permissoes()
    print(
        f"  → Permissões RBAC: {resumo['permissoes_totais']} no catálogo "
        f"({resumo['permissoes_criadas']} novas), "
        f"{resumo['perfis_atualizados']} perfis atualizados."
    )
PYTHON

# Inicia a aplicação
echo "[4/4] Iniciando aplicação..."

if [ "$FLASK_ENV" = "production" ]; then
    echo "  → Modo: PRODUÇÃO (Gunicorn)"
    exec gunicorn \
        --bind 0.0.0.0:5000 \
        --workers 2 \
        --threads 2 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        "wsgi:app"
else
    echo "  → Modo: DESENVOLVIMENTO (Flask dev server)"
    exec flask run --host=0.0.0.0 --port=5000 --debug
fi
