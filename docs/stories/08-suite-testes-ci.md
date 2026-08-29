# Story S-08 — Suíte de testes automatizados + CI

**Épico:** Base e Segurança / Qualidade (NFR-06)
**Prioridade:** P1
**Status:** Concluído
**Origem:** @architect (qualidade) · apoia S-01..S-06

---

## Contexto
O diretório `backend/tests/` está **vazio** e não há pipeline de CI (`.github/workflows`
ausente), embora `pytest`, `pytest-flask`, `pytest-cov` e `factory-boy` já estejam no
`requirements.txt`. Sem testes/CI, as correções de segurança (RBAC, IDOR, config) podem
regredir silenciosamente.

## Descrição
Como **time de desenvolvimento**, quero testes automatizados e um CI, para garantir que as
correções de segurança e os fluxos clínicos críticos não quebrem a cada mudança.

## Critérios de Aceite
- [x] Suíte `pytest` com `TestingConfig` (SQLite in-memory, CSRF off) — 47 testes.
- [x] Cobertura dos fluxos críticos: autenticação (S-06), **RBAC (S-01)**, **IDOR (S-02)**, validação de config (S-04), auditoria LGPD (S-07) e **fluxo clínico ponta a ponta** (admissão → prescrição → prontuário → alta + laudo PDF).
- [x] Pipeline CI (GitHub Actions `ci.yml`): instalação, **lint (ruff)**, `flask db upgrade` em Postgres efêmero e `pytest`, a cada push/PR.
- [x] CI inclui `pip-audit` (apoia S-05).
- [x] Build falha se lint, migração, testes ou `pip-audit` falharem (cada passo é bloqueante).

## Tarefas
1. [x] `tests/` já estruturado com fixtures (app/db/usuários por perfil) — reforçado.
2. [x] Testes de auth/RBAC/IDOR/config já existiam (S-04/06/07); mantidos verdes.
3. [x] `tests/test_fluxo_clinico.py` — fluxo clínico integrado (3 testes).
4. [x] `.github/workflows/ci.yml` (ruff + `flask db upgrade` + pytest + pip-audit).
5. [x] Seção **Testes e CI** no `README.md`.

## Implementação (resumo @dev)
- **Fluxo clínico E2E** (`test_fluxo_clinico.py`): cria leito+paciente+prontuário,
  admite, prescreve item, visualiza o prontuário **pela rota** (integra RBAC +
  auditoria), dá alta e gera o **laudo em PDF** (reportlab → valida assinatura `%PDF`);
  + teste de 403 para perfil sem `internacao.ver`.
- **Bug real corrigido:** o teste E2E revelou `Internacao.dias_internado` estourando
  `TypeError` (subtração de datetime naive × aware) — o SQLite devolve datetimes sem
  timezone mesmo em coluna `DateTime(timezone=True)`. Normalizado para UTC-aware.
- **Lint:** `ruff` adicionado (`pyproject.toml`: regras E9/F/B/I; exclui `migrations`).
  Rodado `ruff --fix` → removidos 27 imports não usados e ordenados 54 blocos de
  import em toda a base. Codebase agora **lint-clean**.
- **CI:** `ci.yml` com serviço Postgres 16, cache de pip, e 4 passos bloqueantes.
- **Migração:** gerado/commitado `d8cb1d8248c9` (tabela `logs_acesso` da S-07 +
  `pacientes.criado_por_id` NOT NULL), para que `flask db upgrade` produza o schema
  completo no CI/produção sem depender de autogenerate no boot.
- **Deps de CI:** `ruff==0.16.5`, `pip-audit==2.10.1` (versões confirmadas no PyPI).

## Verificação (todos os passos do CI rodados localmente)
- `ruff check .` → **All checks passed!**
- `flask db upgrade` em Postgres efêmero (do zero) → schema correto; `logs_acesso`
  criado e `criado_por_id` NOT NULL confirmados via `information_schema`.
- `pytest` → **47 passed** (44 existentes + 3 do fluxo clínico).
- `pip-audit` → **No known vulnerabilities found**.

## Notas
- A limpeza de imports pelo `ruff --fix` tocou vários arquivos; validada pela suíte
  completa + `ruff` limpo + diagnósticos sem erro (sem regressão).
- O CI em si (execução no GitHub) não pôde ser disparado localmente; cada passo foi
  reproduzido em container equivalente ao runner.
- Próximo passo: **@qadv `*qa 8`**.

---

## QA — @qadv (`*qa 8`)

**Resultado:** ✅ **APROVADO** na primeira rodada.

### Método
Reproduzi **todos os passos do CI** localmente em container equivalente ao runner
(o GitHub Actions em si não pode ser disparado daqui), + revisão do `ci.yml`,
integridade da cadeia de migração e um probe extra do bug corrigido.

### Evidências
| Critério | Verificação | Resultado |
|----------|-------------|-----------|
| Suíte com TestingConfig | `pytest -q --cov=app` | **47 passed**, cobertura 65% |
| Fluxo clínico E2E | `test_fluxo_clinico.py` | admissão→prescrição→prontuário(rota)→alta + laudo PDF (`%PDF`) ✅ |
| CI lint + migração + testes | ruff / `flask db upgrade` / pytest | todos exit 0 ✅ |
| CI pip-audit | `pip-audit` | **No known vulnerabilities found** ✅ |
| Build falha em qualquer etapa | passos bloqueantes no `ci.yml` | ✅ |
| Integridade da migração | `flask db heads` / `db current` | **1 head** (`d8cb1d8248c9`); upgrade do zero chega ao head ✅ |

### Probe adicional do @qadv
- **Bug tz do `dias_internado`:** confirmei que o fix cobre também o caso **ativo**
  (sem `alta_em`) — que era exatamente o caminho do crash original — e retorna `int`
  sem `TypeError`. O teste E2E do @dev só exercitava o caso com alta.

### Observações (não bloqueantes)
- **Least-privilege no CI:** o `ci.yml` não declara `permissions:`. Para um workflow
  só de testes os defaults bastam, mas recomendo pinar `permissions: contents: read`
  como hardening. Não bloqueia.
- **Execução real no GitHub** só será confirmada no primeiro push; cada passo foi
  reproduzido fielmente em container.
- A limpeza de imports pelo `ruff --fix` foi ampla mas segura (suíte verde + ruff
  limpo + `flask db upgrade` ok).

### Nota de processo
- @dev encontrou e corrigiu um **bug real de produção latente** (`dias_internado`
  naive×aware) graças ao teste E2E — exatamente o valor que a S-08 deveria entregar.
- A migração `d8cb1d8248c9` (S-07) foi commitada aqui; bom, pois torna o schema
  reprodutível via `flask db upgrade` sem depender do autogenerate no boot.
