# Workflow: Projeto Novo (Greenfield)

Guia passo a passo para iniciar um projeto do zero com PDA-SQUAD.

---

## Visão Geral

```
DESCOBERTA → DESIGN → PLANEJAMENTO → CONSTRUÇÃO (ciclo) → ENTREGA
```

---

## Fase 1: Descoberta

**Objetivo:** Entender o problema e definir o que será construído.

### 1.1 Brainstorm
```
Ative: @product
Comando: *brainstorm
```
O `@product` conduz uma sessão estruturada:
- Qual problema estamos resolvendo?
- Para quem?
- Quais são as possíveis soluções?
- Hipóteses a validar

**Entrega:** Documento de brainstorm no chat (insumo para o PRD)

### 1.2 PRD
```
Ative: @product
Comando: *prd
```
Cria `docs/prd.md` com:
- Visão do produto e problema
- Público-alvo e personas
- Funcionalidades organizadas por épico
- Requisitos não-funcionais
- Fora do escopo (MVP)

**Entrega:** `docs/prd.md` preenchido

### 1.3 Pesquisa UX (opcional)
```
Ative: @ux
Comando: *research
```
Complementa o PRD com pesquisa de usuário.

**Entrega:** `docs/ux/research.md`, `docs/ux/personas.md`

---

## Fase 2: Design

**Objetivo:** Definir como o sistema será construído.

> As subfases 2.1 e 2.2 podem ser executadas em paralelo.

### 2.1 Arquitetura Técnica
```
Ative: @architect
Comandos (em sequência): *stack → *architecture → *datamodel
```

- `*stack`: define tecnologias (backend, frontend, banco, deploy)
- `*architecture`: cria `docs/architecture.md`
- `*datamodel`: cria `docs/datamodel.md` com schema SQL/NoSQL

**Entrega:** `docs/architecture.md`, `docs/datamodel.md`, ADRs em `docs/decisions/`

### 2.2 Design System (opcional)
```
Ative: @ux
Comandos: *wireframes → *design-system
```

- `*wireframes`: wireframes textuais das telas principais
- `*design-system`: define cores, tipografia, componentes

**Entrega:** `docs/ux/wireframes/`, `docs/ux/design-system.md`

---

## Fase 3: Planejamento

**Objetivo:** Criar e priorizar as stories de desenvolvimento.

```
Ative: @product
Comando: *stories
```

O `@product` lê o `docs/prd.md` e gera uma story para cada funcionalidade, priorizadas por valor/esforço.

**Entrega:** `docs/stories/N-titulo.md` para cada story (status: `Draft`)

> Stories ficam com status `Pronto` após o `@architect` confirmar viabilidade técnica.

---

## Fase 3.5: Auditoria de Segurança (Pré-desenvolvimento, recomendado)

**Objetivo:** Validar que templates, dependências e arquitetura não possuem riscos de segurança antes de implementar código.

> **Nota:** Esta fase é opcional para MVPs em desenvolvimento, mas obrigatória antes de deploy em produção ou em projetos regulados.

### 3.5.1 Auditoria de Segurança

```
Ative: @security
Comando: *scan-deps
```

Valida:
- Supply chain (typosquatting, versões perigosas)
- Dependências e licenças
- Padrões suspeitos de código

**Entrega:** `docs/security/scan-report.md`

### 3.5.2 Compliance Regulatório (se aplicável)

```
Ative: @security
Comando: *compliance [BCB|FEBRABAN|B3-CVM]
```

Se o projeto for para ambiente regulado, valide conformidade.

---

## Fase 4: Construção (ciclo por story)

**Objetivo:** Implementar e validar uma story por vez.

Repita este ciclo para cada story com status `Pronto`:

### 4.1 Implementar
```
Ative: @dev
Comando: *develop {N}
```
O `@dev`:
1. Lê a story e a arquitetura
2. Identifica a stack pelo projeto
3. Implementa tarefa por tarefa
4. Escreve testes
5. Faz commits atômicos

### 4.2 Quality Gate
```
Ative: @ship
Comando: *qa {N}
```
O `@ship` verifica 7 critérios. Se aprovado → status `Concluído`. Se reprovado → volta para `@dev`.

---

## Fase 5: Entrega

**Objetivo:** Fazer deploy do que foi construído.

```
Ative: @ship
Comandos: *push → *pr "descrição" → *deploy staging → *deploy production
```

> O `@ship` tem autoridade exclusiva sobre git push, Pull Requests e deploy.

---

## Diagrama do Fluxo

```
START
  │
  ▼
@product *brainstorm
  │
  ▼
@product *prd ─────── (opcional: @ux *research)
  │
  ▼
@architect *stack
  │
  ▼
@architect *architecture ── (opcional: @ux *wireframes)
  │
  ▼
@architect *datamodel ───── (opcional: @ux *design-system)
  │
  ▼
@product *stories
  │
  ▼
@security *scan-deps (recomendado antes de implementar)
  │
  ▼
@security *compliance [se regulado]
  │
  ▼
┌─────────────────────────────┐
│  Para cada story "Pronto"   │
│                             │
│  @dev *develop {N}          │
│        │                    │
│        ▼                    │
│  @ship *qa {N}              │
│        │                    │
│  ✅ Aprovado? ──── Sim ─► Próxima story
│        │                    │
│        └─── Não ──► @dev corrige
└─────────────────────────────┘
  │
  ▼
@security *audit-code (obrigatório antes de produção)
  │
  ▼
@ship *deploy production
  │
  ▼
END
```

---

*PDA-SQUAD v1.0.0*
