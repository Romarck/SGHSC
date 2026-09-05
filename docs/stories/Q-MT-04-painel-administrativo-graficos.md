# Story Q-MT-04 — Painel administrativo do Super-Admin (indicadores + gráficos)

**Épico:** SAAS Multi-tenant (FR-MT-05)
**Prioridade:** P1
**Status:** A fazer
**Origem:** `docs/plano-quiron-multitenant.md` (Fase MT-4), PRD v2.0
**Branch:** `quiron`
**Depende de:** Q-MT-03

---

## Contexto
O Super-Admin precisa de visão gerencial da base de clientes para acompanhar vendas, uso e
saúde comercial do SAAS — **sem** acessar conteúdo clínico das empresas (apenas metadados agregados).

## Descrição
Como **Super-Admin**, quero um dashboard com indicadores e gráficos das empresas cadastradas,
para acompanhar crescimento, distribuição por plano/status, vencimentos e uso agregado.

## Critérios de Aceite
- [ ] Dashboard em `/admin/dashboard` protegido por `@requer_super_admin`.
- [ ] Indicadores: nº de empresas por status (ativa/trial/suspensa/cancelada); por plano;
  MRR estimado por plano; empresas com assinatura próxima do vencimento.
- [ ] Métricas de uso **agregadas por empresa** (contagens, não conteúdo): usuários ativos,
  nº de pacientes, internações no período, volume de atendimentos.
- [ ] **Gráficos** com Chart.js (via CDN dentro da CSP da S-09): crescimento de empresas no
  tempo, distribuição por plano/status, uso comparado entre empresas.
- [ ] Filtro por período. Dados servidos por endpoint(s) JSON próprios do admin.
- [ ] Nenhum dado clínico individual é exposto (só números agregados).
- [ ] Testes: acesso só de Super-Admin; agregações corretas; ausência de dado clínico no payload.

## Tarefas
1. `services/saas_indicadores_service.py` — agregações entre empresas (contagens/uso), respeitando privacidade.
2. Rotas `/admin/dashboard` + endpoints JSON para os gráficos.
3. Templates `templates/admin/dashboard.html` + integração Chart.js (CDN já permitido na CSP).
4. Ajustar CSP se necessário (só para o domínio do Chart.js, mínimo necessário).
5. Testes (`tests/test_saas_dashboard.py`).

## Notas
- Reusar o padrão do `indicadores_service.py` existente (dashboard clínico intra-empresa).
- MRR é **estimado** a partir do plano (não integra gateway de pagamento — fora de escopo).
