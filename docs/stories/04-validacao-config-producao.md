# Story S-04 — Validação de configuração e segredos em produção

**Épico:** Base e Segurança (NFR-04)
**Prioridade:** P0 — **bloqueia produção** (veto @si)
**Status:** Concluído
**Origem:** @si A-06 (Alto) · @architect S2

---

## Contexto
`Config.SECRET_KEY` tem fallback fraco hardcoded (`"troque-antes-de-produção"`) e
`ProductionConfig.validate()` existe mas **nunca é chamado** no `create_app`. Uma produção mal
configurada roda com chave previsível — compromete a assinatura da sessão (agravado pelo
CVE-2025-47278 do Flask).

## Descrição
Como **administrador de TI**, quero que o sistema **se recuse a subir em produção** sem os
segredos obrigatórios, para evitar operar com configuração insegura.

## Critérios de Aceite
- [x] `create_app` chama `ProductionConfig.validate()` quando `FLASK_ENV=production`.
- [x] A aplicação **falha rápido** (`RuntimeError` no boot) se faltar `SECRET_KEY`, `DATABASE_URL` ou `POSTGRES_PASSWORD` em produção.
- [x] Em produção, o `SECRET_KEY` **nunca** usa o fallback hardcoded — a validação inspeciona o valor **efetivo** de `app.config["SECRET_KEY"]` e rejeita defaults/placeholders.
- [x] `.env.example` e README reforçam a geração de `SECRET_KEY` forte.

## Tarefas
1. [x] `ProductionConfig.validate(app.config)` invocado no factory sob `FLASK_ENV=production`.
2. [x] Default hardcoded + placeholder do `.env.example` na lista `FORBIDDEN_SECRET_KEYS`.
3. [x] Mensagem de erro clara: prefixo + lista de variáveis ausentes e/ou SECRET_KEY previsível.
4. [x] Testes em `tests/test_config_producao.py` (5 casos) — todos passando; suíte completa 22/22.

## Implementação (resumo @dev)
- `backend/app/config.py`: `validate(app_config=None)` valida o **SECRET_KEY efetivo**
  (não só a env var), com `REQUIRED_ENV` e `FORBIDDEN_SECRET_KEYS`.
- `backend/app/__init__.py`: em produção chama `ProductionConfig.validate(app.config)`.
  Também **re-resolve** `SECRET_KEY` do ambiente após `from_object` — as classes de
  Config congelam o valor no import, então sem isso o valor default poderia vazar
  para produção mesmo com a env var setada (bug latente encontrado via teste).
- `README.md`: nota de produção reforçando a validação de boot e a geração de chave forte.
- `.env.example`: já traz o comando `secrets.token_hex(32)` para `SECRET_KEY`.

## Verificação
- `pytest` dentro da imagem do app: **22 passed** (5 novos de S-04 + 17 existentes, sem regressão).
- Casos cobertos: sem segredos → falha; SECRET_KEY default/placeholder → falha; segredos válidos → sobe (com `SESSION_COOKIE_SECURE=True`); dev sobe com defaults.

## Notas
- Dev/test continuam funcionando com defaults (validação só em `production`).
- Próximo passo: **@qadv `*qa 4`** antes de `Concluído`.

---

## QA — @qadv (`*qa 4`)

**Resultado:** ✅ **APROVADO** na primeira rodada.

### Método
Revisão de código + execução da suíte + verificação do **caminho real de boot**
(`wsgi.py`, o mesmo usado pelo Gunicorn em produção) dentro da imagem do app.

### Evidências
| Critério | Verificação | Resultado |
|----------|-------------|-----------|
| `validate()` chamado em produção | `create_app`/`wsgi.py` sob `FLASK_ENV=production` | ✅ |
| Falha rápido sem segredos | `import wsgi` sem env → **exit 1** + `RuntimeError` listando `SECRET_KEY`/`DATABASE_URL`/`POSTGRES_PASSWORD` | ✅ |
| SECRET_KEY default rejeitado | vars presentes + `SECRET_KEY=troque-antes-de-produção` → **exit 1** com mensagem específica | ✅ |
| Placeholder `.env.example` rejeitado | `TROQUE_PARA_UM_VALOR_SECRETO_FORTE` na `FORBIDDEN_SECRET_KEYS` (teste) | ✅ |
| Boot OK com segredos válidos | `import wsgi` com chave forte → **exit 0**, `SESSION_COOKIE_SECURE=True` | ✅ |
| Dev/test com defaults | dev sobe sem validação estrita | ✅ |
| Docs reforçam SECRET_KEY forte | README + `.env.example` (`secrets.token_hex(32)`) | ✅ |
| Regressão | suíte completa | **22 passed** |

### Pontos fortes observados
- O @dev encontrou e corrigiu um **bug latente**: as classes `Config` congelam o
  `SECRET_KEY` no import; a validação passou a checar o valor **efetivo** em
  `app.config` e o factory re-resolve a env var. Isso fecha o vetor do contexto
  (chave previsível chegando à produção, agravado pelo CVE-2025-47278).
- Mensagem de erro clara e acionável (inclui o comando para gerar chave forte).
- O placeholder do `.env.example` está na lista de proibidos — quem esquecer de
  trocar é bloqueado no boot de produção.

### Observação (não bloqueante)
- A validação não impõe entropia mínima (uma chave curta não-default como `"123"`
  passaria). Está **dentro do escopo** da story (que exige rejeitar apenas
  default/placeholders). Se desejável, endurecer entropia é tema para nova story.
