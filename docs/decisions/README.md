# Registros de Decisão de Arquitetura (ADRs) — SGHSC

Este diretório contém os **Architecture Decision Records** do SGHSC: decisões técnicas
significativas, seu contexto, consequências e alternativas consideradas.

Os ADRs abaixo foram **promovidos retroativamente** a partir de decisões implícitas no
código, identificadas durante o `@architect *audit` (ver `docs/architecture.md`,
seção 4). Novas decisões devem seguir o mesmo formato.

## Índice

| ADR | Título | Status |
|-----|--------|--------|
| [ADR-001](ADR-001-frontend-jinja2-htmx.md) | Frontend server-side com Jinja2 + HTMX (sem SPA) | Aceito |
| [ADR-002](ADR-002-assinatura-pyhanko-a1.md) | Assinatura digital via pyHanko com certificado A1 no servidor | Aceito |
| [ADR-003](ADR-003-monolito-flask-blueprints.md) | Arquitetura monólito Flask com blueprints por módulo | Aceito |
| [ADR-004](ADR-004-postgres-portas-externas.md) | PostgreSQL 16 e portas externas customizadas (5050/5444) | Aceito |
| [ADR-005](ADR-005-auth-sessao-rbac.md) | Autenticação por sessão (Flask-Login) e autorização RBAC | Aceito (com pendência) |
| [ADR-006](ADR-006-validacao-publica-hash-qrcode.md) | Validação pública de documentos via hash SHA-256 + QR Code | Aceito |

## Convenção

- **Arquivo:** `ADR-NNN-slug.md` (numeração sequencial, três dígitos).
- **Status:** `Proposto` → `Aceito` → `Substituído por ADR-XXX` / `Depreciado`.
- **Estrutura:** Contexto · Decisão · Consequências (positivas/negativas) ·
  Alternativas consideradas · Referências.
- Autoridade sobre decisões técnicas: `@architect` (ver `.kiro/constitution.md`, Artigo II).

## Como criar um novo ADR

1. Copie a estrutura de um ADR existente.
2. Use o próximo número sequencial.
3. Registre o **contexto** (por que a decisão foi necessária) antes da **decisão**.
4. Liste **alternativas** e o motivo de terem sido descartadas.
5. Referencie no `docs/architecture.md` (seção 4).

---

*PDA-SQUAD v1.0.0 — decisões sob autoridade do `@architect`*
