# Reauditoria de Segurança (pré-produção) — SGHSC

**Agente:** @si (Segurança & Compliance)
**Comando:** `*audit-code` (reauditoria das 7 fases)
**Data:** 2026-08-29
**Referência:** `docs/security/audit-report.md` (auditoria original, 2026-08-28)
**Escopo de compliance:** LGPD + normas de saúde (CFM/PEP, ANVISA). BCB/FEBRABAN/B3/CVM fora de escopo.

---

## Parecer geral

> ✅ **VETO DE PRÉ-PRODUÇÃO LEVANTADO.** Todos os achados **Crítico** e **Altos que
> bloqueavam produção** foram corrigidos e reverificados. O sistema está **liberado para
> produção com dados reais de pacientes**, condicionado às ações operacionais de deploy
> (backup, TLS real, segredos fortes) e ao acompanhamento dos itens "Plano" abaixo.

Verificação independente feita sobre o codebase integrado (S-01…S-10): leitura de código,
`pytest` (**52 passed**), `pip-audit` (**sem vulnerabilidades**), `nginx -t` e boot real em
container. Não me baseei apenas nos relatórios de @dev/@qadv.

---

## Reverificação por achado

| ID | Sev. | Achado original | Story | Status | Evidência (independente do @si) |
|----|------|-----------------|-------|--------|----------------------------------|
| **C-01** | 🔴 Crítico | RBAC não aplicado | S-01 | ✅ **Fechado** | `@requer_permissao("modulo.acao")` aplicado em todos os blueprints sensíveis; `test_rbac.py`/`test_permissoes_seed.py` verdes; Administrador com acesso total; rota pública isenta. |
| **A-01** | 🟠 Alto | Cookie sem Secure + HTTPS off | S-03 | ✅ **Fechado** | `ProductionConfig.SESSION_COOKIE_SECURE=True`; `ProxyFix` confia em `X-Forwarded-Proto`. |
| **A-02** | 🟠 Alto | IDOR/BOLA em downloads | S-02 | ✅ **Fechado** | `autorizar_recurso()` **antes** do `send_file` em `baixar_documento`/`desativar`; `test_idor.py` (6) verdes; 403 antes do 404. |
| **A-03** | 🟠 Alto | Sem TLS em trânsito | S-03 | ✅ **Fechado** | `listen 443 ssl` (TLS 1.2/1.3), redirect 80→443, HSTS — validado em runtime no QA da S-03. |
| **A-06** | 🟠 Alto | SECRET_KEY fraca + validate() não chamado | S-04 | ✅ **Fechado** | `ProductionConfig.validate(app.config)` no factory (linha 45); rejeita default/placeholder; boot de produção aborta sem segredos. |
| **A-05** | 🟠 Alto | Werkzeug/cryptography com CVE | S-05 | ✅ **Fechado** | Werkzeug 3.1.8, cryptography 50.0.1; `pip-audit`: **No known vulnerabilities found**. |
| **M-01** | 🟡 Médio | Contador revela usuário | S-06 | ✅ **Fechado** | Mensagem genérica única; sem contador. |
| **M-02** | 🟡 Médio | Política de senha fraca | S-06 | ✅ **Fechado** | ≥10 + complexidade + blocklist (`password_policy.py`). |
| **M-03** | 🟡 Médio | Upload de cert sem validação de conteúdo | S-09 | ✅ **Fechado** | temp → valida → move; inválido não persiste (probe QA). |
| **M-04** | 🟡 Médio | Sem log de acesso a prontuário | S-07 | ✅ **Fechado** | `LogAcesso` + `registrar_acesso()` nas rotas de leitura; relatório `/auditoria/`. |
| **M-05** | 🟡 Médio | Flask/Pillow com CVE | S-05 | ✅ **Fechado** | Flask 3.1.3, Pillow 12.3.0; audit limpo. |
| **M-07** | 🟡 Médio | Rota pública sem rate limit | S-09 | ✅ **Fechado** | Flask-Limiter em `/certificado/validar` (30/min) e login (10/min); 429 testado. |
| **B-01** | ⚪ Baixo | remember-me em estação compartilhada | S-06 | ✅ **Fechado** | Desabilitado por padrão (`LOGIN_REMEMBER_HABILITADO=False`). |
| **B-02** | ⚪ Baixo | Nome de upload | S-09 | ✅ **Fechado** | Nome `uuid4().hex.<ext>`, sem o nome original. |
| **B-03** | ⚪ Baixo | Headers de segurança no Nginx ativo | S-09 | ✅ **Fechado** | CSP/nosniff/X-Frame/Referrer no bloco dev (sem HSTS) e prod; validado em runtime. |
| **I-01** | ⚪ Info | `migrate` no boot | S-10 | ✅ **Fechado** | Produção só `flask db upgrade`; falha aborta o boot (exit 1) — validado em runtime. |
| **M-06** | 🟡 Médio | Admin seed com senha fixa | — | 🟨 **Plano** | Ainda cria `admin/Admin@123` (troca obrigatória no 1º acesso via S-06). Mitigado, não fechado. |
| **A-04** | 🟠 Alto | Dados em repouso sem cifra | — | 🟨 **Plano** | **Não implementado.** Marcado como "Plano" na auditoria original (não bloqueava produção). Ver abaixo. |

**Extra (fora dos achados originais):** S-08 adicionou suíte de testes + CI (ruff, `flask db
upgrade` efêmero, pytest, `pip-audit`) — reduz risco de regressão dos controles de segurança.

---

## Itens remanescentes (não bloqueiam o veto, exigem acompanhamento)

### A-04 — Criptografia de dados em repouso (Alto, "Plano")
Continua **em aberto**. Na auditoria original foi classificado como "Plano" (não bloqueia
produção) por ser mitigável no nível de infraestrutura. **Exigência para o go-live real:**
- Criptografia de disco/volume do PostgreSQL e do storage de PDFs (ex.: LUKS/volume cifrado
  do provedor) **e** backup cifrado. Isso pode ser satisfeito no provisionamento de
  infraestrutura sem mudança de código.
- Recomendo abrir story dedicada (`@po`) se a cifra de coluna (ex.: campos de identificação)
  for exigida pelo DPO além da cifra de volume.

### M-06 — Segredo inicial do admin (Médio, mitigado)
`entrypoint.sh` cria `admin/Admin@123` com `deve_trocar_senha=True`. Aceitável como bootstrap,
mas recomendo, para produção: gerar senha inicial aleatória (ou exigir via env var) e não logar
o valor. Story de higiene futura.

### Hardening operacional recomendado (documentado, a executar no deploy)
- **Rate limit com storage compartilhado** (Redis) em produção multi-worker (hoje memória por
  worker) — `RATELIMIT_STORAGE_URI`.
- **Grants do banco** para a trilha de auditoria: app com INSERT/SELECT em `logs_acesso`
  (purga por papel separado) — ver `docs/security/auditoria-lgpd.md`.
- **CSP** endurecer (remover `'unsafe-inline'` via nonces) — evolução.
- **Backup do banco antes de cada `flask db upgrade`** em produção (`docs/migracao-producao.md`).

---

## Compliance LGPD (síntese)

- **Criptografia em trânsito:** ✅ (S-03).
- **Controle de acesso / menor privilégio:** ✅ (S-01/S-02).
- **Accountability / trilha de acesso a dado sensível:** ✅ (S-07) — escopo coberto:
  prontuário, cadastro do paciente e documento clínico assinado. **Nota:** exames e
  maternidade podem ser instrumentados em evolução; considero suficiente para o go-live,
  com recomendação de ampliar.
- **Criptografia em repouso:** 🟨 pendente (A-04) — cobrir via infraestrutura antes de
  processar dados reais.

---

## Veredito (Artigo II da Constituição)

**Veto de pré-produção: LEVANTADO.** ✅
Todos os bloqueadores (C-01, A-01, A-02, A-03, A-06) fechados e reverificados; SCA limpo.
Liberação condicionada a: (1) TLS com certificado real, (2) `SECRET_KEY` forte por env,
(3) criptografia de volume + backup cifrado (A-04) no provisionamento, (4) troca imediata da
senha do admin. Itens "Plano" (A-04, M-06) devem ser rastreados como stories/issues.

---

*Gerado pelo PDA-SQUAD v1.0.0 — comando `@si *audit-code` (reauditoria)*
