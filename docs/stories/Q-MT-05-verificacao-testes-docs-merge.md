# Story Q-MT-05 — Verificação final, testes de isolamento, documentação e merge

**Épico:** SAAS Multi-tenant + Segurança (encerramento)
**Prioridade:** P0 — porta de saída antes do merge na `main`
**Status:** A fazer
**Origem:** `docs/plano-quiron-multitenant.md` (Fases MT-5/MT-6), PRD v2.0
**Branch:** `quiron`
**Depende de:** todas as Q-MT-* e Q-SEC-*

---

## Contexto
Antes de levar o QUÍRON para a `main`, é preciso consolidar a verificação: isolamento entre
tenants sem vazamento, controles ISO no lugar, documentação atualizada e CI verde. O merge
só acontece após sua validação.

## Descrição
Como **product owner**, quero uma verificação de fechamento que comprove isolamento,
segurança e ausência de regressão, para aprovar o merge na `main` com confiança.

## Critérios de Aceite
- [ ] Suíte completa passa, incluindo os testes de **isolamento de tenant** (A↔B) e de **segurança**
  (2FA, auditoria de eventos, criptografia de coluna).
- [ ] CI verde com as novas etapas de DevSecOps (bandit, gitleaks, pip-audit).
- [ ] Revisão do **@si** sobre isolamento de tenant e controles ISO (P0) sem achados abertos.
- [ ] Documentação atualizada: `PROJECT_STATE.md`, `architecture.md`, `datamodel.md`,
  `GUIA_DE_USO.md` (Super-Admin, empresas, 2FA), `iso27001-gap-analysis.md` (status),
  `docs/security/iso27001-controles.md` (matriz).
- [ ] `ADR-007` (modelo de multi-tenancy) registrado em `docs/decisions/`.
- [ ] Migração da Pedralva validada (0 órfãos) e procedimento de deploy/backup revisado.
- [ ] **Merge da `quiron` na `main`** somente após aprovação explícita do cliente.

## Tarefas
1. Rodar suíte completa + cobertura; garantir testes de isolamento e segurança.
2. Rodar/estabilizar o CI com todas as etapas.
3. Solicitar reauditoria do @si (isolamento + ISO P0).
4. Atualizar toda a documentação e a matriz de controles ISO.
5. Registrar ADR-007.
6. Abrir PR `quiron → main`; após aprovação do cliente, fazer o merge.

## Notas
- Não fazer merge sem o aval explícito do cliente (requisito do item 7 do pedido original).
- Pendências que dependem de infra da VPS (LUKS, SSH, WAF, agendador de backup) ficam
  documentadas como passo de deploy, não bloqueiam o merge do código se os controles de
  aplicação estiverem entregues e testados.
