# ▶️ RETOMAR AQUI — Deploy VPS de Homologação (SGHSC)

> Documento de retomada. Paramos no meio do deploy de homologação. Este arquivo diz
> **onde paramos** e **o que executar a seguir**, na ordem. O guia técnico detalhado
> está em `docs/deploy-vps-homolog.md`; o checklist de go-live em `docs/deploy-checklist.md`.

**Última atualização:** 2026-08-29

---

## Dados do ambiente (homologação)

| Item | Valor |
|------|-------|
| Domínio | `https://sghsc.romarck.com` |
| IP da VPS | `129.121.51.114` |
| Porta SSH | `22022` |
| Usuário | `root` |
| Repositório | `Romarck/SGHSC` (privado) — branch `main` |
| Diretório na VPS | `/opt/sghsc` (sugerido) |

> ⚠️ **Escopo:** ambiente de **teste/validação** com o time da Santa Casa.
> **NÃO usar dados reais de pacientes** até a VPS de produção (falta cifra em repouso — A-04).
> Nunca colar senha/chave privada no chat.

---

## ✅ O que já está pronto (feito nesta sessão)

- 10 stories de segurança/qualidade concluídas e aprovadas (S-01..S-10).
- Reauditoria do `@si`: veto de pré-produção **levantado condicionalmente**
  (`docs/security/audit-report-reauditoria.md`).
- Código publicado no GitHub privado `Romarck/SGHSC`; **CI verde** (ruff, migração,
  pytest, pip-audit).
- Arquivos de deploy commitados e no repo:
  - `docker-compose.prod.yml` — fecha portas 5444/5050, expõe só nginx 80/443, força produção.
  - `docs/deploy-vps-homolog.md` — guia técnico completo.
  - `docs/deploy-checklist.md` — checklist de go-live.

**Decisões já tomadas com o Romarck:** Docker já instalado na VPS · acesso por chave SSH ·
fechar 5444/5050 e expor só 80/443 · usar deploy key para clonar o repo privado.

---

## 📍 ONDE PARAMOS

Estávamos prestes a executar a **ETAPA 1** na VPS (firewall + confirmar Docker).
Nada foi executado no servidor ainda. **Retome pela Etapa 1 abaixo.**

---

## 🔜 PRÓXIMOS PASSOS (executar na VPS, em ordem)

### ETAPA 1 — Firewall e Docker
```bash
ssh -p 22022 root@129.121.51.114

apt-get update && apt-get install -y ufw
ufw allow 22022/tcp     # SSH custom — ESSENCIAL antes do enable (senão trava o acesso)
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status

docker --version
docker compose version
```
➡️ **Traga a saída** de `ufw status` + versões do Docker para o Kiro validar.

### ETAPA 2 — Deploy key + clone do repo privado
```bash
# Na VPS:
ssh-keygen -t ed25519 -f ~/.ssh/sghsc_deploy -N "" -C "vps-homolog"
cat ~/.ssh/sghsc_deploy.pub      # copie esta linha
```
No navegador: **GitHub → repo SGHSC → Settings → Deploy keys → Add deploy key** →
cole a chave · **NÃO** marcar "Allow write access" · Add.
```bash
# Na VPS:
cat >> ~/.ssh/config <<'EOF'
Host github-sghsc
  HostName github.com
  User git
  IdentityFile ~/.ssh/sghsc_deploy
EOF
git clone github-sghsc:Romarck/SGHSC.git /opt/sghsc
cd /opt/sghsc
```
➡️ Confirmar que o clone funcionou (`ls /opt/sghsc`).

### ETAPA 3 — Configurar `.env`
```bash
cd /opt/sghsc
cp .env.example .env
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"   # gere e copie
nano .env
```
Preencher no `.env` (NUNCA commitar):
```dotenv
FLASK_ENV=production
NGINX_ENV=production
NGINX_SERVER_NAME=sghsc.romarck.com
SECRET_KEY=<valor gerado>
POSTGRES_DB=sghsc
POSTGRES_USER=sghsc_user
POSTGRES_PASSWORD=<senha forte>
INSTITUICAO_CNES=<CNES>
INSTITUICAO_CNPJ=<CNPJ>
```

### ETAPA 4 — Emitir certificado TLS (Let's Encrypt) em 2 etapas
> O nginx de produção aborta sem cert; por isso emitimos primeiro em modo HTTP.
```bash
mkdir -p nginx/certs nginx/certbot

# 4.1 Sobe temporariamente em modo HTTP para responder ao desafio ACME:
NGINX_ENV=development docker compose up -d --build nginx app db
curl -I http://sghsc.romarck.com/     # confirmar DNS + porta 80 (traga a saída)

# 4.2 Emitir o certificado:
docker run --rm \
  -v "$PWD/nginx/certbot:/var/www/certbot" \
  -v "$PWD/letsencrypt:/etc/letsencrypt" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d sghsc.romarck.com \
  --email <seu-email> --agree-tos --no-eff-email

cp letsencrypt/live/sghsc.romarck.com/fullchain.pem nginx/certs/fullchain.pem
cp letsencrypt/live/sghsc.romarck.com/privkey.pem   nginx/certs/privkey.pem
```
➡️ **Ponto de atenção:** antes do 4.2, o `curl -I http://sghsc.romarck.com/` precisa
responder. Se não responder, é DNS ou porta 80 — traga a saída para o Kiro diagnosticar.

### ETAPA 5 — Subir em produção (HTTPS)
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose logs nginx | tail -5     # espera "Modo PRODUÇÃO: HTTPS + HSTS"
docker compose logs app   | tail -15     # migrações + Gunicorn
```

### ETAPA 6 — Smoke test
```bash
curl -sI http://sghsc.romarck.com/ | grep -i location                 # 301 -> https
curl -sI https://sghsc.romarck.com/ | grep -iE "HTTP/|strict-transport-security"
```
No navegador: `https://sghsc.romarck.com` → login `admin` / `Admin@123` → **trocar senha**
(forçado) → validar fluxo clínico com o time.

---

## ⚠️ Armadilhas já mapeadas (não cair de novo)

1. **Rebuild ao mudar dependências:** sempre `docker compose ... up -d --build`. O bug do
   `flask_limiter` faltando veio de subir sem rebuild.
2. **Backfill antes de NOT NULL:** o boot aborta se uma migração tornar coluna NOT NULL com
   dados NULL (aconteceu com `pacientes.criado_por_id`). Em homolog o banco começa vazio, então
   não deve ocorrer; se ocorrer, ver `docs/migracao-producao.md`.
3. **Ordem do firewall:** liberar 22022 **antes** de `ufw enable`.
4. **Certificado ovo-e-galinha:** emitir em modo HTTP (Etapa 4.1) antes de virar produção.

---

## ▶️ Como retomar com o Kiro na próxima sessão

Diga algo como: *"Vamos continuar o deploy da VPS de homologação — estou na Etapa 1"*
e cole a saída dos comandos conforme for executando. O Kiro valida cada etapa antes da próxima.
