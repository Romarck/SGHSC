# Arquitetura: SGHSC — Auditoria do Codebase

**Data:** 2026-08-28
**Autor:** @architect
**Comando:** `*audit`
**Stack real (auditada):** Python 3.12 / Flask 3.1 + Jinja2/HTMX/Bootstrap 5 + PostgreSQL 16

> Este documento foi preenchido a partir de uma **auditoria do código-fonte real**, não do
> template. Onde o código diverge da documentação existente (`config.yaml`, `PROJECT_STATE.md`),
> o fato observado no código prevalece e a divergência está registrada na seção 8.

---

## 1. Visão Geral

O SGHSC é um **monólito web server-side** em Flask que cobre o ciclo hospitalar completo de uma
Santa Casa: porta de entrada (pacientes, emergência, ambulatório), internação, apoio clínico
(exames, farmácia, nutrição, CCIH, cirurgias, maternidade, certificação digital), administrativo
(estoque, compras, financeiro, faturamento SUS, convênios, patrimônio, RH, manutenção) e
gestão/compliance (indicadores, PGRSS, RNDS).

A renderização é **server-side (Jinja2)** com interatividade via **HTMX** — não há SPA nem build
de frontend. A aplicação segue o padrão **Application Factory** (`create_app`) com **blueprints**
por módulo.

### Números da auditoria (verificados)

| Item | Quantidade |
|------|-----------|
| Módulos de models (`app/models/*.py`) | 24 |
| Módulos de rotas / blueprints (`app/routes/*.py`) | 25 (24 registrados + `__init__`) |
| Diretórios de templates | 27 |
| Templates `.html` | 110 |
| Migrações Alembic | 7 |
| Decoradores `@bp.route` | ~140 |
| Decoradores `@login_required` | ~130 |
| Chamadas de `tem_permissao` em rotas | **0** |
| Testes automatizados | **0** (diretório `backend/tests/` vazio) |

### Diagrama de Componentes (real)

```
┌───────────────────────────────────────────────┐
│                 Navegador                       │
│         (HTML + HTMX + Bootstrap 5)             │
└───────────────────────┬─────────────────────────┘
                        │ HTTP (80) / HTTPS (443, comentado)
┌───────────────────────▼─────────────────────────┐
│              Nginx 1.25 (reverse proxy)          │
│   - serve /static/ direto                        │
│   - proxy_pass → app:5000                        │
│   - server_tokens off; bloco HTTPS/HSTS pronto   │
│     porém comentado                              │
└───────────────────────┬─────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────┐
│        Flask (Gunicorn em prod / dev server)     │
│  create_app()                                    │
│  ┌───────────┐ ┌───────────┐ ┌────────────────┐ │
│  │  auth      │ │ 24 blueprints por módulo     │ │
│  │  (session) │ │ (pacientes, internacao, ...) │ │
│  └───────────┘ └──────────────────────────────┘ │
│  extensões: SQLAlchemy · Migrate · Login ·       │
│             Bcrypt · CSRFProtect                 │
│  services: pdf_service · cert_service ·          │
│            indicadores_service                   │
└───────────────────────┬─────────────────────────┘
                        │ SQLAlchemy 2 / psycopg2
┌───────────────────────▼─────────────────────────┐
│              PostgreSQL 16 (container)            │
│              volume pgdata (persistente)          │
└───────────────────────────────────────────────┘
```

---

## 2. Stack Tecnológico (auditado)

| Camada | Tecnologia | Versão | Observação |
|--------|-----------|--------|------------|
| Frontend | Jinja2 + HTMX + Bootstrap 5 | — | Server-side, sem build step |
| Backend | Python + Flask | 3.12 / 3.1.1 | Application Factory + blueprints |
| ORM | SQLAlchemy + Flask-SQLAlchemy | 2.0.41 / 3.1.1 | `pool_pre_ping`, `pool_recycle=300` |
| Migrações | Flask-Migrate (Alembic) | 4.1.0 / 1.16.1 | 7 revisões versionadas |
| Banco de Dados | PostgreSQL | 16-alpine | Porta externa 5444 |
| Autenticação | Flask-Login (sessão) | 0.6.3 | `session_protection="strong"` |
| Hash de senha | Flask-Bcrypt | 1.0.1 | via property `senha` no model |
| CSRF | Flask-WTF (CSRFProtect) | 1.2.2 | global, exceto `TestingConfig` |
| Assinatura digital | pyHanko + cryptography | 0.25.1 / 43.0.3 | PAdES / ICP-Brasil |
| PDF | ReportLab | 4.2.5 | laudos, prescrições, evoluções |
| QR Code | qrcode | 8.0 | validação pública de documentos |
| Servidor WSGI | Gunicorn | 23.0.0 | 2 workers × 2 threads em prod |
| Proxy | Nginx | 1.25-alpine | HTTPS pronto porém comentado |
| Containers | Docker + Docker Compose | — | 3 serviços: db, app, nginx |

**Dependências declaradas mas não usadas (candidatas a remoção):**
- `Flask-CORS` — nenhuma inicialização `CORS(...)` encontrada no código.
- `marshmallow` / `Flask-Marshmallow` / `marshmallow-sqlalchemy` — diretório `app/schemas/`
  está vazio; validação hoje é feita via Flask-WTF (formulários), não schemas.

---

## 3. Padrões e Convenções (observados no código)

### Camadas
- **REST parcial + páginas server-side.** A maioria das rotas retorna HTML (full page ou
  fragmento HTMX). Há endpoints JSON pontuais (ex.: contadores do dashboard).
- **Sem versionamento de API** (`/api/v1` não existe) — coerente com app server-side.

### Código
- **Idioma:** Português para models, rotas, templates e comentários.
- **Estrutura por módulo:** cada módulo tem `models/<x>.py`, `routes/<x>.py` (Blueprint) e
  `templates/<x>/`. Blueprint registrado em `app/__init__.py::_register_blueprints`.
- **Enumerações:** `enum.Enum` do Python mapeado com `db.Enum(...)` (ex.: `TipoPerfil`,
  `StatusUsuario`).
- **Auditoria de dados:** convenção de `criado_em`, `atualizado_em`, `criado_por_id` nos models.
- **Numeração de documentos:** padrão `PREFIXOAAAAMMDDNNNN` / `ANO-NNNNNN`.

### Segurança de sessão (config)
- Cookie `HTTPOnly` sempre; `Secure` e `SameSite=Strict` apenas em `ProductionConfig`.
- Sessão de 8h (turno hospitalar). CSRF global via `flask_wtf`.
- Bloqueio de conta após 5 tentativas de login por 30 min (`Usuario.registrar_tentativa_falha`).
- `ProductionConfig.validate()` exige `SECRET_KEY`, `DATABASE_URL`, `POSTGRES_PASSWORD`.

---

## 4. Decisões Técnicas

As decisões implícitas no código foram **promovidas a ADRs** em `docs/decisions/`
(ver [índice](decisions/README.md)):

| ADR | Decisão | Motivo (conforme código/docs) |
|-----|---------|-------------------------------|
| [ADR-001](decisions/ADR-001-frontend-jinja2-htmx.md) | Frontend Jinja2 + HTMX (sem SPA) | Sem build step; interatividade sem JS pesado |
| [ADR-002](decisions/ADR-002-assinatura-pyhanko-a1.md) | Assinatura via pyHanko (A1 no servidor) | Pure Python, PAdES/ICP-Brasil, sem token físico |
| [ADR-003](decisions/ADR-003-monolito-flask-blueprints.md) | Monólito Flask com blueprints por módulo | Simplicidade operacional para unidade única |
| [ADR-004](decisions/ADR-004-postgres-portas-externas.md) | PostgreSQL 16 + portas externas 5050/5444 | Evitar conflito no ambiente de dev local |
| [ADR-005](decisions/ADR-005-auth-sessao-rbac.md) | Autenticação por sessão + RBAC Perfil/Permissão | Casa com UI server-side; RBAC granular (aplicação pendente — S1) |
| [ADR-006](decisions/ADR-006-validacao-publica-hash-qrcode.md) | Validação pública via hash SHA-256 + QR | Conferência de autenticidade sem login |

---

## 5. Segurança (achados da auditoria)

### Pontos fortes
- Autenticação de sessão aplicada de forma abrangente: **~130 `@login_required`** cobrindo
  praticamente todas as rotas protegidas.
- A rota **pública** de validação de documento (`/certificado/validar/<codigo>`) corretamente
  **não** exige login — é o destino do QR Code.
- Senhas com Bcrypt; CSRF global; bloqueio por tentativas; cabeçalho de versão do Nginx oculto.

### Achados prioritários

| # | Severidade | Achado | Evidência | Recomendação |
|---|-----------|--------|-----------|--------------|
| S1 | **ALTA** | **RBAC não é aplicado.** O model `Perfil/Permissao/tem_permissao` existe, mas `tem_permissao` **nunca é chamado em nenhuma rota**. Qualquer usuário autenticado acessa qualquer módulo. | 0 ocorrências de `tem_permissao` em `app/routes/` | Criar decorator `@requer_permissao("modulo.acao")` e aplicar nas rotas sensíveis (prescrição, alta, faturamento, financeiro, RH). |
| S2 | **ALTA** | **`SECRET_KEY` com fallback fraco** hardcoded (`"troque-antes-de-produção"`). Em prod há `validate()`, mas ele **não é chamado** em `create_app`. | `config.py` + `__init__.py` | Invocar `ProductionConfig.validate()` no factory quando `FLASK_ENV=production`. |
| S3 | **ALTA** | **HTTPS/HSTS desativado.** O bloco TLS no `nginx.conf` está comentado; dados de saúde trafegariam em HTTP. | `nginx/nginx.conf` | Ativar 443 + redirect 80→443 + HSTS antes de produção. |
| S4 | MÉDIA | **`deve_trocar_senha` não é forçado globalmente.** Só é checado no login; um usuário com sessão ativa e a flag ligada não é redirecionado. | `auth.py` | `before_request` global que redireciona para troca de senha enquanto a flag estiver ativa. |
| S5 | MÉDIA | **Admin seed com senha fixa** (`Admin@123`) criado pelo `entrypoint.sh`. | `entrypoint.sh` | Aceitável para bootstrap (com `deve_trocar_senha=True`), mas documentar/forçar troca e evitar em ambientes expostos. |
| S6 | BAIXA | **Dependências não usadas** (`Flask-CORS`, `marshmallow`) aumentam superfície. | `requirements.txt` vs código | Remover ou passar a usar. |
| S7 | INFO | Validação da **cadeia ICP-Brasil** (`trust_roots`) não ativada — só integridade. | `PROJECT_STATE.md` / `cert_service` | Ativar com ACs raiz quando houver certificado real. |

> **Nota de governança:** conforme a Constituição PDA-SQUAD, achados de vulnerabilidade e
> compliance são autoridade do `@si`. Este audit os **sinaliza**; a auditoria formal de segurança
> (`@si *audit-code`) e o veto de pré-produção continuam com o `@si`.

---

## 6. Modelo de Dados (visão macro)

O detalhamento fica em `docs/datamodel.md` (a criar via `@architect *datamodel`). Panorama:

- **Núcleo de acesso:** `Usuario`, `Perfil`, `Permissao` (+ tabela associativa `perfil_permissao`) — RBAC.
- **Clínico:** `Paciente`, `Prontuario`/`EntradaProntuario`, `AtendimentoEmergencia`/`TriagemManchester`,
  `AgendaAmbulatorio`/`ConsultaAmbulatorial`, cadeia de `Internacao` (`Leito`, `PrescricaoMedica`,
  `ControlesPaciente`, `Evolucao*`).
- **Apoio clínico:** exames, farmácia (lote/FEFO), nutrição, CCIH, cirurgias, maternidade,
  certificado digital.
- **Administrativo:** estoque, compras, financeiro, faturamento SUS (AIH/APAC/BPA), convênios
  (TISS/CBHPM), patrimônio, RH, manutenção.
- **Compliance:** resíduos (PGRSS), RNDS (FHIR R4).

Convenção transversal de auditoria (`criado_em`/`atualizado_em`/`criado_por_id`) presente nos
models principais.

---

## 7. Deploy e Infraestrutura (auditado)

### Ambientes
| Ambiente | Como sobe | Servidor de app |
|----------|-----------|-----------------|
| Development | `docker compose up -d` | Flask dev server (`--debug`) |
| Testing | `TestingConfig` (SQLite in-memory, CSRF off) | pytest (sem testes escritos ainda) |
| Production | `FLASK_ENV=production` | Gunicorn (2 workers × 2 threads, timeout 120s) |

### Fluxo de inicialização (`entrypoint.sh`)
1. Aguarda o PostgreSQL responder.
2. `flask db init` (se necessário) → `flask db migrate` → `flask db upgrade`.
3. Cria perfil e usuário `admin` padrão se não existirem.
4. Inicia Gunicorn (prod) ou Flask dev server (dev).

> ⚠️ **Risco operacional:** rodar `flask db migrate` no boot pode gerar migrações automáticas
> não revisadas em produção. Recomenda-se **apenas `flask db upgrade`** no boot de produção e
> gerar migrações manualmente no fluxo de desenvolvimento.

### CI/CD
**Inexistente.** Não há `.github/workflows`. Sem pipeline de lint, testes ou build automatizado.

---

## 8. Divergências entre documentação e código

| Fonte | Diz | Realidade no código |
|-------|-----|---------------------|
| `.pda-squad/config.yaml` | `backend: "Outro"`, `frontend: "Outro"` | Backend = Flask/Python; Frontend = Jinja2/HTMX |
| `docs/architecture.md` (antes deste audit) | Template em branco | Preenchido por esta auditoria |
| `docs/prd.md` | Template em branco (placeholders) | Produto já implementado nas 6 fases |
| `docs/stories/` | Vazio (`.gitkeep`) | Código existe sem stories — viola Artigo I da Constituição |
| RBAC (`tem_permissao`) | Descrito como ativo em `PROJECT_STATE.md` | Nunca invocado nas rotas (só autenticação) |

---

## 9. Recomendações priorizadas (backlog de arquitetura)

**P0 — antes de qualquer produção**
1. Ativar HTTPS/HSTS no Nginx (S3).
2. Chamar `ProductionConfig.validate()` no factory e falhar rápido sem segredos (S2).
3. Implementar e aplicar autorização RBAC (`@requer_permissao`) nas rotas sensíveis (S1).

**P1 — qualidade e governança**
4. Escrever a suíte de testes (`backend/tests/` está vazio); começar por auth, RBAC e fluxos
   clínicos críticos (prescrição, alta, dispensação).
5. Adicionar CI (GitHub Actions): lint + pytest + `flask db upgrade` em banco efêmero.
6. Trocar o boot para `flask db upgrade` apenas (sem `migrate` automático) em produção.
7. Forçar `deve_trocar_senha` via `before_request` global (S4).

**P2 — higiene**
8. Preencher `docs/prd.md` (via `@po`) e criar stories retroativas para rastreabilidade.
9. Promover decisões implícitas a ADRs em `docs/decisions/`.
10. Remover dependências não usadas (`Flask-CORS`, `marshmallow`) ou passar a usá-las (S6).
11. Gerar `docs/datamodel.md` com `@architect *datamodel`.

---

## 10. Histórico de Mudanças

| Data | Mudança | Autor |
|------|---------|-------|
| 2026-08-28 | Versão inicial (template) | @architect |
| 2026-08-28 | Auditoria do codebase — documento preenchido com arquitetura real e achados | @architect (`*audit`) |
| 2026-08-28 | Decisões implícitas promovidas a ADRs em `docs/decisions/` (ADR-001 a ADR-006) | @architect |

---

*Gerado pelo PDA-SQUAD v1.0.0 — comando `@architect *audit`*
