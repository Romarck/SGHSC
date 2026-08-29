# SGHSC — Sistema de Gestão Hospitalar para Santas Casas

Sistema de gestão hospitalar completo desenvolvido para a **Santa Casa de Misericórdia de Pedralva - MG**.
Construído com Python/Flask, PostgreSQL e Docker, com suporte a certificação digital ICP-Brasil para
validade jurídica dos documentos do Prontuário Eletrônico do Paciente (PEP).

---

## Stack Tecnológica

| Camada       | Tecnologia                              |
|-------------|----------------------------------------|
| Backend      | Python 3.12 + Flask 3.1               |
| ORM          | SQLAlchemy + Flask-Migrate (Alembic)   |
| Banco        | PostgreSQL 16                          |
| Frontend     | Jinja2 + HTMX + Bootstrap 5           |
| Servidor web | Nginx 1.25                             |
| Containers   | Docker + Docker Compose               |
| Assinatura   | Certificação digital ICP-Brasil        |

---

## Pré-requisitos

- Docker >= 24.x
- Docker Compose >= 2.x
- Git

---

## Setup local (desenvolvimento)

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/sghsc.git
cd sghsc
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` e preencha:
- `SECRET_KEY` — gere com `python -c "import secrets; print(secrets.token_hex(32))"`
- `POSTGRES_PASSWORD` — senha do banco
- `INSTITUICAO_CNES` — número CNES da unidade
- `INSTITUICAO_CNPJ` — CNPJ da Santa Casa

> **Produção (`FLASK_ENV=production`):** a aplicação **valida a configuração no boot**
> e **se recusa a subir** se `SECRET_KEY`, `DATABASE_URL` ou `POSTGRES_PASSWORD`
> estiverem ausentes, ou se `SECRET_KEY` ainda for o valor default/placeholder.
> Sempre gere uma `SECRET_KEY` forte antes de ir para produção.

### 3. Suba os containers

```bash
docker compose up --build
```

O entrypoint faz automaticamente:
- Aguarda o PostgreSQL iniciar
- Aplica as migrações de banco (`flask db upgrade`)
- Cria o usuário administrador padrão

### 4. Acesse o sistema

| URL                      | Serviço        |
|--------------------------|----------------|
| http://localhost         | App via Nginx  |
| http://localhost:5050    | Flask direto   |
| localhost:5444           | PostgreSQL     |

> As portas externas 5050 (Flask) e 5444 (PostgreSQL) foram escolhidas para
> evitar conflito com outros projetos no ambiente de desenvolvimento local.

**Login inicial:**
- Usuário: `admin`
- Senha: `Admin@123` *(o sistema obriga a troca no primeiro acesso)*

### 5. Como usar

Para o passo a passo de cada funcionalidade, consulte o
**[Guia de Uso](docs/GUIA_DE_USO.md)** — cobre todos os módulos, do cadastro de
paciente à assinatura digital de documentos.

---

## Migrações de banco

O boot separa **geração** (dev) de **aplicação** (produção) — ver
**[docs/migracao-producao.md](docs/migracao-producao.md)** para o procedimento completo.

- **Produção** (`FLASK_ENV=production`): o boot roda **apenas `flask db upgrade`**
  (aplica revisões já commitadas). Falha no upgrade **aborta o boot** (não sobe com
  schema inconsistente). **Faça backup do banco antes de cada deploy.**
- **Desenvolvimento:** o boot autogera (`flask db migrate`) e aplica por conveniência.

Após alterar modelos em dev, gere/revise/commite a migração:

```bash
docker compose exec app flask db migrate -m "descrição da mudança"
# revise o arquivo em backend/migrations/versions/ e commite
docker compose exec app flask db upgrade
```

---

## Comandos úteis

```bash
# Ver logs da aplicação
docker compose logs -f app

# Acessar shell do container
docker compose exec app bash

# Criar nova migração após alterar modelos
docker compose exec app flask db migrate -m "Descrição da mudança"
docker compose exec app flask db upgrade

# Parar tudo
docker compose down

# Parar e remover volumes (APAGA O BANCO)
docker compose down -v
```

---

## Testes e CI

A suíte roda com `TestingConfig` (SQLite em memória, CSRF desabilitado) e cobre os
fluxos críticos: autenticação, RBAC (S-01), IDOR (S-02), validação de produção
(S-04), endurecimento de auth (S-06), auditoria LGPD (S-07) e um fluxo clínico
ponta a ponta (admissão → prescrição → prontuário → alta).

```bash
# Rodar a suíte completa (dentro do container)
docker compose exec app pytest

# Com cobertura
docker compose exec app pytest --cov=app --cov-report=term-missing

# Lint (ruff)
docker compose exec app ruff check .

# Auditoria de dependências (CVEs conhecidos)
docker compose exec app pip-audit
```

Sem o container, a partir de `backend/` num ambiente com as dependências instaladas:

```bash
pytest -q
ruff check .
```

### CI (GitHub Actions)

O workflow `.github/workflows/ci.yml` roda a cada push/PR e **falha o build** se
qualquer etapa falhar:

1. **Lint** — `ruff check .`
2. **Migração** — `flask db upgrade` contra um PostgreSQL efêmero.
3. **Testes** — `pytest` com cobertura.
4. **Auditoria de dependências** — `pip-audit` (apoia a S-05).

---

## Estrutura do projeto

```
sghsc/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App factory Flask
│   │   ├── config.py            # Configurações por ambiente
│   │   ├── extensions.py        # Extensões (db, login, bcrypt...)
│   │   ├── models/              # Modelos SQLAlchemy (um arquivo por módulo)
│   │   ├── routes/              # Blueprints (um por módulo)
│   │   ├── services/            # Lógica de negócio (PDF, assinatura, indicadores)
│   │   ├── templates/           # Templates Jinja2 (um diretório por módulo)
│   │   └── static/              # CSS, JS, imagens
│   ├── migrations/              # Alembic migrations
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── wsgi.py
│   └── entrypoint.sh
├── nginx/
│   └── nginx.conf
├── docs/
│   ├── PROJECT_STATE.md         # Estado técnico detalhado do projeto
│   └── GUIA_DE_USO.md           # Guia passo a passo de uso
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Módulos do sistema (roadmap)

As 6 fases planejadas estão implementadas. Veja o detalhamento técnico em
[`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) e o passo a passo de uso em
[`docs/GUIA_DE_USO.md`](docs/GUIA_DE_USO.md).

### Fase 1 — Base ✅
- [x] Autenticação (login, logout, troca de senha obrigatória, bloqueio após 5 tentativas)
- [x] Controle de acesso por perfis (RBAC)
- [x] Estrutura base Docker + Flask + PostgreSQL

### Fase 2 — Porta de entrada ✅
- [x] Cadastro de pacientes (busca em tempo real, ViaCEP)
- [x] Pronto-Atendimento / Emergência + Triagem Manchester
- [x] Ambulatório (agenda + atendimento)

### Fase 3 — Internação ✅
- [x] Gestão de leitos (mapa visual)
- [x] Internação (admissão, transferência, alta com laudo PDF)
- [x] Prescrição médica
- [x] Prescrição e evolução de enfermagem
- [x] Controles do paciente (sinais vitais, balanço hídrico)

### Fase 4 — Apoio clínico ✅
- [x] Exames (solicitação, coleta, laudo)
- [x] Farmácia (dispensação por prescrição, controle de estoque)
- [x] Nutrição (mapa de dietas)
- [x] Maternidade / Perinatal (pré-natal, parto, recém-nascido)
- [x] Cirurgias (solicitação, escala, centro cirúrgico, descrição)
- [x] Certificação digital ICP-Brasil (assinatura de documentos + QR de validação)
- [x] Controle de infecção (CCIH)

### Fase 5 — Administrativo ✅
- [x] Faturamento SUS (AIH, APAC, BPA — estrutura; export DATASUS pendente*)
- [x] Faturamento convênios (CBHPM/TUSS, guias TISS)
- [x] Estoque (materiais e medicamentos, requisições, inventário)
- [x] Compras e fornecedores (recebimento alimenta o estoque)
- [x] Financeiro (contas a pagar/receber, fluxo de caixa)
- [x] Patrimônio e inventário (com depreciação)
- [x] Recursos Humanos (funcionários, escalas de plantão)
- [x] Ordens de manutenção (corretiva e preventiva)

### Fase 6 — Gestão e compliance ✅
- [x] Dashboard gerencial (ocupação, giro de leitos, produção)
- [x] Gestão de resíduos (PGRSS)
- [x] Integração RNDS (payload FHIR R4; transmissão pendente*)

\* *Pendências que dependem de credenciais/tabelas externas: certificado ICP-Brasil
real, exportação DATASUS no layout magnético oficial e transmissão à RNDS. A estrutura
de código está pronta; ver detalhes em `docs/PROJECT_STATE.md`.*

---

## Certificação digital (ICP-Brasil)

Documentos que exigem assinatura digital do profissional de saúde (prescrições,
evoluções, laudos) são assinados com certificado digital A1/A3 emitido por Autoridade
Certificadora credenciada pela ICP-Brasil. Isso garante:

- Autenticidade e integridade do documento (assinatura PAdES + carimbo de tempo)
- Validade jurídica (equivalente à assinatura manuscrita — MP 2.200-2/2001)
- Eliminação da impressão para arquivo físico
- Validação pública via QR Code impresso no documento

**Em desenvolvimento**, o sistema gera um certificado de teste autoassinado para
validar o fluxo de assinatura (menu Apoio Clínico → Certificação Digital → "Gerar
certificado de teste"). Para produção, recomenda-se um **certificado A1 e-CNPJ**
(instruções de aquisição em `docs/PROJECT_STATE.md`).

---

## Licença

Projeto privado — Santa Casa de Misericórdia de Pedralva.
Desenvolvido com intenção de tornar-se template para outras Santas Casas.
