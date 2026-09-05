# Story Q-MT-03 — Super-Admin e CRUD de Empresas

**Épico:** SAAS Multi-tenant (FR-MT-02 / FR-MT-03)
**Prioridade:** P0
**Status:** A fazer
**Origem:** `docs/plano-quiron-multitenant.md` (Fase MT-3), PRD v2.0
**Branch:** `quiron`
**Depende de:** Q-MT-02

---

## Contexto
O operador do SAAS (Super-Admin) precisa de uma área própria, isolada dos dados clínicos,
para vender e cadastrar empresas-clientes e gerir o ciclo de vida delas.

## Descrição
Como **Super-Admin**, quero cadastrar, editar, listar e mudar o status das empresas, e opcionalmente
criar o usuário administrador de cada empresa no momento do cadastro.

## Critérios de Aceite
- [ ] Decorator `@requer_super_admin` (em `utils/authz.py`): 403 para quem não for Super-Admin.
- [ ] Blueprint `routes/admin_saas.py` sob `/admin`, **sem** acesso a dados clínicos de nenhuma empresa.
- [ ] CRUD de empresas: listar, criar, editar, detalhe, e ações de status
  (ativar / suspender / cancelar / iniciar trial), com confirmação nas ações sensíveis.
- [ ] Ao criar empresa, opção de **provisionar o admin daquela empresa**: cria o `Usuario`
  (perfil Administrador do tenant, `deve_trocar_senha=True`) e semeia perfis/permissões padrão.
- [ ] Seed de um **Super-Admin inicial** (credenciais via env; troca obrigatória no 1º acesso).
- [ ] Empresa suspensa/cancelada **bloqueia login** dos usuários daquela empresa (mensagem clara).
- [ ] Testes: acesso negado a não-super-admin; criação de empresa + admin; bloqueio por status.

## Tarefas
1. `@requer_super_admin` + ajustes no `before_request` (Super-Admin não entra no fluxo de tenant de negócio).
2. `routes/admin_saas.py` + formulários (FlaskForm) + templates `templates/admin/`.
3. Provisionamento do admin da empresa (reuso de `seed_perfis_padrao`/`seed_permissoes` escopado ao tenant).
4. Seed do Super-Admin no `entrypoint.sh` (idempotente; credenciais via env).
5. Regra de login que bloqueia empresa não-ativa.
6. Testes (`tests/test_super_admin.py`, `tests/test_crud_empresas.py`).

## Notas
- O Super-Admin **não** tem `empresa_id`; suas telas nunca instanciam queries de negócio (só `Empresa` e agregados).
- Menu/navbar do Super-Admin é distinto do menu de usuário de empresa.
- Personalização (logo/nome) da empresa alimenta o branding por tenant (FR-MT-06).
