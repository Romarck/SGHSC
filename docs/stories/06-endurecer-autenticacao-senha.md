# Story S-06 — Endurecer autenticação e política de senha

**Épico:** Base e Segurança (FR-01 / NFR-01)
**Prioridade:** P1
**Status:** Concluído
**Origem:** @si M-01 / M-02 (Médio) · B-01 (Baixo)

---

## Contexto
- O login expõe "Tentativas restantes: N", que só aparece para usuário existente — reduz o
  benefício da mensagem genérica e permite enumeração (M-01).
- Política de senha exige apenas 8 caracteres, sem complexidade ou verificação contra senhas
  comuns (M-02).
- `remember me` gera cookie persistente em estações compartilhadas do hospital (B-01).
- `deve_trocar_senha` só é checado no login; usuário com sessão ativa e flag ligada não é
  forçado a trocar.

## Descrição
Como **administrador de TI**, quero controles de autenticação mais fortes, para reduzir risco
de acesso indevido em um ambiente com estações compartilhadas.

## Critérios de Aceite
- [x] Mensagem de credencial inválida **genérica** — sem contador de tentativas e indistinguível entre usuário inexistente e senha errada (anti-enumeração).
- [x] Política de senha reforçada: **≥ 10** caracteres + complexidade (≥ 3 de 4 classes) + blocklist de senhas comuns + bloqueio de username na senha; validada na troca.
- [x] `before_request` global redireciona para a troca de senha enquanto `deve_trocar_senha=True` (inclusive em sessão já ativa).
- [x] `remember me` **desabilitado por padrão** (config `LOGIN_REMEMBER_HABILITADO=False`); checkbox oculto; duração limitada + `Secure` em prod caso reabilitado.

## Tarefas
1. [x] Mensagens de login genéricas, sem contador (`MSG_CREDENCIAL_INVALIDA`).
2. [x] Validador de política em `app/security/password_policy.py` (`validar_senha` + `SenhaForte`), aplicado no `TrocarSenhaForm` e revalidado no route com o username.
3. [x] `before_request` `_forcar_troca_de_senha` no factory (isenta `auth.trocar_senha`, `auth.logout`, `static`).
4. [x] `remember me` desabilitado por padrão; config `REMEMBER_COOKIE_*`; UI condicional.
5. [x] Testes em `tests/test_auth_hardening.py` (14 casos) — suíte completa **36 passed**.

## Implementação (resumo @dev)
- `app/security/password_policy.py`: política reutilizável (comprimento/complexidade/blocklist/username).
- `routes/auth.py`: mensagem única genérica para qualquer falha de credencial; bloqueio de 5 tentativas mantido (silencioso); `SenhaForte` no form + revalidação server-side na troca; `remember` só honrado se `LOGIN_REMEMBER_HABILITADO`.
- `__init__.py`: `before_request` de troca obrigatória (cobre sessão ativa, não só o login).
- `config.py`: `LOGIN_REMEMBER_HABILITADO=False`, `REMEMBER_COOKIE_DURATION/HTTPONLY/SECURE`; `ProductionConfig.REMEMBER_COOKIE_SECURE=True`.
- Templates: checkbox "lembrar" condicional; dica de senha atualizada (10+ / complexidade).

## Verificação
- `pytest`: **36 passed** (14 novos + 22 existentes, sem regressão) na imagem do app.
- Cobertos: mensagem genérica/anti-enumeração, política (validador + fluxo), redirect forçado em sessão ativa (sem loop), remember me sem cookie persistente.

## Notas
- Bloqueio após 5 tentativas preservado.
- `remember me` foi **desabilitado** (não apenas reduzido) por ser o default mais seguro em estações compartilhadas; pode ser reativado via config (com duração/Secure já preparados) se um perfil específico justificar.
- Próximo passo: **@qadv `*qa 6`**.

---

## QA — @qadv (`*qa 6`)

**Resultado:** ✅ **APROVADO** na primeira rodada.

### Método
Revisão de código + suíte completa + **probes de borda** próprios (rodados em
pytest na imagem do app, depois removidos).

### Evidências
| Critério | Verificação | Resultado |
|----------|-------------|-----------|
| Mensagem genérica / anti-enumeração | usuário inexistente vs senha errada → mesma mensagem, sem contador | ✅ |
| Política de senha (≥10 + complexidade + blocklist + username) | validador puro + fluxo de troca | ✅ |
| `before_request` de troca obrigatória | cobre `/dashboard`, **outros blueprints** (`/pacientes/`) e **partial HTMX** (`/dashboard/contadores`); POST de troca não é bloqueado (sem loop); login com flag redireciona | ✅ |
| `remember me` desabilitado | sem cookie `remember_token`; checkbox oculto | ✅ |
| Regressão | suíte completa | **36 passed** |

### Observações (não bloqueantes)
1. **Canal lateral de tempo (timing):** para usuário inexistente o retorno é
   imediato; para usuário existente com senha errada há o custo do bcrypt + escrita
   de `tentativas_login`. Um atacante determinado poderia inferir existência por
   tempo de resposta. O critério da story trata da **mensagem** (atendido). Mitigar
   o timing (ex.: hash dummy para usuário inexistente) fica como melhoria futura.
2. **Mensagem de bloqueio** ("Conta temporariamente bloqueada") revela que o
   usuário existe após 5 tentativas — inerente ao recurso de lockout, aceitável.
3. **Blocklist é match exato** (`senha123` barrada; `senha123!` passa pela blocklist
   mas é barrada por comprimento/complexidade). Sem furo prático; ampliar a lista/
   heurística é evolução opcional.

### Decisão de escopo aceita
- @dev **desabilitou** o remember me (em vez de só reduzir duração). A story permitia
  ambos; desabilitar é o default mais seguro para estações compartilhadas e a config
  (`LOGIN_REMEMBER_HABILITADO` + `REMEMBER_COOKIE_*`) permite reativar de forma
  controlada. Aprovado.
