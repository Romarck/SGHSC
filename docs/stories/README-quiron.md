# Backlog QUÍRON — Stories de implementação (v2.0)

Índice das stories da evolução para **QUÍRON — SAAS Multi-tenant + adequação ISO 27001**.
Contexto em `docs/plano-quiron-multitenant.md`, `docs/prd.md` (v2.0) e `docs/iso27001-gap-analysis.md`.
Trabalho na branch `quiron`; merge na `main` só após conclusão e validação.

## Ordem sugerida de execução

| # | Story | Prioridade | Depende de |
|---|-------|-----------|-----------|
| 1 | [Q-MT-00](Q-MT-00-fundacao-empresa-rebranding.md) — Fundação: model Empresa, papéis, rebranding | P0 | — |
| 2 | [Q-SEC-01](Q-SEC-01-2fa-totp.md) — 2FA/TOTP (Super-Admin/Admin) | P0 | Q-MT-00 |
| 3 | [Q-MT-01](Q-MT-01-coluna-tenant-migracao-dados.md) — Coluna `empresa_id` + migração Pedralva | P0 | Q-MT-00 |
| 4 | [Q-MT-02](Q-MT-02-isolamento-automatico.md) — Isolamento automático de tenant | P0 | Q-MT-01 |
| 5 | [Q-SEC-02](Q-SEC-02-auditoria-eventos-trilha-inviolavel.md) — Auditoria de eventos + trilha inviolável | P0 | Q-MT-00 |
| 6 | [Q-SEC-03](Q-SEC-03-criptografia-em-repouso.md) — Criptografia em repouso (2 camadas) | P0 | — |
| 7 | [Q-MT-03](Q-MT-03-super-admin-crud-empresas.md) — Super-Admin + CRUD de empresas | P0 | Q-MT-02 |
| 8 | [Q-MT-04](Q-MT-04-painel-administrativo-graficos.md) — Painel admin do SAAS (gráficos) | P1 | Q-MT-03 |
| 9 | [Q-SEC-04](Q-SEC-04-backup-externo-dr.md) — Backup externo criptografado + DR | P0 | — |
| 10 | [Q-SEC-05](Q-SEC-05-dados-seguros-fora-de-producao.md) — Dados seguros fora de produção | P0 | — |
| 11 | [Q-SEC-06](Q-SEC-06-devsecops-ci.md) — DevSecOps no CI (SAST, secrets, bleach) | P1 | — |
| 12 | [Q-SEC-07](Q-SEC-07-hardening-infra-controles-iso.md) — Hardening de infra + matriz de controles ISO | P1 | — |
| 13 | [Q-MT-05](Q-MT-05-verificacao-testes-docs-merge.md) — Verificação, docs e merge na `main` | P0 | todas |

## Legenda
- **Q-MT-*** — trilha multi-tenant (SAAS).
- **Q-SEC-*** — trilha de segurança ISO 27001 (controles técnicos do Anexo A).
- **P0** bloqueia o go-live do SAAS; **P1** endurecimento; **P2** melhoria (registradas no gap analysis).

## Decisões do cliente incorporadas
- 2FA obrigatório **apenas** para Super-Admin e Administradores (perfis clínicos ficam opcionais).
- Criptografia em repouso em **duas camadas**: cifra de volume (LUKS, infra) + cifra de coluna (aplicação).
- Modelo de tenant: **coluna discriminadora `empresa_id`** (shared DB/schema) — ADR-007.
