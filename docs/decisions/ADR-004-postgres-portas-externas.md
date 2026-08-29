# ADR-004 — PostgreSQL 16 e portas externas customizadas (5050/5444)

**Status:** Aceito (retroativo)
**Data:** 2026-08-28
**Autor:** @architect
**Contexto de origem:** decisão implícita promovida a ADR durante o `*audit`

---

## Contexto

O sistema precisa de um banco relacional robusto para dados clínicos e administrativos,
com integridade transacional e suporte a migrações. O ambiente de desenvolvimento local
já roda outros projetos que ocupam as portas padrão (5432/5433 do PostgreSQL e 5000 do
Flask).

## Decisão

- **Banco:** **PostgreSQL 16** (imagem `postgres:16-alpine`), com volume persistente
  `pgdata`. ORM SQLAlchemy 2 + Flask-Migrate (Alembic) para o schema.
- **Portas externas customizadas** no `docker-compose.yml` para evitar conflito no dev
  local:
  - PostgreSQL: **5444** externa → 5432 interna
  - Flask/app: **5050** externa → 5000 interna
  - Nginx: 80 (e 443 preparado para produção)
- Pool com `pool_pre_ping=True` e `pool_recycle=300` para resiliência de conexão.

## Consequências

**Positivas**
- Integridade transacional, tipos ricos (Numeric, Enum nativo, Date/Time com timezone).
- Sem conflito de portas com outros projetos no ambiente de desenvolvimento.
- Migrações versionadas (7 revisões Alembic) reproduzíveis.

**Negativas / trade-offs**
- Portas não padrão exigem atenção na documentação e no onboarding.
- Enum nativo do PostgreSQL torna alterações de membros de Enum mais custosas (exigem
  migração cuidadosa) — ver observação no `datamodel.md`.
- O mapeamento de portas externas é uma conveniência de dev; em produção o acesso ao
  banco não deve ser exposto.

## Alternativas consideradas

- **MySQL/MariaDB:** viável, mas PostgreSQL oferece Enum nativo, melhor suporte a tipos e
  é o padrão adotado no `config.yaml` do projeto.
- **SQLite:** usado apenas em `TestingConfig` (in-memory). Inadequado para produção
  multiusuário.
- **Portas padrão (5432/5000):** causariam conflito com outros serviços locais.

## Referências
- `docker-compose.yml`, `app/config.py` (`SQLALCHEMY_ENGINE_OPTIONS`)
- `backend/migrations/versions/` (7 revisões)
