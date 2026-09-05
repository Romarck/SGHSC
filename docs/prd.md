# PRD: QUÍRON — Inteligência Clínica, Segurança e Performance Hospitalar

**Data:** 2026-09-05
**Autor:** @po
**Status:** Em Revisão (aprovação pendente)
**Versão:** 2.0 (evolução para SAAS Multi-tenant)

> **Versão 2.0** — Reposiciona o produto: o antigo **SGHSC** (Sistema de Gestão
> Hospitalar para Santas Casas), de instância única para a Santa Casa de Pedralva,
> passa a ser o **QUÍRON**, um **SAAS multi-tenant** comercializável para múltiplas
> empresas (hospitais e Santas Casas), com **isolamento total de dados** por empresa,
> **Super-Admin** operador do SAAS e **painel administrativo** gerencial.
> A versão 1.0 (produto de instância única) está preservada na seção "Histórico".

---

## 1. Visão do Produto

### O que é o QUÍRON
**QUÍRON — Inteligência Clínica, Segurança e Performance Hospitalar** é uma plataforma
hospitalar **web, integrada, multi-empresa (SAAS)**, que cobre o ciclo assistencial e
administrativo completo de um hospital e o disponibiliza como serviço para diversas
empresas na mesma instalação, cada uma com seus dados isolados.

### Problema
As Santas Casas e hospitais de pequeno/médio porte operam com processos em papel ou
sistemas fragmentados e caros. Individualmente, cada unidade tem dificuldade de
custear, instalar e manter um sistema hospitalar completo. Falta uma oferta de
**baixo custo, pronta para uso e replicável**, que entregue prontuário eletrônico,
rastreabilidade clínica, controle operacional e conformidade (assinatura digital,
faturamento SUS, PGRSS, RNDS) — **sem que cada unidade precise montar sua própria infra**.

### Solução Proposta
Um **SAAS multi-tenant**: uma única plataforma QUÍRON atende N empresas. Um **Super-Admin**
(operador comercial do SAAS) cadastra e gerencia as empresas-clientes; cada empresa acessa
**somente os seus próprios dados**, com o mesmo conjunto de módulos hospitalares já
consolidados na v1.0. Documentos clínicos mantêm **assinatura digital ICP-Brasil (PAdES)**
com validação pública por QR Code (MP 2.200-2/2001).

### Modelo de negócio
- Comercialização por **assinatura** (planos: Básico, Profissional, Enterprise).
- Cada empresa-cliente é um **tenant** com ciclo de vida (trial → ativa → suspensa → cancelada).
- A **Santa Casa de Pedralva** é a primeira empresa (piloto/modelo) migrada para o SAAS.

### Público-alvo

| Perfil | Descrição | Necessidade Principal |
|--------|-----------|----------------------|
| **Super-Admin (operador SAAS)** | Vende, cadastra e acompanha as empresas-clientes | CRUD de empresas + painel gerencial com gráficos |
| Administrador da empresa (TI/gestão) | Configura usuários/perfis da sua empresa | Controle de acesso dentro do tenant |
| Recepção / Admissão | Cadastra pacientes, agenda, registra chegada | Cadastro rápido, busca ágil |
| Enfermagem | Triagem, controles, evolução, prescrição de enfermagem | Registro à beira-leito, mapa de leitos |
| Corpo clínico (médicos) | Atendimento, prescrição, evolução, alta, cirurgia | PEP confiável e assinável |
| Farmácia | Dispensação por prescrição, controle de lote/validade | Estoque acurado, rastreabilidade |
| Administrativo | Estoque, compras, financeiro, faturamento, RH, patrimônio | Integração e controle |
| Faturamento SUS/convênios | Guias AIH/APAC/BPA e TISS | Reduzir glosa e subfaturamento |
| Gestão / CCIH / Qualidade | Indicadores, infecção, resíduos, RNDS | Visão gerencial e compliance |

---

## 2. Objetivos

### Objetivos de Negócio
- [ ] Transformar o produto em **SAAS multi-tenant** comercializável para várias empresas.
- [ ] Permitir que o **Super-Admin** venda e cadastre novas empresas de forma autônoma.
- [ ] Garantir **isolamento total de dados** entre empresas (requisito inegociável — LGPD/saúde).
- [ ] Oferecer ao Super-Admin **visão gerencial** (indicadores + gráficos) da base de clientes.
- [ ] Migrar a **Santa Casa de Pedralva** como primeira empresa, sem perda de dados.
- [ ] Manter todos os módulos hospitalares da v1.0 funcionando dentro de cada tenant.

### Métricas de Sucesso (KPIs)
| Métrica | Meta | Prazo |
|---------|------|-------|
| Isolamento entre tenants (vazamentos A↔B em testes) | **0** | Antes do go-live |
| Empresas cadastráveis pelo Super-Admin sem intervenção de dev | 100% do fluxo | Pós MT-3 |
| Dados existentes migrados para a empresa Pedralva | 100% (0 órfãos) | MT-1 |
| Módulos assistenciais operando por tenant | 100% do ciclo | Piloto |
| Documentos clínicos assinados digitalmente | ≥ 90% dos assináveis | Pós go-live |
| Tempo de resposta (p95) das telas principais | < 2 s | Contínuo |

---

## 3. Funcionalidades

### 3.1. NOVAS (v2.0 — Multi-tenant)

- **FR-MT-01 — Empresa (Tenant):** entidade `Empresa` com dados cadastrais/fiscais
  (CNPJ, CNES), plano, status de assinatura e personalização (nome, logo).
- **FR-MT-02 — Super-Admin:** papel operador do SAAS, sem vínculo a nenhuma empresa e
  **sem acesso a dados clínicos**; acessa área administrativa própria.
- **FR-MT-03 — CRUD de Empresas:** cadastrar, editar, listar, detalhar e mudar status
  (trial/ativa/suspensa/cancelada) de empresas; opção de criar o admin da empresa no cadastro.
- **FR-MT-04 — Isolamento de dados por empresa:** toda leitura/escrita é automaticamente
  escopada ao tenant do usuário; nenhuma empresa acessa dados de outra.
- **FR-MT-05 — Painel administrativo (SAAS):** dashboard do Super-Admin com indicadores
  gerenciais (empresas por status/plano, vencimentos, uso agregado) e **gráficos**.
- **FR-MT-06 — Branding por empresa:** documentos e telas exibem a identidade da empresa
  (tenant), não mais uma instituição fixa global.

### 3.2. HERDADAS (v1.0 — operam dentro de cada tenant)

> Detalhamento técnico em `docs/PROJECT_STATE.md`; dados em `docs/datamodel.md`.

- **Épico 1 — Base e Segurança:** Autenticação, RBAC (Perfil/Permissão), auditoria/LGPD.
- **Épico 2 — Porta de Entrada:** Pacientes (busca + ViaCEP), Emergência (Triagem Manchester), Ambulatório.
- **Épico 3 — Internação:** Leitos (mapa visual), admissão/transferência/alta (laudo PDF), prescrição médica e de enfermagem, controles.
- **Épico 4 — Apoio Clínico:** Exames, Farmácia (FEFO), Nutrição, CCIH, Cirurgias, Maternidade, Certificação digital ICP-Brasil (PAdES + QR).
- **Épico 5 — Administrativo:** Estoque, Compras, Financeiro, Faturamento SUS, Convênios, Patrimônio, RH, Manutenção.
- **Épico 6 — Gestão e Compliance:** Dashboard gerencial, PGRSS, RNDS (FHIR R4).

---

## 4. Requisitos Não-Funcionais

| ID | Categoria | Requisito |
|----|-----------|-----------|
| **NFR-MT-01** | **Isolamento de tenant** | **Nenhuma requisição pode ler/gravar dados de outra empresa. Enforcement na camada de dados (não só por rota), com testes de isolamento obrigatórios.** |
| **NFR-MT-02** | Privacidade do Super-Admin | O Super-Admin não acessa conteúdo clínico de nenhuma empresa; apenas metadados agregados de gestão. |
| **NFR-MT-03** | Escrita segura de tenant | `empresa_id` é atribuído automaticamente na criação do registro a partir do contexto autenticado; nunca por input do cliente. |
| NFR-01 | Segurança — AuthZ | Toda rota sensível exige permissão específica (RBAC efetivo) + escopo de tenant. |
| NFR-02 | Segurança — Transporte | HTTPS/TLS 1.2+ obrigatório com HSTS em produção. |
| NFR-03 | Privacidade — LGPD | Dados de saúde tratados como sensíveis; log de acesso a prontuário; mínimo necessário exposto; isolamento por empresa. |
| NFR-04 | Segurança — Segredos | `SECRET_KEY`/senhas apenas via env; falha rápida se ausentes em produção. |
| NFR-05 | Segurança — Dependências | Sem vulnerabilidades CRÍTICAS/ALTAS conhecidas; varredura contínua no CI. |
| NFR-06 | Qualidade | Suíte de testes automatizados (incluindo isolamento de tenant); CI com lint + testes + migração. |
| NFR-07 | Performance | p95 < 2 s nas telas principais, mesmo com múltiplos tenants. |
| NFR-08 | Conformidade documental | Assinatura PAdES com cadeia ICP-Brasil validável em produção. |
| NFR-09 | Disponibilidade | Operação com recuperação simples (backup cifrado do banco único compartilhado). |

---

## 5. Restrições e Premissas

### Restrições
- **Tecnológicas:** Python/Flask + PostgreSQL + Docker; frontend server-side Jinja2/HTMX; gráficos via Chart.js (CDN).
- **Multi-tenancy:** modelo de **coluna discriminadora `empresa_id`** (shared DB/schema) com filtro automático — ver ADR-007.
- **Regulatórias:** LGPD, CFM/PEP, MP 2.200-2/2001 (ICP-Brasil), ANVISA RDC 222/2018 (PGRSS).
- **Orçamento:** baixo custo por unidade; um único banco compartilhado reduz custo operacional do SAAS.

### Premissas
- No MVP, empresas são cadastradas **pelo Super-Admin** (não há onboarding self-service).
- Assinatura com certificado **A1 e-CNPJ** por empresa (evolução: certificado por tenant).
- Integrações externas (DATASUS/SIGTAP, RNDS) dependem de credenciamento por empresa.

---

## 6. Fora do Escopo (agora)

- Billing automático via gateway de pagamento (só estrutura de plano/status de assinatura).
- Subdomínio/roteamento por host por tenant (`empresa.quiron.app`).
- Banco ou schema dedicado por tenant (mantido o modelo de coluna discriminadora).
- Onboarding self-service da empresa.
- Exportação DATASUS no layout magnético oficial e transmissão real à RNDS (herdado da v1.0, depende de credenciais/tabelas externas).

---

## 7. Riscos

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| **Vazamento de dados entre tenants** | Média | **Crítico** | Isolamento na camada de dados + escrita automática de `empresa_id` + testes de isolamento + revisão @si |
| Dados existentes ficarem órfãos na migração da Pedralva | Média | Alto | Data migration atômica + backup + verificação pós-migração |
| Super-Admin acessar dado clínico indevidamente | Baixa | Alto | Super-Admin sem `empresa_id`; blueprint isolado; sem queries de negócio |
| Regressão nos módulos v1.0 durante a refatoração | Média | Médio | Execução por fases, app subindo e testes a cada fase |
| Unicidade global (username/cpf) conflitar entre empresas | Média | Médio | Constraints compostas por empresa |
| Ir a produção sem HTTPS/RBAC efetivo | Média | Alto | Mantidos os controles das stories S-01/S-03 da v1.0 |

---

## 8. Plano e Backlog

O plano de execução detalhado (fases MT-0 a MT-6) está em
**`docs/plano-quiron-multitenant.md`**. Resumo das fases:

| Fase | Entrega |
|------|---------|
| MT-0 | Fundação: model `Empresa`, campos no `Usuario`, rebranding QUÍRON |
| MT-1 | Coluna `empresa_id` nas tabelas raiz + migração de dados da Pedralva |
| MT-2 | Isolamento automático (leitura/escrita) + testes de isolamento |
| MT-3 | Super-Admin + CRUD de empresas |
| MT-4 | Painel administrativo com gráficos |
| MT-5 | Verificação, testes e atualização de documentação |
| MT-6 | Merge da branch `quiron` na `main` (após aprovação e validação) |

O backlog de segurança da v1.0 (stories S-01 a S-10) permanece válido e concluído;
a v2.0 acrescenta a story de **isolamento multi-tenant** como P0.

---

## 9. Histórico de Mudanças

| Data | Versão | Mudança | Autor |
|------|--------|---------|-------|
| 2026-08-28 | 1.0 | PRD do SGHSC (instância única) a partir do sistema implementado e auditorias | @po |
| 2026-09-05 | 2.0 | Evolução para SAAS multi-tenant QUÍRON: Super-Admin, CRUD de empresas, isolamento por tenant, painel administrativo, rebranding | @po |

---

*Gerado pelo PDA-SQUAD v1.0.0 — comando `@po *prd`*
