# Checklist de Deploy — SGHSC (@qadv)

Sistema de saúde com dado sensível (LGPD). O veto de pré-produção do `@si` foi
**levantado condicionalmente** (ver `docs/security/audit-report-reauditoria.md`).
Este checklist consolida o que precisa estar pronto **antes do go-live com dados reais**.

---

## 1. Pré-requisitos de segurança (condições do @si — obrigatórias)

- [ ] **TLS real**: certificado do domínio em `nginx/certs/` (`fullchain.pem` + `privkey.pem`);
  `NGINX_ENV=production`, `NGINX_SERVER_NAME=<domínio>`. Ver `docs/deploy-tls.md`.
- [ ] **SECRET_KEY forte** via env (`python -c "import secrets; print(secrets.token_hex(32))"`).
  A app aborta o boot em produção sem segredos fortes (S-04).
- [ ] **Criptografia em repouso (A-04)**: volume do PostgreSQL e storage de PDFs cifrados
  (LUKS/volume do provedor) + **backup cifrado**. (Infraestrutura — sem mudança de código.)
- [ ] **Trocar a senha do admin** (`admin`/`Admin@123`) no primeiro acesso (forçado por S-06).

## 2. Configuração de produção

- [ ] `.env` de produção preenchido (NUNCA commitado) a partir de `.env.example`.
- [ ] `FLASK_ENV=production`, `NGINX_ENV=production`.
- [ ] Rate limiting com storage compartilhado se multi-worker: `RATELIMIT_STORAGE_URI=redis://...`.
- [ ] Retenção de auditoria conforme DPO: `AUDITORIA_RETENCAO_DIAS`.

## 3. Build e banco

- [ ] **Rebuildar a imagem** sempre que `requirements.txt` mudar:
  `docker compose build` (o volume `./backend:/app` mascara o código, não as libs).
- [ ] **Backup do banco ANTES** de qualquer `flask db upgrade` (`pg_dump`).
- [ ] Em produção o boot roda **apenas `flask db upgrade`** (S-10); falha aborta o boot.
- [ ] Migração que torna coluna NOT NULL exige **backfill** antes (ex.: `pacientes.criado_por_id`
  na S-07 — em base já povoada, preencher os NULLs antes de aplicar). Ver `docs/migracao-producao.md`.

## 4. Qualidade (quality gate — CI)

- [ ] CI verde: `ruff`, `pytest` (52+), `flask db upgrade` efêmero, `pip-audit` (S-08).
- [ ] `pip-audit` sem vulnerabilidades conhecidas.

## 5. Pós-deploy (smoke test)

- [ ] Login sobre HTTPS; redirect 80→443; HSTS presente.
- [ ] Fluxo clínico: admissão → prescrição → prontuário → alta + laudo PDF.
- [ ] Download de documento respeita RBAC/IDOR (403 para não autorizado).
- [ ] Trilha de auditoria registrando acessos (`/auditoria/`).
- [ ] Validação pública de documento (QR) responde e é limitada (rate limit).

## 6. Rollback

- [ ] Plano de rollback: restaurar imagem anterior + `pg_restore` do backup pré-upgrade.
- [ ] `flask db downgrade` só se a migração tiver `downgrade()` seguro e testado.

---

## Itens de acompanhamento (não bloqueiam o deploy, mas rastrear)

- **A-04** criptografia em repouso — abrir story se exigir cifra de coluna além da de volume.
- **M-06** segredo inicial do admin — gerar aleatório/por env em vez de fixo.
- **CSP** endurecer (remover `'unsafe-inline'` via nonces).
- Ampliar trilha de auditoria (S-07) para exames/maternidade, se o DPO exigir.
