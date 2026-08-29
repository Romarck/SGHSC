# Deploy em VPS — Ambiente de Homologação (SGHSC)

> **Escopo:** ambiente de **testes/validação** com o time da Santa Casa, exposto em
> `https://sghsc.romarck.com`. **NÃO usar dados reais de pacientes** ainda — a
> criptografia em repouso (A-04) será tratada na VPS de produção definitiva.
>
> **Servidor:** `129.121.51.114` · SSH porta `22022` · usuário `root`.
>
> Execute os comandos **você mesmo** na VPS. Este guia foi escrito por passos; ao
> final de cada bloco, confira a saída antes de seguir.

---

## 0. Pré-requisitos e segurança de acesso

### 0.1 Acesso por chave SSH (recomendado; evite senha)
Na **sua máquina local** (não na VPS):
```bash
# Se ainda não tem uma chave:
ssh-keygen -t ed25519 -C "sghsc-deploy"
# Copie sua chave pública para a VPS:
ssh-copy-id -p 22022 root@129.121.51.114
# Teste:
ssh -p 22022 root@129.121.51.114 "echo ok"
```

### 0.2 Hardening básico do SSH (na VPS, opcional mas recomendado)
Depois de confirmar o login por chave, desabilite senha:
```bash
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh || systemctl restart sshd
```

### 0.3 Firewall — expor só o necessário
```bash
apt-get update && apt-get install -y ufw
ufw allow 22022/tcp     # SSH (porta custom)
ufw allow 80/tcp        # HTTP (redirect + ACME)
ufw allow 443/tcp       # HTTPS
ufw --force enable
ufw status
```
> Postgres e Flask **não** ficam expostos (o `docker-compose.prod.yml` remove as portas).

---

## 1. Instalar Docker (se ainda não houver)
```bash
docker --version 2>/dev/null || curl -fsSL https://get.docker.com | sh
docker compose version
```

---

## 2. Obter o código (repositório privado)

O repo `Romarck/SGHSC` é **privado**. Use uma **deploy key** (chave SSH só-leitura):
```bash
# Na VPS: gere uma chave de deploy
ssh-keygen -t ed25519 -f ~/.ssh/sghsc_deploy -N "" -C "vps-homolog"
cat ~/.ssh/sghsc_deploy.pub
```
Adicione a chave pública em **GitHub → repo SGHSC → Settings → Deploy keys → Add**
(sem permissão de escrita). Configure o SSH e clone:
```bash
cat >> ~/.ssh/config <<'EOF'
Host github-sghsc
  HostName github.com
  User git
  IdentityFile ~/.ssh/sghsc_deploy
EOF
git clone github-sghsc:Romarck/SGHSC.git /opt/sghsc
cd /opt/sghsc
```

---

## 3. Configurar o ambiente (`.env`)

```bash
cp .env.example .env
# Gere um SECRET_KEY forte:
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
```
Edite o `.env` e preencha (NUNCA commitar):
```dotenv
FLASK_ENV=production
NGINX_ENV=production
NGINX_SERVER_NAME=sghsc.romarck.com

SECRET_KEY=<cole o valor gerado acima>
POSTGRES_DB=sghsc
POSTGRES_USER=sghsc_user
POSTGRES_PASSWORD=<senha forte do banco>

INSTITUICAO_CNES=<CNES da unidade>
INSTITUICAO_CNPJ=<CNPJ>
```

---

## 4. Emitir o certificado TLS (Let's Encrypt) — fluxo em 2 etapas

> **Por quê 2 etapas:** em produção o nginx **aborta** se não achar o certificado,
> mas o desafio ACME precisa do nginx no ar na porta 80. Então subimos primeiro em
> modo HTTP para emitir, depois viramos para HTTPS.

### 4.1 Subir só o nginx em modo HTTP (dev) para responder ao desafio ACME
```bash
mkdir -p nginx/certs nginx/certbot
# Sobe nginx em modo HTTP temporário (sem exigir cert):
NGINX_ENV=development docker compose up -d --build nginx app db
curl -I http://sghsc.romarck.com/    # deve responder (200/302), confirmando DNS+porta 80
```

### 4.2 Emitir o certificado via webroot
```bash
docker run --rm \
  -v "$PWD/nginx/certbot:/var/www/certbot" \
  -v "$PWD/letsencrypt:/etc/letsencrypt" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d sghsc.romarck.com \
  --email <seu-email> --agree-tos --no-eff-email
```
Copie os arquivos emitidos para onde o nginx espera:
```bash
cp letsencrypt/live/sghsc.romarck.com/fullchain.pem nginx/certs/fullchain.pem
cp letsencrypt/live/sghsc.romarck.com/privkey.pem   nginx/certs/privkey.pem
```

---

## 5. Subir em modo produção (HTTPS)
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose logs nginx | tail -5   # deve mostrar "Modo PRODUÇÃO: HTTPS + HSTS"
docker compose logs app   | tail -15  # migrações + Gunicorn
```

---

## 6. Smoke test (validação)
```bash
# 80 redireciona para 443
curl -sI http://sghsc.romarck.com/ | grep -i location
# HTTPS responde + HSTS
curl -sI https://sghsc.romarck.com/ | grep -iE "HTTP/|strict-transport-security"
# Login acessível
curl -sI https://sghsc.romarck.com/auth/login | head -1
```
No navegador: acesse `https://sghsc.romarck.com`, faça login com `admin` /
`Admin@123` e **troque a senha** (forçado no 1º acesso). Valide o fluxo clínico.

---

## 7. Renovação do certificado (Let's Encrypt expira em 90 dias)
```bash
docker run --rm \
  -v "$PWD/nginx/certbot:/var/www/certbot" \
  -v "$PWD/letsencrypt:/etc/letsencrypt" \
  certbot/certbot renew --webroot -w /var/www/certbot
cp letsencrypt/live/sghsc.romarck.com/fullchain.pem nginx/certs/fullchain.pem
cp letsencrypt/live/sghsc.romarck.com/privkey.pem   nginx/certs/privkey.pem
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec nginx nginx -s reload
```
(Automatize via cron mensal quando validar o fluxo.)

---

## 8. Atualizar a aplicação (novo deploy)
```bash
cd /opt/sghsc
git pull
# backup do banco ANTES de migrar (S-10):
docker compose exec -T db pg_dump -U sghsc_user sghsc > backup_$(date +%Y%m%d_%H%M%S).sql
# rebuild (necessário se requirements.txt mudou) + upgrade automático no boot:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## Lembretes de escopo (homologação → produção)

- **Homologação:** dados de teste. Deixe claro ao time que não é para dados reais de
  pacientes ainda.
- **Antes da produção real:** cumprir o `docs/deploy-checklist.md` (cifra em repouso
  A-04, backup cifrado, rate limit com Redis se multi-worker, rotação do segredo do
  admin, etc.).
