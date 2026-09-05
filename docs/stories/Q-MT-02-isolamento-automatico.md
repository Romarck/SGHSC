# Story Q-MT-02 — Isolamento automático de tenant (leitura, escrita e autorização)

**Épico:** SAAS Multi-tenant (FR-MT-04 / NFR-MT-01..03)
**Prioridade:** P0 — **bloqueia go-live SAAS** (risco crítico de vazamento entre empresas)
**Status:** A fazer
**Origem:** `docs/plano-quiron-multitenant.md` (Fase MT-2), PRD v2.0
**Branch:** `quiron`
**Depende de:** Q-MT-01

---

## Contexto
Com `empresa_id` presente, o isolamento **não pode** depender do desenvolvedor lembrar de
filtrar em cada uma das 154 rotas. O enforcement fica na **camada de dados**: filtro
automático de leitura + escrita automática do tenant + autorização por objeto que checa a
empresa. Este é o controle mais crítico de todo o projeto (LGPD/saúde).

## Descrição
Como **encarregado de dados**, quero garantir que uma empresa jamais leia ou grave dados de
outra, mesmo diante de erro de programação numa rota específica.

## Critérios de Aceite
- [ ] Contexto de tenant por requisição: `before_request` resolve a empresa do usuário logado
  em `flask.g.empresa_id` (Super-Admin fica sem tenant).
- [ ] **Filtro automático de leitura:** `TenantMixin` + evento SQLAlchemy injeta
  `WHERE empresa_id = g.empresa_id` nas queries dos models com tenant.
- [ ] **Escrita automática:** todo registro novo de model com tenant recebe
  `empresa_id = g.empresa_id` automaticamente (nunca a partir de input do cliente).
- [ ] `autorizar_recurso()` passa a **negar (403)** acesso a objeto de outra empresa.
- [ ] Super-Admin **não** ganha acesso a dado de negócio por este caminho.
- [ ] **Testes de isolamento A↔B:** usuário da empresa A não lista, não lê por id, não baixa
  e não edita dado da empresa B (403/404), e não vaza em buscas/relatórios.
- [ ] Regressão: módulos existentes seguem funcionando dentro de uma empresa.

## Tarefas
1. `app/tenancy/` (ou `utils/tenant.py`): `TenantMixin`, resolução de `g.empresa_id`, event listeners de leitura/escrita.
2. Aplicar o mixin aos models raiz (herdam o comportamento).
3. Ajustar `utils/authz.autorizar_recurso` para checar `empresa_id` do objeto.
4. Tratar consultas legítimas cross-tenant do Super-Admin como caminho **explícito e separado** (sem filtro), nunca em rotas de negócio.
5. Testes dedicados de isolamento (`tests/test_isolamento_tenant.py`) — leitura, escrita, download, busca, relatório.
6. Revisão do @si sobre o mecanismo de isolamento.

## Notas
- Avaliar `unscoped()` explícito só para caminhos administrativos controlados (migração/seed).
- Cuidado com queries que rodam **fora** de request (CLI/seed): quando não há `g.empresa_id`,
  o mixin não deve filtrar silenciosamente errado — definir política (ex.: exigir escopo explícito).
- Este é o ponto de maior risco; priorizar cobertura de teste e revisão de segurança.
