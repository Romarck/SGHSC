# ADR-003 — Arquitetura monólito Flask com blueprints por módulo

**Status:** Aceito (retroativo)
**Data:** 2026-08-28
**Autor:** @architect
**Contexto de origem:** decisão implícita promovida a ADR durante o `*audit`

---

## Contexto

O SGHSC atende **uma única instituição** (Santa Casa de Pedralva), com dezenas de
módulos funcionais (pacientes, emergência, internação, apoio clínico, administrativo,
compliance). É operado em rede local, com carga de acessos moderada e equipe de
desenvolvimento enxuta. Não há requisito de escala horizontal massiva nem de times
independentes por serviço.

## Decisão

Adotar um **monólito modular** em Flask usando o padrão **Application Factory**
(`create_app`) e **blueprints por módulo**.

- `app/__init__.py::_register_blueprints()` registra ~24 blueprints, cada um com seu
  `url_prefix` (`/pacientes`, `/internacao`, `/farmacia`, ...).
- Cada módulo segue a mesma estrutura: `models/<x>.py`, `routes/<x>.py`,
  `templates/<x>/`. Lógica transversal fica em `services/`.
- Extensões inicializadas sem app binding (`extensions.py`) e ligadas no factory:
  SQLAlchemy, Migrate, Login, Bcrypt, CSRFProtect.

## Consequências

**Positivas**
- Deploy único e simples (um container de app + db + nginx).
- Transações ACID diretas entre módulos (sem consistência distribuída).
- Estrutura previsível — o checklist de "novo módulo" é replicável.
- Baixo custo operacional, adequado ao porte da instituição.

**Negativas / trade-offs**
- Escala apenas verticalmente / por réplicas do processo inteiro.
- Acoplamento no banco compartilhado; mudanças de schema afetam todo o app.
- `app/__init__.py` cresce com o número de blueprints (aceitável; centralizado).

## Alternativas consideradas

- **Microsserviços:** desnecessário e caro para uma única unidade; adicionaria
  complexidade de rede, deploy e observabilidade sem benefício real.
- **Monólito sem blueprints (rotas planas):** dificultaria a organização por módulo e
  a atribuição de `url_prefix`.

## Referências
- `app/__init__.py`, `app/extensions.py`
- `docs/architecture.md` (seção 1 e diagrama de componentes)
