# Plano de Implementação — QUÍRON (SAAS Multi-tenant)

**Data:** 2026-09-05
**Autor:** @po (proposto para aprovação)
**Status:** 🟡 AGUARDANDO APROVAÇÃO
**Branch de trabalho:** `quiron` (merge na `main` só após tudo concluído e validado)

> Transforma o SGHSC (produto de instância única, hoje dedicado à Santa Casa de
> Pedralva) no **QUÍRON — Inteligência Clínica, Segurança e Performance Hospitalar**,
> um SAAS **multi-tenant** que atende várias empresas (hospitais/Santas Casas) na
> mesma instalação, com **isolamento total de dados** por empresa.

---

## 1. Objetivo do trabalho

1. **Rebranding** do projeto para *QUÍRON — Inteligência Clínica, Segurança e Performance Hospitalar*.
2. **Super-Admin** (operador do SAAS): vende e cadastra novas empresas, gerencia o ciclo de vida delas.
3. **CRUD de Empresas (tenants)**, tendo a *Santa Casa de Pedralva* como a primeira empresa migrada.
4. **Isolamento de dados por empresa**: cada empresa vê e opera apenas os próprios dados.
5. **Painel administrativo do Super-Admin** com indicadores gerenciais e gráficos das empresas.

---

## 2. Decisão de arquitetura: modelo de multi-tenancy

Três abordagens possíveis para isolar tenants no PostgreSQL:

| Abordagem | Isolamento | Custo de refatoração | Operação |
|-----------|-----------|----------------------|----------|
| **A. Banco por tenant** | Máximo (bancos separados) | Alto (roteamento dinâmico de conexão) | Complexa (N bancos, N migrações) |
| **B. Schema por tenant** | Alto (schema PG por tenant) | Médio-alto (search_path dinâmico) | Média |
| **C. Coluna discriminadora (`empresa_id`)** | Lógico (uma coluna + filtro obrigatório) | Médio (coluna em todas as tabelas + filtro global) | Simples (1 banco, 1 migração) |

**Escolha: C — coluna discriminadora `empresa_id` (shared database, shared schema),
com isolamento reforçado por camada de aplicação.** Motivos:

- Casa com o monólito Flask atual (ADR-003) e com 1 único PostgreSQL/Docker Compose — sem reengenharia de infraestrutura.
- Refatoração previsível: adicionar `empresa_id` às tabelas de negócio e um **filtro global obrigatório** por tenant.
- Menor custo operacional (uma migração, um backup) — coerente com o público de baixo orçamento.
- **Mitigação do risco de isolamento** (o ponto fraco da abordagem C) com três camadas:
  1. **Filtro automático** de tenant nas queries (event listener/escopo de sessão), não confiando só no dev lembrar do `.filter()`.
  2. **`empresa_id` gravado automaticamente** na criação de qualquer registro (a partir do contexto do usuário logado).
  3. **Testes de isolamento** dedicados (empresa A não acessa dado da empresa B) na suíte.

> Esta decisão será registrada como **ADR-007** em `docs/decisions/`.

### Papéis de acesso (novo eixo, ortogonal ao RBAC atual)

O RBAC atual (Perfil/Permissão) continua **dentro** de cada empresa. Acrescentamos o
eixo de **escopo de tenant** ao `Usuario`:

- **SUPER_ADMIN** — opera o SAAS. **Não pertence a nenhuma empresa** (`empresa_id = NULL`).
  Acessa o painel administrativo e o CRUD de empresas. **Não acessa dados clínicos** de nenhuma empresa (privacidade/LGPD).
- **Usuário de empresa** — pertence a exatamente uma empresa (`empresa_id` obrigatório).
  Enxerga somente os dados da própria empresa. Mantém seu Perfil/permissões atuais.

---

## 3. Modelo de dados

### 3.1. Nova tabela `empresas` (tenant)

Model `Empresa` (`app/models/empresa.py`):

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `nome_fantasia` | str | Nome de exibição |
| `razao_social` | str | |
| `cnpj` | str, único | Identificador fiscal |
| `cnes` | str | Cadastro Nacional de Estabelecimentos de Saúde |
| `slug` | str, único | Identificador curto (ex.: `santa-casa-pedralva`) |
| `email_contato`, `telefone` | str | |
| endereço (cidade, uf, cep, logradouro...) | str | |
| `status` | Enum(`ATIVA`, `SUSPENSA`, `CANCELADA`, `TRIAL`) | Ciclo de vida comercial |
| `plano` | Enum(`BASICO`, `PROFISSIONAL`, `ENTERPRISE`) | Base para faturamento do SAAS |
| `data_contratacao`, `data_expiracao` | date | Controle de assinatura |
| `logo_path` | str | Personalização por empresa |
| `criado_em`, `atualizado_em`, `criado_por_id` | auditoria | |

### 3.2. `empresa_id` nas tabelas de negócio

Adicionar `empresa_id` (FK → `empresas.id`, indexado) às **tabelas raiz** de cada
agregado. Tabelas "filhas" (itens de guia, itens de prescrição, etc.) herdam o
tenant pela FK ao pai — não precisam da coluna, o que reduz a superfície.

**Tabelas raiz que recebem `empresa_id`** (aprox. 30–35 tabelas):
`usuarios`, `perfis`, `pacientes`, `prontuarios`, `atendimentos_emergencia`,
`agendas_ambulatorio`, `consultas_ambulatoriais`, `leitos`, `internacoes`,
`prescricoes_medicas`, `prescricoes_enfermagem`, `controles_paciente`,
`evolucoes_medicas`, `evolucoes_enfermagem`, `exames_catalogo`, `solicitacoes_exame`,
`medicamentos_farmacia`, `lotes_estoque`, `dispensacoes`, `prescricoes_dieteticas`,
`notificacoes_infeccao`, `isolamentos_paciente`, `salas_cirurgicas`, `cirurgias`,
`prenatais`, `partos`, `certificados_digitais`, `documentos_assinados`,
`locais_estoque`, `produtos_estoque`, `saldos_estoque`, `requisicoes_material`,
`inventarios`, `fornecedores`, `solicitacoes_compra`, `pedidos_compra`,
`categorias_financeiras`, `contas`, `lancamentos_caixa`, `procedimentos_sigtap`,
`guias_faturamento`, `convenios`, `guias_convenio`, `bens_patrimoniais`,
`setores`, `funcionarios`, `escalas_plantao`, `ordens_servico`,
`registros_residuo`, `registros_rnds`, `logs_acesso`.

**Tabelas globais (sem `empresa_id`)**: `permissoes` (catálogo compartilhado),
tabelas de catálogo puramente estáticas se houver. `procedimentos_sigtap`/`cbhpm`
serão avaliados — provavelmente por-empresa para permitir tabelas de preço distintas.

### 3.3. `Usuario`

- Novo campo `empresa_id` (FK → `empresas.id`, **nullable** — nulo = Super-Admin).
- Novo campo `is_super_admin` (bool) ou um `TipoPerfil.SUPER_ADMIN` — a definir na implementação;
  proposta: **flag `is_super_admin`** para manter o Super-Admin fora do RBAC intra-empresa.
- `username`/`email` deixam de ser globalmente únicos e passam a ser **únicos por empresa**
  (constraint composta `(empresa_id, username)`), permitindo `admin` em cada empresa.

---

## 4. Isolamento de dados (o coração do multi-tenant)

### 4.1. Contexto de tenant por requisição
- `before_request` resolve a empresa do usuário logado e a guarda em `flask.g.empresa_id`.
- Super-Admin não tem `empresa_id`; suas rotas ficam num blueprint próprio que **não** consulta dados clínicos.

### 4.2. Filtro automático nas queries
- Um **mixin `TenantMixin`** + evento SQLAlchemy que injeta `WHERE empresa_id = :tenant`
  automaticamente nas consultas dos models com tenant, usando `g.empresa_id`.
- Alternativa/complemento: `Query` customizada no `db.session` que aplica o filtro. A
  implementação exata será validada com um teste de isolamento antes de propagar.

### 4.3. Escrita automática do tenant
- No `before_flush`/construtor do mixin, todo registro novo recebe `empresa_id = g.empresa_id`
  automaticamente — o desenvolvedor não precisa (e não deve) setar manualmente.

### 4.4. Autorização reforçada
- `autorizar_recurso()` (já existe, anti-IDOR) passa a checar também `empresa_id` do objeto.
- Super-Admin **não** ganha acesso a dados de empresa por aqui — separação explícita.

---

## 5. Super-Admin e Painel Administrativo

### 5.1. Super-Admin
- Blueprint novo `routes/admin_saas.py` sob prefixo `/admin` (nome a confirmar).
- Protegido por decorator `@requer_super_admin` (novo em `utils/authz.py`).
- Seed: cria um Super-Admin inicial (credenciais via env, com troca obrigatória no 1º acesso).

### 5.2. CRUD de Empresas
- Listar, criar, editar, ver detalhe, suspender/reativar/cancelar empresa.
- Ao **criar** uma empresa: opção de já criar o **usuário administrador** daquela empresa
  (perfil Administrador + seed de perfis/permissões padrão daquele tenant).

### 5.3. Painel administrativo (dashboard do SAAS)
Indicadores agregados **entre empresas** (sem expor dados clínicos individuais):
- Nº de empresas por status (ativas, trial, suspensas, canceladas).
- Nº de empresas por plano; receita recorrente estimada (MRR) por plano.
- Empresas com assinatura próxima do vencimento.
- Métricas de uso por empresa (contagens agregadas: usuários ativos, nº de pacientes,
  internações no período, volume de atendimentos) — números, não conteúdo clínico.
- **Gráficos** (crescimento de empresas no tempo, distribuição por plano/status, uso
  comparado). Implementação com **Chart.js** (CDN, coerente com o stack Jinja2/HTMX,
  respeitando a CSP da S-09).

---

## 6. Rebranding QUÍRON

- Nome do produto: **QUÍRON — Inteligência Clínica, Segurança e Performance Hospitalar**.
- Onde trocar: título/branding nos templates (`layout.html`, login, rodapé), `README.md`,
  documentação (`docs/`), nome amigável em `config.py` (mantendo compatibilidade de env),
  e-mails/mensagens. O nome técnico interno de pacote/DB pode permanecer para evitar
  migração desnecessária de infra; o rebranding é de **produto/UX**, decidido na implementação.
- O nome da instituição em documentos clínicos (laudos/PDFs) passa a vir da **empresa (tenant)**,
  não mais de `INSTITUICAO_NOME` global do `config.py`.

---

## 7. Migração da empresa-modelo (Santa Casa de Pedralva)

- Migração de dados: cria a empresa `Santa Casa de Pedralva` e **vincula todos os
  registros existentes** a ela (`empresa_id` = ela) numa data migration Alembic.
- Garante que nenhum dado atual fique "órfão" (sem tenant) após a introdução da coluna.
- Backup do banco antes de aplicar (procedimento já documentado em `docs/migracao-producao.md`).

---

## 8. Fases de execução (com validação incremental)

> Cada fase termina com app subindo, testes passando e commit/push na branch `quiron`.

**Fase MT-0 — Fundação e rebranding (base)**
- ADR-007 (multi-tenancy). Model `Empresa`. Flag `is_super_admin` e `empresa_id` no `Usuario`.
- Rebranding QUÍRON na UI e docs. Sem quebrar o app atual (empresa única).

**Fase MT-1 — Coluna de tenant + migração de dados**
- Adiciona `empresa_id` às tabelas raiz. Data migration cria a Santa Casa de Pedralva e
  vincula os dados existentes. Constraints de unicidade compostas.

**Fase MT-2 — Isolamento automático**
- `TenantMixin`, filtro automático de leitura, escrita automática do tenant, contexto `g.empresa_id`.
- Ajuste de `autorizar_recurso` para checar tenant. **Testes de isolamento A↔B.**

**Fase MT-3 — Super-Admin + CRUD de empresas**
- Decorator `@requer_super_admin`, blueprint `/admin`, CRUD de empresas, criação do admin
  da empresa no cadastro. Seed do Super-Admin.

**Fase MT-4 — Painel administrativo com gráficos**
- Service de indicadores do SAAS + dashboard com Chart.js.

**Fase MT-5 — Verificação, testes e documentação**
- Suíte de testes (isolamento, super-admin, CRUD). Atualiza `PROJECT_STATE.md`,
  `architecture.md`, `datamodel.md`, `GUIA_DE_USO.md`. CI verde.

**Fase MT-6 — Merge**
- Após validação completa (você aprova), merge da `quiron` na `main`.

### Trilha de segurança ISO 27001 (fases SEC-x)

> Detalhamento e mapeamento por controle do Anexo A em `docs/iso27001-gap-analysis.md`.
> Executadas junto/depois das fases MT-x (compartilham a refatoração de usuário,
> auditoria e config). **A ISO 27001 certifica a organização/SGSI, não o software** —
> aqui entregamos os **controles técnicos** que deixam o produto aderente e auditável.

**Fase SEC-1 — Autenticação forte (A.8.5)**
- **2FA/TOTP** (`pyotp`) com QR de enrollment; obrigatório para Super-Admin e Administradores;
  forçável por empresa. Recuperação por códigos de backup.

**Fase SEC-2 — Auditoria de eventos de segurança + integridade (A.8.15/A.5.28)**
- Estende a trilha para login (sucesso/falha), CRUD de usuário, mudança de permissão,
  cadastro/suspensão de empresa. **Encadeamento por hash** (cadeia à prova de adulteração).

**Fase SEC-3 — Criptografia em repouso (A.8.24)**
- Cifra a nível de coluna para dados ultrassensíveis (ex.: CPF, CNS) via `pgcrypto`/app;
  orientação de cifra de volume (LUKS) na VPS. Gestão/rotação de chave documentada.

**Fase SEC-4 — Backup externo criptografado (A.8.13/A.5.29-30)**
- Rotina de `pg_dump` diário → criptografado → enviado a armazenamento externo isolado
  da VPS (S3/GCS/outro). Procedimento de restore + DR documentado.

**Fase SEC-5 — Dados seguros fora de produção (A.8.31)**
- Garante seed 100% fictício/mascarado; anonimização de dump para homolog; regra
  documentada "nunca dado real em dev/homolog".

**Fase SEC-6 — DevSecOps no CI (A.8.28)**
- Adiciona **SAST (`bandit`)** e **secret scanning (`gitleaks`)** ao `ci.yml` (falha o build).
- Sanitização com `bleach` em texto livre / revisão de `| safe`. Redes Docker segregadas
  também em dev. Proteção de branch `main` + revisão obrigatória.

**Fase SEC-7 — Hardening de infra e documentação (A.5.23/A.8.20/A.8.22)**
- Documento de responsabilidade compartilhada VPS; hardening SSH (chave, sem senha, via VPN);
  WAF na frente da VPS; tabela de rastreabilidade de controles ISO (`docs/security/iso27001-controles.md`).

---

## 9. Riscos e mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Vazamento entre tenants (dado da empresa A visível para B) | **Crítico** (LGPD/saúde) | Filtro automático + escrita automática + testes de isolamento dedicados; revisão do @si |
| Esquecer `empresa_id` em alguma das 154 rotas | Alto | Isolamento na **camada de dados** (não por rota), reduzindo dependência de disciplina do dev |
| Migração de dados órfãos na Pedralva | Alto | Data migration atômica + backup + verificação pós-migração |
| Unicidade global de `username`/`cpf` quebrando multi-tenant | Médio | Constraints compostas por empresa; revisão caso a caso |
| Super-Admin acessar dado clínico por engano | Alto (privacidade) | Super-Admin sem `empresa_id`; blueprint isolado; nunca instancia queries de negócio |
| Regressão nos 24 módulos existentes | Médio | Execução por fases com app subindo e testes a cada fase |
| Ransomware destruindo VPS + banco juntos | **Crítico** | Backup externo criptografado e isolado (SEC-4) + DR testado |
| Dados sensíveis legíveis se o disco/volume vazar | Alto | Criptografia em repouso: volume (LUKS) + coluna (SEC-3) |
| Conta comprometida por senha fraca/vazada | Alto | 2FA/TOTP para papéis privilegiados (SEC-1) |
| Adulteração de trilha de auditoria | Alto | Encadeamento por hash (trilha inviolável — SEC-2) |
| Vulnerabilidade introduzida em atualização | Médio | SAST + secret scanning + pip-audit no CI (SEC-6) |

---

## 10. Fora de escopo (agora)

- Billing/cobrança automática integrada a gateway de pagamento (só a estrutura de plano/status).
- Subdomínio por tenant (`empresa.quiron.app`) e roteamento por host — avaliável em fase futura.
- Provisionamento de banco/schema por tenant (fica na abordagem C).
- Onboarding self-service (empresa se cadastra sozinha) — no MVP o Super-Admin cadastra.

---

## 11. Entregáveis para sua aprovação

1. **Este plano** (`docs/plano-quiron-multitenant.md`) — inclui as trilhas MT-x (multi-tenant) e SEC-x (ISO 27001).
2. **PRD atualizado** para o QUÍRON multi-tenant + segurança ISO 27001 (`docs/prd.md`, versão 2.0).
3. **Gap analysis ISO 27001** (`docs/iso27001-gap-analysis.md`) — o que já temos x o que falta, por controle do Anexo A.

Ao aprovar, sigo pela **Fase MT-0** e vou commitando na branch `quiron` a cada fase.
As fases SEC-x entram intercaladas com as MT-x conforme dependências (ex.: SEC-1/2
dependem do model de usuário já ajustado na MT-0).
