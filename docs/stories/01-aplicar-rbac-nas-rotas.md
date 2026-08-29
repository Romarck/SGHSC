# Story S-01 — Aplicar RBAC (autorização por permissão) nas rotas

**Épico:** Base e Segurança (FR-02 / NFR-01)
**Prioridade:** P0 — **bloqueia produção** (veto @si)
**Status:** Concluído (aprovado no QA do @qadv em 2026-08-28)
**Origem:** @si C-01 (Crítico) · @architect S1

---

## Contexto
O modelo `Usuario → Perfil → Permissao` e `Usuario.tem_permissao()` existem, mas **nenhuma
rota chama `tem_permissao`**. Hoje todas as rotas usam apenas `@login_required`, de modo que
qualquer usuário autenticado acessa qualquer módulo (prescrição, alta, faturamento, RH,
financeiro). Isso viola o menor privilégio e o sigilo do prontuário.

## Descrição
Como **administrador de TI da Santa Casa**, quero que cada rota sensível exija a **permissão
específica** do perfil do usuário, para que cada profissional acesse apenas o que lhe compete.

## Critérios de Aceite
- [ ] Existe um decorator `@requer_permissao("modulo.acao")` reutilizável que retorna **403**
  (template `errors/403.html`) quando o usuário não tem a permissão.
- [ ] O decorator é aplicado em **todas as rotas de escrita/ação sensível** dos módulos
  clínicos e administrativos (prescrição, evolução, alta, dispensação, faturamento, financeiro,
  RH, estoque, patrimônio, usuários).
- [ ] As `Permissao` no formato `modulo.acao` são **semeadas** e associadas aos 15 perfis
  (`TipoPerfil`) via seed/migração idempotente.
- [ ] O perfil **Administrador** mantém acesso total.
- [ ] Rotas públicas conhecidas (ex.: `/certificado/validar/<codigo>`) permanecem sem exigência.
- [ ] Um usuário sem permissão recebe 403 e o evento é logado.

## Tarefas
1. Criar `app/utils/authz.py` com `requer_permissao(codigo)` (usa `current_user.tem_permissao`).
2. Definir o catálogo de permissões por módulo/ação e o mapeamento perfil→permissões.
3. Criar seed idempotente (script ou etapa no `entrypoint.sh`/comando Flask) das permissões.
4. Aplicar o decorator nas rotas sensíveis (revisar blueprint por blueprint).
5. Testes: usuário com/sem permissão em rotas representativas (200 vs 403).

## Notas
- Não substituir `@login_required` — a autorização é adicional à autenticação.
- Depende de S-06 apenas no sentido de higiene de auth; pode seguir em paralelo.

---

## Implementação (@dev)

**Arquivos criados**
- `app/utils/authz.py` — decorator `requer_permissao("modulo.acao")` (403 + log; Administrador tem acesso total).
- `app/security/permissoes.py` — `CATALOGO` (52 permissões), `PERFIL_PERMISSOES` (mapeamento por `TipoPerfil`, com curinga `modulo.*`) e `seed_permissoes()` idempotente.
- `tests/conftest.py`, `tests/test_rbac.py`, `tests/test_permissoes_seed.py` — suíte de testes.

**Arquivos alterados**
- `app/__init__.py` — comando CLI `flask seed-permissoes` registrado.
- `entrypoint.sh` — chama `seed_permissoes()` no boot (idempotente), após criar o admin.
- Rotas decoradas com `@requer_permissao(...)` (adicional ao `@login_required`) em:
  pacientes, emergencia, ambulatorio, internacao, exames, farmacia, nutricao, ccih,
  cirurgias, maternidade, certificado, estoque, compras, financeiro, faturamento,
  convenios, patrimonio, rh, manutencao, relatorios, residuos, rnds.

**Critérios de aceite — situação**
- [x] Decorator `@requer_permissao` retorna 403 e loga o evento.
- [x] Aplicado nas rotas de ação sensível dos módulos clínicos e administrativos.
- [x] Permissões `modulo.acao` semeadas e associadas por perfil (seed idempotente).
- [x] Administrador mantém acesso total (curto-circuito no decorator).
- [x] Rota pública `/certificado/validar/<codigo>` permanece sem exigência.
- [x] Usuário sem permissão recebe 403; o evento é logado.

**Verificação**
- `pytest tests/` → **11 passed** (RBAC: 403 sem permissão, acesso com permissão,
  admin total, anônimo redirecionado ao login; seed: catálogo completo e idempotência).
- `flask seed-permissoes` no container (PostgreSQL) → 52 permissões criadas, sem erro.
- `create_app` importa e registra 145 rotas sem erro.

**Observações para o @qadv / próximos passos**
- Permissão `usuarios.gerir` está no catálogo, mas ainda **não há rota** de gestão de
  usuários (blueprint inexistente) — decorator será aplicado quando a tela existir.
- A verificação de **vínculo com o paciente** (evitar IDOR) é escopo da **S-02**; aqui
  garantimos a permissão de módulo. `baixar_laudo_alta` e downloads recebem, por ora,
  permissão de visualização do módulo.

---

## QA (@qadv) — APROVADO ✅

**Data:** 2026-08-28 · **Veredito:** Aprovado (quality gate passou)

Verificação independente (não baseada apenas no relatório do @dev):

| Verificação | Método | Resultado |
|-------------|--------|-----------|
| Testes passam | `pytest tests/ -v` no container | **11 passed** |
| Cobertura de rotas de ação | varredura de todas as rotas POST/GET+POST sem `requer_permissao` | Só exceções legítimas: `auth.login`, `auth.trocar_senha`, `certificado.desativar` (self-scoped por `usuario_id`) |
| Ordem dos decorators | `requer_permissao` sempre abaixo de `@login_required` | **0 problemas** (auth roda primeiro) |
| Consistência do catálogo | códigos usados nas rotas × `CATALOGO` | **0 órfãos**; 51 usados / 52 no catálogo (`usuarios.gerir` reservado) |
| Template 403 | `app/templates/errors/403.html` | Presente |
| Branch defensivo sem perfil | probe de `_usuario_autorizado` | Retorna 403 sem crash |
| Admin acesso total | teste `test_admin_acesso_total` | OK |
| Anônimo → login (não 403) | teste `test_anonimo_redireciona_para_login` | OK (302 → /auth/login) |

**Critérios de aceite:** todos atendidos.

**Ressalvas (não bloqueantes) repassadas ao backlog:**
- IDOR por objeto (vínculo com paciente em downloads) permanece em aberto — **é escopo da S-02** (já priorizada P0). O RBAC de módulo não substitui essa verificação.
- Cobertura de teste pode crescer: falta caso explícito para usuário sem perfil e asserção de log do 403 (baixo risco; comportamento já validado manualmente por probe).
- `usuarios.gerir` sem rota correspondente ainda (aguarda tela de gestão de usuários).

**Encaminhamento:** S-01 concluída. Recomenda-se ao `@si` **reauditar** (`*audit-code`)
para confirmar o fechamento do achado C-01 antes de levantar o veto de pré-produção
(pendem ainda S-02, S-03, S-04 na barreira P0).

---

## QA — reconfirmação (@qadv `*qa 1`, 2026-08-29)

Já **Concluída/Aprovada** em 2026-08-28. Reexecutei o QA a pedido para confirmar
que as mudanças posteriores (S-03…S-10) **não regrediram** o RBAC:

- `requer_permissao` intacto em `app/utils/authz.py` e ainda aplicado nas rotas.
- `pytest tests/test_rbac.py tests/test_permissoes_seed.py` → **11 passed** no
  codebase atual (com todas as stories subsequentes integradas).

**Veredito mantido:** ✅ APROVADO. Sem novas ressalvas.
