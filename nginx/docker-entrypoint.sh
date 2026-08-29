#!/bin/sh
# ============================================================================
# Entrypoint do Nginx — SGHSC
# Seleciona o bloco de servidor ativo conforme NGINX_ENV:
#   - development (padrão) -> HTTP puro na porta 80, SEM HSTS
#   - production           -> 80 redireciona p/ 443 (HTTPS) + HSTS
# O resultado é gravado em /etc/nginx/conf.d/active.conf, incluído pelo
# nginx.conf principal.
# ============================================================================
set -eu

NGINX_ENV="${NGINX_ENV:-development}"
NGINX_SERVER_NAME="${NGINX_SERVER_NAME:-_}"
ACTIVE="/etc/nginx/active/active.conf"

# Diretório gravável para o snippet ativo (conf.d é montado somente-leitura)
mkdir -p /etc/nginx/active

if [ "$NGINX_ENV" = "production" ]; then
    echo "[nginx-entrypoint] Modo PRODUÇÃO: HTTPS + HSTS (server_name=${NGINX_SERVER_NAME})"

    if [ ! -f /etc/nginx/certs/fullchain.pem ] || [ ! -f /etc/nginx/certs/privkey.pem ]; then
        echo "[nginx-entrypoint] ERRO: certificado TLS ausente." >&2
        echo "  Esperado: /etc/nginx/certs/fullchain.pem e /etc/nginx/certs/privkey.pem" >&2
        echo "  Monte os certificados via volume (ver docs/deploy-tls.md)." >&2
        exit 1
    fi

    # Substitui apenas ${NGINX_SERVER_NAME}, preservando as variáveis do nginx ($host, etc.)
    export NGINX_SERVER_NAME
    envsubst '${NGINX_SERVER_NAME}' \
        < /etc/nginx/conf.d/server-prod.conf.template \
        > "$ACTIVE"
else
    echo "[nginx-entrypoint] Modo DESENVOLVIMENTO: HTTP na porta 80 (sem HSTS)"
    cp /etc/nginx/conf.d/server-dev.conf "$ACTIVE"
fi

# Valida a configuração antes de subir
nginx -t

exec nginx -g 'daemon off;'
