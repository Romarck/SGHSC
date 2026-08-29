# Story S-10 — Migração de banco segura em produção

**Épico:** Base e Segurança / Operação (NFR-09)
**Prioridade:** P2
**Status:** Concluído
**Origem:** @si I-01 (Informativo) · @architect (risco operacional)

---

## Contexto
O `entrypoint.sh` roda `flask db migrate` (geração automática de migração) **no boot**, antes
do `upgrade`. Em produção, isso pode gerar migrações não revisadas automaticamente a partir do
estado dos models — risco de alteração de schema inesperada e difícil de reverter.

## Descrição
Como **operador do sistema**, quero que o boot em produção apenas **aplique** migrações já
revisadas, para evitar mudanças de schema não intencionais em ambiente com dados reais.

## Critérios de Aceite
- [x] Em produção, o boot executa **apenas `flask db upgrade`** (sem `migrate` nem `db init`).
- [x] `flask db migrate` só no fluxo de dev; procedimento de revisão/commit documentado.
- [x] Falha no `upgrade` **aborta o boot** (exit 1) com log claro — não sobe com schema inconsistente.
- [x] Procedimento de migração para produção documentado (gerar em dev → revisar → aplicar em prod) + recomendação de backup.

## Tarefas
1. [x] `entrypoint.sh`: branch `FLASK_ENV=production` → só `upgrade`; dev mantém `migrate`+`upgrade`.
2. [x] Tratamento de erro explícito no `upgrade` (mensagem + `exit 1`) em ambos os ramos.
3. [x] Fluxo documentado em `docs/migracao-producao.md` + seção no `README.md`.
4. [x] Backup antes do `upgrade` recomendado no boot (log) e na doc (`pg_dump`).

## Implementação (resumo @dev)
- `backend/entrypoint.sh`: seção `[2/4]` reescrita com dois ramos:
  - **produção** → apenas `flask db upgrade`; sem `db init`/`db migrate`; aborta com
    `exit 1` e mensagem clara se o upgrade falhar; loga recomendação de backup.
  - **dev/test** → mantém `db init` (1ª vez) + `db migrate -m auto` + `upgrade`.
- `docs/migracao-producao.md`: procedimento completo (gerar/revisar/commit em dev;
  backup + `upgrade` em prod; passos para NOT NULL com backfill; garantir 1 head).
- `README.md`: seção "Migrações de banco" apontando para a doc.

## Verificação
- **Lógica dos ramos** (stub de `flask`): produção chama **só** `db upgrade`
  (0 ocorrências de `db migrate`); dev chama `init`+`migrate`+`upgrade`.
- **Abort em falha:** `upgrade` falhando em produção → **exit 1** + log de erro.
- **Boot real ponta a ponta** (imagem do app + Postgres efêmero, `FLASK_ENV=production`):
  log mostra "Produção: aplicando migrações revisadas", Alembic roda **apenas upgrade**
  aplicando a cadeia até `d8cb1d8248c9`, e o **Gunicorn sobe** na 5000. Nenhum
  `db migrate` autogerado no boot.
- `bash -n entrypoint.sh`: sintaxe OK.

## Notas
- Observação (fora do escopo): o seed de boot ainda cria `admin/Admin@123` com troca
  obrigatória no 1º acesso (S-06). Endurecer o segredo inicial do admin em produção
  pode ser uma story futura.
- Próximo passo: **@qadv `*qa 10`**.

---

## QA — @qadv (`*qa 10`)

**Resultado:** ✅ **APROVADO** na primeira rodada.

### Método
Revisão do `entrypoint.sh`/doc + verificação **em runtime** com a imagem do app
contra um Postgres efêmero, cobrindo os dois comportamentos críticos.

### Evidências
| Critério | Verificação | Resultado |
|----------|-------------|-----------|
| Produção só `upgrade` (sem `migrate`) | boot com `FLASK_ENV=production`, backend montado | log "aplicando migrações revisadas"; **nenhum novo arquivo** em `migrations/versions/` (antes==depois); grep sem `migrate` ✅ |
| `migrate` só em dev | ramo `else` do entrypoint | ✅ |
| Falha aborta o boot com log claro | poisoned `alembic_version` → `flask db upgrade` falha | **exit code 1**, gunicorn **não** inicia (0), seed `[3/4]` **não** alcançado; mensagem de erro clara ✅ |
| Procedimento documentado + backup | `docs/migracao-producao.md` + README | ✅ (inclui `pg_dump` e passo NOT NULL com backfill) |

### Probes do @qadv
- **Não-geração em produção:** com o backend montado (um arquivo autogerado
  apareceria no host), o boot de produção **não criou** nenhuma migração — só aplicou.
- **Abort real:** corrompi a `alembic_version` para forçar erro no `upgrade`; o
  container saiu com **código 1**, sem subir o Gunicorn e sem chegar ao seed — ou
  seja, não roda a app com schema inconsistente.

### Observações (não bloqueantes)
- O seed de boot ainda cria `admin/Admin@123` (troca obrigatória no 1º acesso via
  S-06). Endurecer o segredo inicial do admin em produção é candidato a story futura
  — fora do escopo da S-10 (concordo com o @dev).
- `bash -n` limpo; mudança isolada ao shell (não afeta a suíte pytest).
