# ADR-005 — Autenticação por sessão (Flask-Login) e autorização RBAC por Perfil/Permissão

**Status:** Aceito (retroativo) — com pendência de implementação (ver Consequências)
**Data:** 2026-08-28
**Autor:** @architect
**Contexto de origem:** decisão implícita promovida a ADR durante o `*audit`

---

## Contexto

O SGHSC é uma aplicação web server-side (ver ADR-001) usada por profissionais com papéis
distintos (médico, enfermeiro, farmacêutico, recepção, faturamento, gestor, etc.). É
preciso autenticar usuários e restringir o que cada papel pode fazer, atendendo a
requisitos de sigilo do prontuário e trilha de auditoria.

## Decisão

- **Autenticação por sessão** com **Flask-Login** (`session_protection="strong"`),
  senhas com **Bcrypt** (property `senha` no model `Usuario`), CSRF global via Flask-WTF.
- Cookies de sessão `HTTPOnly`; `Secure` + `SameSite=Strict` em produção; sessão de 8h
  (turno hospitalar). Bloqueio de conta após 5 tentativas por 30 min. Troca de senha
  obrigatória no primeiro acesso (`deve_trocar_senha`).
- **Autorização RBAC** modelada com `Usuario → Perfil → (M:N) Permissao`, permissões no
  formato `modulo.acao` (ex.: `pacientes.criar`). Método `Usuario.tem_permissao(codigo)`.

## Consequências

**Positivas**
- Sessão server-side casa naturalmente com a UI Jinja2/HTMX (sem gestão de tokens no cliente).
- RBAC granular já modelado, com 15 tipos de perfil pré-definidos.
- Proteções de conta (bloqueio, troca obrigatória, CSRF) presentes.

**Negativas / trade-offs / pendências**
- ⚠️ **RBAC não é aplicado nas rotas.** `tem_permissao()` existe mas **não é invocado**
  em nenhum handler — hoje qualquer usuário autenticado acessa qualquer módulo. Este ADR
  ratifica o **modelo**; a **aplicação** é uma pendência prioritária (achado S1 do
  `*audit`). Ação: criar decorator `@requer_permissao("modulo.acao")` e aplicá-lo nas
  rotas sensíveis.
- `deve_trocar_senha` só é checado no login; falta um `before_request` global.
- Sessão não serve clientes de API externos (coerente com ADR-001); exigiria tokens no futuro.

## Alternativas consideradas

- **JWT/OAuth (stateless):** indicado para SPA/API; desnecessário para app server-side de
  unidade única e adicionaria complexidade de refresh/revogação.
- **Autorização por papel simples (sem permissões granulares):** mais fácil, porém menos
  flexível que o modelo `Perfil`↔`Permissao` já adotado.

## Referências
- `app/models/usuario.py`, `app/extensions.py`, `app/config.py`, `app/routes/auth.py`
- `docs/architecture.md` (seção 5, achado **S1**)
