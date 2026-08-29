# Story S-09 — Rate limiting, cabeçalhos de segurança e endurecimento de upload

**Épico:** Base e Segurança (NFR-01 / NFR-03)
**Prioridade:** P2
**Status:** Concluído
**Origem:** @si M-03 / M-07 (Médio) · B-02 / B-03 (Baixo)

---

## Contexto
- A rota pública `/certificado/validar/<codigo>` não tem **rate limiting** (M-07) — risco de
  enumeração; deve expor apenas o mínimo necessário (LGPD).
- O bloco Nginx ativo não define **cabeçalhos de segurança** (CSP, `X-Content-Type-Options`,
  `X-Frame-Options`) — só o bloco HTTPS comentado os traz (B-03).
- O upload de certificado valida apenas a extensão e salva antes de inspecionar; o nome do
  arquivo mantém parte do nome original (M-03/B-02).

## Descrição
Como **responsável de segurança**, quero limites de taxa, cabeçalhos de proteção e upload
endurecido, para reduzir abuso e exposição em endpoints públicos.

## Critérios de Aceite
- [x] Rate limiting na rota pública de validação (30/min) e no login (10/min, só POST).
- [x] Página pública de validação expõe só o mínimo — **removido o título** (podia conter PII clínica); mantém tipo, assinante, data, código, hash e resultado de integridade.
- [x] Cabeçalhos de segurança no bloco Nginx **ativo** (dev): CSP, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy` (sem HSTS no dev — S-03). CSP também adicionado ao snippet de produção.
- [x] Upload de certificado: salva em **temp** → **valida** conteúdo/senha → **move** para destino com nome **uuid** (sem nenhuma parte do nome original).

## Tarefas
1. [x] Flask-Limiter (`4.1.1`) nas rotas pública e de login.
2. [x] `certificado/validar.html` minimizado (sem título/PII).
3. [x] Cabeçalhos de segurança no `nginx/conf.d/server-dev.conf` (bloco ativo) + CSP no `security-headers.conf` (prod).
4. [x] Fluxo de upload refatorado (temp → validar → `shutil.move` para `uuid.<ext>`).
5. [x] `tests/test_seguranca_s09.py` (5 testes); suíte completa **52 passed**.

## Implementação (resumo @dev)
- `extensions.py`: `limiter = Limiter(key_func=get_remote_address)` (IP respeita ProxyFix); `init_app` no factory.
- `config.py`: `RATELIMIT_ENABLED` (True; **False** em `TestingConfig` p/ evitar flakiness), `RATELIMIT_STORAGE_URI=memory://` (usar Redis em produção multi-worker), `RATELIMIT_LOGIN`, `RATELIMIT_VALIDACAO_PUBLICA`.
- `routes/auth.py`: `@limiter.limit(... , methods=["POST"])` no login (não limita o GET da tela).
- `routes/certificado.py`: `@limiter.limit` na validação pública; upload endurecido (mkstemp → `inspecionar_certificado` → `shutil.move` para `uuid4().hex.<ext>`); removido `secure_filename` (não mais necessário).
- `templates/certificado/validar.html`: sem o título do documento (PII).
- `nginx/conf.d/server-dev.conf`: CSP/nosniff/X-Frame/Referrer no `location /` (sem HSTS). `security-headers.conf` (prod) ganhou CSP.

## Verificação
- `pytest`: **52 passed** (5 novos + 47 existentes, sem regressão).
  - Rate limit: 429 ao exceder no login (POST) e na validação pública; GET do login não é limitado.
  - Upload: arquivo persistido com nome `^[0-9a-f]{32}\.p12$` (sem o nome original).
  - Página pública não renderiza o título com PII.
- `nginx -t`: OK no bloco dev com os novos headers.
- `ruff`: limpo. `pip-audit`: sem vulnerabilidades (Flask-Limiter incluído).

## Notas
- **CSP** permite `'unsafe-inline'` e `cdn.jsdelivr.net` (Bootstrap/ícones/HTMX inline). É um ponto de partida pragmático; endurecer (nonces, remover inline) é evolução futura.
- **Storage do rate limit** é em memória (por processo). Em produção com múltiplos workers Gunicorn, configurar `RATELIMIT_STORAGE_URI` para Redis para que o limite seja global.
- Próximo passo: **@qadv `*qa 9`**.

---

## QA — @qadv (`*qa 9`)

**Resultado:** ✅ **APROVADO** na primeira rodada.

### Método
Revisão de código + suíte completa + **probes de borda** (upload inválido) +
verificação **em runtime** dos headers na resposta HTTP real.

### Evidências
| Critério | Verificação | Resultado |
|----------|-------------|-----------|
| Rate limit login + validação pública | 429 ao exceder (POST login; GET validação) | ✅ |
| GET do login não limitado | 6 GETs → 200 | ✅ |
| Upload nome uuid | arquivo persistido `^[0-9a-f]{32}\.p12$` | ✅ |
| Upload valida antes de persistir | `.p12` inválido → **nenhum** CertificadoDigital criado, nada na pasta final | ✅ (probe @qadv) |
| Página pública sem PII | título com nome de paciente não aparece | ✅ |
| Headers no bloco ativo (dev) | `curl -I` real: CSP + nosniff + X-Frame + Referrer, **sem HSTS** | ✅ |
| Regressão | suíte completa | **52 passed** |
| CI parity | ruff limpo, pip-audit limpo, `nginx -t` OK | ✅ |

### Probe adicional do @qadv
- **Rejeição de upload inválido:** enviei um `.p12` com conteúdo falso; a validação
  no arquivo temporário falhou e **nada** foi persistido (nem registro, nem arquivo
  na pasta final). Confirma o requisito "validar antes de persistir" — o teste do
  @dev só cobria o caminho feliz (nome uuid).
- **Headers em runtime:** subi o nginx dev com upstream stub e confirmei os 4 headers
  de segurança na resposta e a **ausência** de HSTS (coerente com S-03).

### Observações (não bloqueantes, aceitas)
- **CSP com `'unsafe-inline'` + CDN** é pragmática (Bootstrap/HTMX inline). Endurecer
  com nonces é evolução futura — o @dev já sinalizou.
- **Rate limit em memória** (por worker). Em produção multi-worker, configurar
  `RATELIMIT_STORAGE_URI` para Redis para limite global — documentado.
- `import` locais (tempfile/uuid/shutil) dentro da função de upload seguem o padrão
  já usado no projeto; ruff limpo. Sem objeção.
