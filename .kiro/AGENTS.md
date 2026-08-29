# PDA-SQUAD — SGHSC

**Tipo:** greenfield | **Stack:** Outro + Outro + PostgreSQL
**Framework:** PDA-SQUAD v1.0.0

---

## Visão Geral

Este projeto usa o **PDA-SQUAD**, um framework de desenvolvimento guiado por IA com 6 agentes especializados. O desenvolvimento é orientado por stories em `docs/stories/`.

---

## Agentes Disponíveis

Cada agente tem escopo exclusivo. Invoque-os pelo nome ao iniciar uma conversa:

| Agente | Invocar com | Responsabilidade |
|--------|-------------|-----------------|
| `@po` | `@po` | Brainstorm, PRD, stories, backlog |
| `@architect` | `@architect` | Arquitetura, stack, modelo de dados, ADRs |
| `@dev` | `@dev` | Implementação, debug, refactor |
| `@ux` | `@ux` | Pesquisa, wireframes, design system |
| `@si` | `@si` | Auditoria, segurança, compliance BCB/FEBRABAN/B3/CVM |
| `@qadv` | `@qadv` | QA, aprovação de stories, deploy |

> Cada agente responde ao comando `*help` com sua lista completa de ações.

---

## Comandos por Agente

### @po — Product Owner
| Comando | O que faz |
|---------|-----------|
| `*brainstorm` | Sessão estruturada de ideação |
| `*prd` | Cria/atualiza `docs/prd.md` |
| `*stories` | Gera stories a partir do PRD |
| `*story {título}` | Cria uma story específica |
| `*prioritize` | Reordena o backlog |
| `*status` | Mostra status das stories |

### @architect — Arquiteto
| Comando | O que faz |
|---------|-----------|
| `*audit` | Audita o codebase (brownfield) |
| `*stack` | Escolhe e documenta a stack |
| `*architecture` | Define arquitetura do sistema |
| `*datamodel` | Cria/atualiza modelo de dados |

### @dev — Desenvolvedor
| Comando | O que faz |
|---------|-----------|
| `*develop N` | Implementa a story N |
| `*refactor` | Refatora código existente |
| `*test N` | Gera testes para story N |

### @ux — Design
| Comando | O que faz |
|---------|-----------|
| `*research` | Pesquisa de usuário |
| `*wireframes` | Cria wireframes textuais |
| `*design-system` | Cria/valida design system |

### @si — Segurança & Compliance
| Comando | O que faz |
|---------|-----------|
| `*audit-code` | Auditoria completa (7 fases) |
| `*scan-deps` | Análise de dependências |
| `*compliance BCB` | Valida conformidade BCB 85/2021 |
| `*compliance FEBRABAN` | Checklist CNAB/pagamentos |
| `*compliance B3-CVM` | Checklist mercado de capitais |
| `*report` | Gera relatório de segurança |

### @qadv — QA & Deploy
| Comando | O que faz |
|---------|-----------|
| `*qa N` | Revisa qualidade da story N |
| `*deploy` | Prepara checklist de deploy |
| `*rollback` | Planeja rollback |

---

## Estrutura de Documentos

```
docs/
├── prd.md               # Product Requirements Document
├── architecture.md      # Arquitetura do sistema
├── datamodel.md         # Modelo de dados
├── stories/             # User stories (N-titulo.md)
├── decisions/           # ADRs (ADR-N-titulo.md)
├── security/            # Relatórios de segurança
└── ux/                  # Wireframes, pesquisa, design system
```

---

## Fluxo de Trabalho


### Projeto Novo (Greenfield)

```
1. DESCOBERTA    @po *brainstorm → *prd
2. SEGURANÇA     @si *scan-deps (opcional, pré-build)
3. DESIGN        @architect *stack → *architecture → *datamodel
                 @ux *research → *wireframes (em paralelo)
4. PLANEJAMENTO  @po *stories
5. CONSTRUÇÃO    @dev *develop N → @qadv *qa N   (repetir por story)
6. PRÉ-PRODUÇÃO  @si *audit-code  ← obrigatório
7. ENTREGA       @qadv *deploy
```



---

## Princípios Fundamentais

1. **Story-Driven:** nenhum código sem story válida em `docs/stories/`
2. **Autoridade dos agentes:** respeite escopos exclusivos (ver `.kiro/constitution.md`)
3. **Sem invenção:** implemente apenas o que está documentado
4. **Qualidade primeiro:** toda story passa pelo `@qadv` antes de `Concluído`
5. **Segurança obstinada:** `@si` tem veto em brownfield e pré-produção

---

## Arquivos Sempre Relevantes

- `docs/prd.md` — requisitos do produto
- `docs/architecture.md` — decisões de arquitetura
- `docs/stories/` — stories ativas
- `.kiro/constitution.md` — princípios do framework

---

*PDA-SQUAD v1.0.0 | Kiro CLI | Instalado em 2026-08-28T14:58:50.402Z*
