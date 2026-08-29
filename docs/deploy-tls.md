# Deploy TLS/HTTPS — SGHSC

> Referência da Story **S-03 — Ativar HTTPS/HSTS em produção**.
> Objetivo: todo o tráfego de produção por HTTPS (TLS 1.2+), com redirect 80→443
> e HSTS ativo, sem quebrar o desenvolvimento local (que permanece em HTTP).

---

## Como funciona

O container `nginx` seleciona o bloco de servidor conforme a variável **`NGINX_ENV`**:

| `NGINX_ENV`   | Comportamento                                                        |
|---------------|----------------------------------------------------------------------|
| `development` | HTTP puro na porta 80. **Sem HSTS**. (padrão)                        |
| `production`  | Porta 80 → **301** para 443. HTTPS com **TLS 1.2/1.3** e **HSTS**.  |

A seleção é feita pelo `nginx/docker-entrypoint.sh`, que grava o snippet ativo em
`/etc/nginx/active/active.conf` e valida com `nginx -t` antes de subir.

Arquivos relevantes:

```
nginx/
├── nginx.conf                          # bloco http + include do snippet ativo
├── docker-entrypoint.sh                # seleciona dev/prod por NGINX_ENV
├── conf.d/
│   ├── server-dev.conf                 # HTTP 80, sem HSTS
│   └── server-prod.conf.template       # 80→443 + 443 TLS + HSTS (envsubst)
├── certs/                              # certificados TLS de produção (não commitar)
└── certbot/                            # webroot ACME (Let's Encrypt)
```

---

## Desenvolvimento local (HTTP)

Nada a fazer. Com `NGINX_ENV` ausente ou `development`, o nginx serve em
`http://localhost` (porta 80) sem HSTS. O `docker-compose.yml` já usa esse padrão:

```yaml
environment:
  NGINX_ENV: ${NGINX_ENV:-development}
```

---

## Produção (HTTPS)

### 1. Definir variáveis no `.env`

```dotenv
FLASK_ENV=production
NGINX_ENV=production
NGINX_SERVER_NAME=sghsc.santacasapedralva.org.br
```

Com `FLASK_ENV=production`, o Flask aplica `SESSION_COOKIE_SECURE=True`
(`ProductionConfig`) e passa a confiar no cabeçalho `X-Forwarded-Proto=https`
enviado pelo nginx (via `ProxyFix`).

### 2. Fornecer o certificado TLS

Coloque os dois arquivos em `nginx/certs/`:

```
nginx/certs/fullchain.pem   # certificado + cadeia intermediária
nginx/certs/privkey.pem     # chave privada
```

Se estes arquivos estiverem ausentes em produção, o entrypoint aborta com erro
explícito (não sobe o nginx sem TLS).

#### Opção A — Certificado próprio (arquivo)

Se a instituição já possui um certificado (ex.: emitido pela TI do hospital ou
uma AC comercial), basta copiar/renomear para os nomes acima e subir os
containers.

#### Opção B — Let's Encrypt (certbot)

O bloco de produção já libera o desafio ACME em `/.well-known/acme-challenge/`
(servido de `nginx/certbot/`). Emissão inicial (exemplo com container certbot):

```bash
docker run --rm \
  -v "$PWD/nginx/certs:/etc/letsencrypt/live/sghsc" \
  -v "$PWD/nginx/certbot:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d sghsc.santacasapedralva.org.br \
  --email ti@santacasapedralva.org.br --agree-tos --no-eff-email
```

Aponte/renomeie os arquivos gerados (`fullchain.pem`, `privkey.pem`) para
`nginx/certs/`. Para renovação, reexecute o certbot e recarregue o nginx:

```bash
docker compose exec nginx nginx -s reload
```

### 3. Subir

```bash
docker compose up -d --build
docker compose logs nginx    # deve mostrar: "Modo PRODUÇÃO: HTTPS + HSTS"
```

---

## Verificação ponta a ponta

```bash
# 80 redireciona para 443
curl -sI http://SEU_DOMINIO/ | grep -i location      # Location: https://...

# HSTS presente no HTTPS
curl -sI https://SEU_DOMINIO/ | grep -i strict-transport-security

# TLS 1.2+ (handshake ok)
curl -sI --tlsv1.2 https://SEU_DOMINIO/ | head -1
```

Fluxos a validar manualmente sobre HTTPS: **login**, navegação **HTMX** e
**download** de documentos.

---

## Segurança

- Chave privada (`privkey.pem`) e demais `.pem/.key` são ignorados pelo
  `.gitignore` — **nunca** versione certificados.
- HSTS usa `max-age=31536000; includeSubDomains`. Só ative em produção com o
  domínio definitivo; uma vez enviado, o navegador força HTTPS por 1 ano.
- Nota: este TLS de transporte é independente do certificado **ICP-Brasil**
  usado para assinatura de documentos.
