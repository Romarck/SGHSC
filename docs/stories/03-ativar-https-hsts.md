# Story S-03 — Ativar HTTPS/HSTS em produção

**Épico:** Base e Segurança (NFR-02 / NFR-03)
**Prioridade:** P0 — **bloqueia produção** (veto @si)
**Status:** Concluído
**Origem:** @si A-01 / A-03 (Alto) · @architect S3

---

## Contexto
O bloco HTTPS do `nginx/nginx.conf` está **comentado** e `SESSION_COOKIE_SECURE` só é `True`
em produção. Sem TLS, sessão e dados de saúde trafegam em claro na rede hospitalar
(interceptação, roubo de sessão). Dado sensível de saúde exige criptografia em trânsito (LGPD).

## Descrição
Como **operador do hospital**, quero que todo o tráfego seja por HTTPS, para proteger
credenciais e dados de pacientes em trânsito.

## Critérios de Aceite
- [x] Nginx serve HTTPS (443) com certificado TLS; TLS 1.2+. *(server-prod: `listen 443 ssl`, `ssl_protocols TLSv1.2 TLSv1.3`)*
- [x] Porta 80 **redireciona** para 443 em produção. *(`return 301 https://$host$request_uri`, com exceção do desafio ACME)*
- [x] Cabeçalho **HSTS** ativo (`Strict-Transport-Security`) em produção. *(`max-age=31536000; includeSubDomains`)*
- [x] `SESSION_COOKIE_SECURE=True` efetivo em produção (já em `ProductionConfig`). *(+ `ProxyFix` para honrar `X-Forwarded-Proto`)*
- [x] Documentado como fornecer o certificado TLS (arquivo ou Let's Encrypt) sem quebrar o dev local. *(`docs/deploy-tls.md`)*

## Tarefas
1. [x] Bloco de servidor 443 ativo (`nginx/conf.d/server-prod.conf.template`), certs via volume `nginx/certs`.
2. [x] Redirect 80→443 condicionado a produção (via `NGINX_ENV` no `docker-entrypoint.sh`).
3. [x] Cabeçalhos de segurança no bloco ativo (HSTS + `X-Content-Type-Options`/`X-Frame-Options`/`Referrer-Policy`).
4. [x] `docker-compose.yml` e `docs/deploy-tls.md` atualizados para o provisionamento do certificado TLS.
5. [x] Configuração validada em runtime pelo @qadv: redirect 301, HSTS presente nas respostas (proxied e estática), TLS 1.3 negociado, proxy p/ app OK, ACME sem redirect; dev sem HSTS. Ver seção **QA — @qadv** abaixo.

## Implementação (resumo @dev)
- `nginx/nginx.conf`: bloco `http` + `include /etc/nginx/active/active.conf`.
- `nginx/conf.d/server-dev.conf`: HTTP 80, **sem HSTS** (dev local intacto).
- `nginx/conf.d/server-prod.conf.template`: 80→443 + 443 TLS 1.2/1.3 + HSTS + headers de segurança + webroot ACME.
- `nginx/docker-entrypoint.sh`: seleciona dev/prod por `NGINX_ENV`, renderiza via `envsubst`, exige certs em prod, roda `nginx -t`.
- `docker-compose.yml`: monta `conf.d`, entrypoint, `certs`, `certbot`; injeta `NGINX_ENV`/`NGINX_SERVER_NAME`.
- `backend/app/__init__.py`: `ProxyFix` (somente produção) para o Flask confiar em `X-Forwarded-Proto=https`.
- `.env.example`: `NGINX_ENV`/`NGINX_SERVER_NAME` + notas de TLS. `.gitignore`: exclui `nginx/certs/*`.

## Notas
- Manter o dev local em HTTP (porta 80) sem HSTS para não travar o desenvolvimento. *(garantido: `NGINX_ENV=development` é o padrão)*
- Não confundir com o certificado ICP-Brasil (assinatura de documento) — aqui é TLS de transporte.
- Próximo passo: **@qadv `*qa 3`** (validação funcional sobre HTTPS antes de `Concluído`).

---

## QA — @qadv (`*qa 3`)

**Resultado:** ✅ **APROVADO** (após 1 rodada de correção).

### Método
Validação **em runtime** (não só leitura de config): subi o nginx real em modo
`production` com certificado de teste e um upstream `app` stub, numa rede Docker
isolada, e inspecionei as respostas HTTP de verdade.

### Defeito encontrado (rejeição inicial → devolvido ao @dev)
- **HSTS ausente nas respostas** apesar de estar no config. Causa: em nginx,
  `add_header` **não é herdado** por um `location` que define os próprios
  `add_header`. Como todos os locations do server de produção adicionavam
  `Cache-Control`, os cabeçalhos de segurança do nível do server (incl. HSTS)
  eram descartados. A verificação original do @dev só fez `grep` no arquivo de
  config e nunca checou o header numa resposta real — por isso passou batido.
- **Correção (@dev):** extraído `nginx/conf.d/security-headers.conf` e incluído
  **dentro de cada `location`** do template de produção.

### Evidências (pós-correção)
| Critério | Verificação | Resultado |
|----------|-------------|-----------|
| HTTPS 443 + TLS 1.2+ | handshake curl | `TLSv1.3` (aceita 1.2/1.3) ✅ |
| 80 → 443 | `curl -I http://…` | `301` + `Location: https://…` ✅ |
| HSTS em produção | header na resposta proxied (HTMX) | `max-age=31536000; includeSubDomains` ✅ |
| HSTS em `/static/` | header na resposta estática | presente ✅ |
| Security headers S-09 | resposta HTTPS | `nosniff` / `SAMEORIGIN` / `Referrer-Policy` ✅ |
| Proxy p/ app sobre HTTPS | body upstream | `UPSTREAM-OK` ✅ |
| ACME sem redirect | `/.well-known/acme-challenge/…` | servido em HTTP (sem 301) ✅ |
| Dev sem HSTS | `server-dev.conf` | `nginx -t` ok, 0 ocorrências de HSTS ✅ |

Harness de QA (containers/rede/cert de teste) removido ao final.

### Observações (não bloqueantes)
- `SESSION_COOKIE_SECURE=True` e `ProxyFix` dependem de `FLASK_ENV=production` —
  validado no escopo da S-04.
- Os testes de fluxo funcional (login/HTMX/download) foram exercidos contra um
  upstream stub; recomenda-se um smoke test contra a app real no ambiente de
  produção com o certificado definitivo antes do go-live.
