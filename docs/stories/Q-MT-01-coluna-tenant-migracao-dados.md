# Story Q-MT-01 — Coluna `empresa_id` nas tabelas raiz + migração da empresa-modelo

**Épico:** SAAS Multi-tenant (FR-MT-04)
**Prioridade:** P0
**Status:** A fazer
**Origem:** `docs/plano-quiron-multitenant.md` (Fase MT-1), PRD v2.0
**Branch:** `quiron`
**Depende de:** Q-MT-00

---

## Contexto
Com a entidade `Empresa` criada, é hora de dar "dono" a cada dado. Adicionamos `empresa_id`
às **tabelas raiz** de cada agregado (tabelas filhas herdam pela FK ao pai) e migramos os
dados existentes para a primeira empresa: **Santa Casa de Pedralva**.

## Descrição
Como **arquiteto do sistema**, quero que todo registro de negócio pertença a uma empresa,
para permitir o isolamento por tenant sem deixar dados órfãos.

## Critérios de Aceite
- [ ] `empresa_id` (FK → `empresas.id`, indexado) adicionado às **tabelas raiz** (lista no plano, seção 3.2).
- [ ] Tabelas de catálogo global (ex.: `permissoes`) permanecem **sem** `empresa_id`.
- [ ] **Data migration** Alembic cria a empresa "Santa Casa de Pedralva" e faz o **backfill**
  de `empresa_id` em TODOS os registros existentes, vinculando-os a ela.
- [ ] Após o backfill, `empresa_id` das tabelas raiz é tornado **NOT NULL**.
- [ ] Usuários existentes recebem `empresa_id` = Pedralva; o `admin` atual permanece admin **da empresa**.
- [ ] Unicidade ajustada para escopo por empresa onde fizer sentido:
  `usuarios(empresa_id, username)` e `usuarios(empresa_id, email)`; `pacientes(empresa_id, cpf)` etc.
- [ ] `0` registros órfãos após a migração (verificação/contagem no fim da migração).
- [ ] App sobe e testes passam.

## Tarefas
1. Adicionar `empresa_id` aos models raiz (paciente, prontuário, internação, farmácia, estoque, financeiro, etc.).
2. Ajustar constraints de unicidade globais para compostas por empresa.
3. Escrever a data migration: criar Pedralva → backfill → SET NOT NULL → ajustar uniques.
4. Verificação pós-migração (contagem de órfãos = 0) dentro da própria migração/log.
5. Backup do banco antes de aplicar (documentar no procedimento — ver `docs/migracao-producao.md`).
6. Rodar suíte + upgrade local; conferir contagens por tabela.

## Notas
- Ainda **sem** filtro automático de leitura/escrita — isso é a MT-2. Aqui só estruturamos a coluna e migramos.
- A ordem de backfill respeita dependências (empresa primeiro, depois usuários, depois o resto).
- Atenção a `logs_acesso`: recebe `empresa_id` para escopar a trilha por tenant.
