# ADR-001 — Frontend server-side com Jinja2 + HTMX (sem SPA)

**Status:** Aceito (retroativo)
**Data:** 2026-08-28
**Autor:** @architect
**Contexto de origem:** decisão implícita promovida a ADR durante o `*audit`

---

## Contexto

O SGHSC é operado por uma Santa Casa de pequeno/médio porte, em rede local, por
profissionais com perfis variados (recepção, enfermagem, médicos, administrativo).
A equipe de desenvolvimento é enxuta e não há pipeline de build de frontend nem
especialista dedicado a JavaScript/SPA.

Era preciso escolher como renderizar a interface: SPA (React/Vue/Angular) consumindo
API, ou renderização server-side.

## Decisão

Adotar **renderização server-side com Jinja2**, com interatividade incremental via
**HTMX** e **Bootstrap 5** (+ Bootstrap Icons) para o design. Não há build step de
frontend nem framework SPA.

- Páginas e fragmentos são templates Jinja2 servidos pelo Flask.
- Interações dinâmicas (busca em tempo real, atualização de fila/mapa de leitos,
  formulários parciais) usam atributos HTMX (`hx-get`, `hx-trigger`, `hx-target`).
- JavaScript é usado apenas de forma pontual (ex.: ViaCEP, itens dinâmicos de prescrição).

## Consequências

**Positivas**
- Sem toolchain de build (Node, bundlers) — menor complexidade operacional.
- Um único deploy (o próprio Flask serve tudo); menos superfície de erro.
- Curva de aprendizado baixa para a equipe; produtividade alta por módulo.
- CSRF e sessão tratados nativamente pelo servidor.

**Negativas / trade-offs**
- Interatividade rica (offline, drag-and-drop complexo, gráficos avançados) é mais
  trabalhosa que numa SPA.
- Acoplamento entre backend e apresentação; reuso por clientes externos exige criar
  API dedicada no futuro.
- Testes de UI dependem de renderização server-side.

## Alternativas consideradas

- **SPA (React/Vue) + API REST:** maior flexibilidade de UI, porém adiciona build,
  autenticação via token, versionamento de API e duplicação de validação. Rejeitada
  pelo custo de complexidade frente ao porte do projeto.
- **Server-side puro (só Jinja2, sem HTMX):** simples, mas exige recarregar a página
  inteira a cada ação. HTMX resolve isso sem SPA.

## Referências
- `docs/architecture.md` (seções 1–3)
- `docs/PROJECT_STATE.md` — "Decisões Técnicas Tomadas"
