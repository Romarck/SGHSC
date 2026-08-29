# PRD: SGHSC — Sistema de Gestão Hospitalar para Santas Casas

**Data:** 2026-08-28
**Autor:** @po
**Status:** Em Revisão
**Versão:** 1.0

> Este PRD foi elaborado **retroativamente**, a partir do sistema já implementado (6 fases)
> e das análises do `@architect` (`docs/architecture.md`, `docs/datamodel.md`) e do `@si`
> (`docs/security/audit-report.md`). Ele documenta o produto e orienta o backlog de ajustes.

---

## 1. Visão do Produto

### Problema
As Santas Casas de misericórdia — hospitais filantrópicos que atendem majoritariamente pelo
SUS em municípios de pequeno e médio porte — frequentemente operam com processos em papel ou
sistemas fragmentados e caros. Faltam: prontuário eletrônico integrado, rastreabilidade
clínica, controle de leitos/estoque/farmácia e conformidade documental (assinatura digital,
faturamento SUS, PGRSS, RNDS). Isso gera retrabalho, perda de receita por glosa/subfaturamento
e risco jurídico/sanitário.

### Solução Proposta
O SGHSC é um sistema hospitalar **web, integrado e de baixo custo operacional** (open-source,
Docker), cobrindo o ciclo completo: cadastro do paciente → porta de entrada (emergência/
ambulatório) → internação → apoio clínico → administrativo → gestão e compliance. Documentos
clínicos têm **assinatura digital ICP-Brasil (PAdES)** com validação pública por QR Code,
substituindo o arquivo físico com validade jurídica (MP 2.200-2/2001).

### Público-alvo

| Perfil | Descrição | Necessidade Principal |
|--------|-----------|----------------------|
| Recepção / Admissão | Cadastra pacientes, agenda, registra chegada | Cadastro rápido, busca ágil |
| Enfermagem | Triagem, controles, evolução, prescrição de enfermagem | Registro à beira-leito, mapa de leitos |
| Corpo clínico (médicos) | Atendimento, prescrição, evolução, alta, cirurgia | PEP confiável e assinável |
| Farmácia | Dispensação por prescrição, controle de lote/validade | Estoque acurado, rastreabilidade |
| Administrativo | Estoque, compras, financeiro, faturamento, RH, patrimônio | Integração e controle |
| Faturamento SUS/convênios | Guias AIH/APAC/BPA e TISS | Reduzir glosa e subfaturamento |
| Gestão / CCIH / Qualidade | Indicadores, infecção, resíduos, RNDS | Visão gerencial e compliance |
| Administrador de TI | Usuários, perfis, segurança | Controle de acesso e auditoria |

---

## 2. Objetivos

### Objetivos de Negócio
- [ ] Digitalizar o ciclo assistencial completo em uma unidade (Santa Casa de Pedralva) como piloto.
- [ ] Substituir documentos clínicos em papel por documentos assinados digitalmente com validade jurídica.
- [ ] Servir de **template replicável** para outras Santas Casas.
- [ ] Reduzir perda de receita por glosa/subfaturamento SUS e convênios.

### Métricas de Sucesso (KPIs)
| Métrica | Meta | Prazo |
|---------|------|-------|
| Módulos assistenciais em uso real | 100% do ciclo | Piloto |
| Documentos clínicos assinados digitalmente | ≥ 90% dos assináveis | Pós go-live |
| Achados de segurança CRÍTICOS/ALTOS abertos | 0 antes do go-live | Pré-produção |
| Tempo de resposta (p95) das telas principais | < 2 s | Contínuo |

---

## 3. Funcionalidades (implementadas)

> Detalhamento técnico em `docs/PROJECT_STATE.md`; dados em `docs/datamodel.md`.

### Épico 1 — Base e Segurança
- **FR-01:** Autenticação (login/logout, troca de senha obrigatória, bloqueio após 5 tentativas).
- **FR-02:** Controle de acesso por perfis (RBAC — modelo `Perfil`/`Permissao`).
- **FR-03:** Auditoria de registros (criado/atualizado por, logs).

### Épico 2 — Porta de Entrada
- **FR-04:** Cadastro de pacientes com busca em tempo real e ViaCEP.
- **FR-05:** Pronto-Atendimento com Triagem Manchester.
- **FR-06:** Ambulatório (agenda + atendimento).

### Épico 3 — Internação
- **FR-07:** Gestão de leitos (mapa visual), admissão, transferência, alta com laudo PDF.
- **FR-08:** Prescrição médica e de enfermagem; evoluções; controles (sinais vitais, balanço hídrico).

### Épico 4 — Apoio Clínico
- **FR-09:** Exames, Farmácia (FEFO), Nutrição, CCIH, Cirurgias, Maternidade.
- **FR-10:** Certificação digital ICP-Brasil (assinatura PAdES + QR de validação pública).

### Épico 5 — Administrativo
- **FR-11:** Estoque, Compras, Financeiro, Faturamento SUS, Convênios, Patrimônio, RH, Manutenção.

### Épico 6 — Gestão e Compliance
- **FR-12:** Dashboard gerencial, PGRSS (resíduos), RNDS (payload FHIR R4).

---

## 4. Requisitos Não-Funcionais

| ID | Categoria | Requisito |
|----|-----------|-----------|
| NFR-01 | Segurança — AuthZ | Toda rota sensível deve exigir permissão específica (RBAC efetivo), não só autenticação. |
| NFR-02 | Segurança — Transporte | HTTPS/TLS 1.2+ obrigatório com HSTS em produção. |
| NFR-03 | Privacidade — LGPD | Dados de saúde tratados como sensíveis; log de acesso a prontuário; mínimo necessário exposto. |
| NFR-04 | Segurança — Segredos | `SECRET_KEY`/senhas apenas via env; falha rápida se ausentes em produção. |
| NFR-05 | Segurança — Dependências | Sem vulnerabilidades CRÍTICAS/ALTAS conhecidas; varredura contínua no CI. |
| NFR-06 | Qualidade | Suíte de testes automatizados; CI com lint + testes + migração. |
| NFR-07 | Performance | p95 < 2 s nas telas principais. |
| NFR-08 | Conformidade documental | Assinatura PAdES com cadeia ICP-Brasil validável em produção. |
| NFR-09 | Disponibilidade | Operação em rede local com recuperação simples (backup cifrado). |

---

## 5. Restrições e Premissas

### Restrições
- **Tecnológicas:** Python/Flask + PostgreSQL + Docker; frontend server-side Jinja2/HTMX (ver ADRs).
- **Regulatórias:** LGPD (Lei 13.709/2018), CFM/PEP, MP 2.200-2/2001 (ICP-Brasil), ANVISA RDC 222/2018 (PGRSS).
- **Orçamento:** baixo custo (unidade filantrópica); evitar licenças proprietárias.

### Premissas
- Assinatura com certificado **A1 e-CNPJ** no servidor (A3/token inviável no backend).
- Integrações externas (DATASUS/SIGTAP, RNDS) dependem de credenciamento e tabelas oficiais.
- **Fora de escopo de compliance financeiro:** BCB 85/2021, FEBRABAN/CNAB, B3/CVM — o sistema
  não processa dados bancários, pagamentos regulados nem mercado de capitais.

---

## 6. Fora do Escopo (agora)

- Exportação DATASUS no layout magnético oficial (SISAIH01/BPA-MAG) — depende das tabelas SIGTAP.
- Transmissão real à RNDS — depende de credenciamento no DATASUS (X.509 + OAuth).
- Certificação em nuvem (BirdID/RemoteID) e A3 — evolução futura.
- Compliance de setor financeiro (BCB/FEBRABAN/B3-CVM) — não aplicável.

---

## 7. Riscos

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Ir a produção sem RBAC efetivo (acesso indevido a prontuário) | Alta | Alto | Veto do @si; stories S-01/S-02 antes do go-live |
| Dados de saúde em trânsito sem TLS | Média | Alto | Ativar HTTPS/HSTS (S-03) |
| Vazamento de segredo por config fraca | Média | Alto | `validate()` no factory + segredos por env (S-05) |
| Dependências com CVE exploradas | Média | Médio | Atualização + varredura contínua (S-06) |
| Ausência de testes/CI facilita regressões | Alta | Médio | Suíte de testes + CI (S-08) |
| Não conformidade LGPD (log de acesso) | Média | Médio | Auditoria de leitura de prontuário (S-07) |

---

## 8. Backlog derivado das auditorias

As correções recomendadas pelo `@architect` e `@si` foram convertidas em **stories** em
`docs/stories/`. Prioridade orientada pelo veto de pré-produção do `@si`:

| Story | Prioridade | Origem |
|-------|-----------|--------|
| S-01 — Aplicar RBAC nas rotas | P0 (bloqueia prod) | @si C-01 / @architect S1 |
| S-02 — Corrigir IDOR/BOLA em downloads | P0 | @si A-02 |
| S-03 — Ativar HTTPS/HSTS | P0 | @si A-01/A-03 |
| S-04 — Validação de config de produção | P0 | @si A-06 / @architect S2 |
| S-05 — Atualizar dependências com CVE | P1 | @si A-05/M-05 |
| S-06 — Endurecer autenticação e senha | P1 | @si M-01/M-02 |
| S-07 — Log de acesso a prontuário (LGPD) | P1 | @si M-04 |
| S-08 — Suíte de testes + CI | P1 | @architect (qualidade) |
| S-09 — Rate limiting + headers + upload | P2 | @si M-03/M-07/B-03 |
| S-10 — Migração de banco segura em produção | P2 | @si I-01 / @architect |

---

## 9. Histórico de Mudanças

| Data | Versão | Mudança | Autor |
|------|--------|---------|-------|
| 2026-08-28 | 1.0 | PRD elaborado a partir do sistema implementado e das auditorias | @po |

---

*Gerado pelo PDA-SQUAD v1.0.0 — comando `@po *prd`*
