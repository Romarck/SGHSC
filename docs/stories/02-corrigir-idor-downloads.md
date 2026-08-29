# Story S-02 — Corrigir IDOR/BOLA em downloads e recursos por id

**Épico:** Base e Segurança (NFR-01 / NFR-03)
**Prioridade:** P0 — **bloqueia produção** (veto @si)
**Status:** Concluído (aprovado no QA do @qadv em 2026-08-28)
**Origem:** @si A-02 (Alto)

---

## Contexto
Rotas como `/internacao/<id>/alta/pdf` e `/certificado/documento/<id>/pdf` usam
`get_or_404(id)` e servem o arquivo **sem verificar** se o `current_user` tem vínculo/
permissão sobre aquele paciente/documento. Um usuário autenticado pode baixar o laudo de
qualquer paciente apenas iterando o `id` (IDOR/BOLA). Dado de saúde exposto → risco LGPD.

## Descrição
Como **paciente/instituição**, quero que documentos só sejam acessíveis por profissionais
autorizados àquele registro, para proteger o sigilo do prontuário.

## Critérios de Aceite
- [ ] Toda rota que serve documento/recurso por `id` verifica **autorização sobre o objeto**
  (permissão do módulo + vínculo, quando aplicável) antes de `send_file`.
- [ ] Acesso indevido retorna **403** (não 404) e é logado.
- [ ] O padrão já usado em `certificado.desativar` (`cert.usuario_id != current_user.id → 403`)
  é replicado/estendido para os demais downloads.
- [ ] Nomes de arquivo de download não vazam dados sensíveis desnecessários.

## Tarefas
1. Levantar todas as rotas com `send_file`/recurso por id (`internacao`, `certificado`, outras).
2. Definir a regra de autorização por recurso (permissão + vínculo com paciente/autor).
3. Implementar a verificação antes de servir o arquivo.
4. Testes: acesso autorizado (200) vs não autorizado (403) por recurso.

## Notas
- Complementa S-01 (RBAC): a permissão do módulo é necessária, mas não suficiente — validar
  também o vínculo com o objeto quando o dado for de um paciente específico.

---

## Implementação (@dev)

**Levantamento (Tarefa 1)** — rotas que servem documento/recurso por id via `send_file`:
- `certificado.baixar_documento` (`/certificado/documento/<id>/pdf`) — **estava só com `@login_required`** (o buraco de IDOR real).
- `internacao.baixar_laudo_alta` (`/internacao/<id>/alta/pdf`) — já recebeu `@requer_permissao("internacao.ver")` na S-01.
- `main.guia` — página de ajuda **estática** (sem PII); fora de escopo.

**Regra de autorização (Tarefa 2)** — nova helper `autorizar_recurso()` em `app/utils/authz.py`:
concede acesso se o usuário for **Administrador**, **dono** do recurso (`dono_id == current_user.id`)
ou possuir **uma das permissões de módulo** informadas; caso contrário **403 + log**.

**Aplicação (Tarefa 3)**
- `certificado.baixar_documento`: `autorizar_recurso(dono_id=doc.assinante_id, permissoes=("certificado.usar",))`,
  chamada **antes** do check de existência do arquivo (não vaza existência do documento).
- `certificado.desativar`: trocado o `if usuario_id != current_user.id: abort(403)` pela helper
  (agora também permite Administrador, de forma consistente).
- `internacao.baixar_laudo_alta`: mantém `@requer_permissao("internacao.ver")` (permissão de módulo).

**Testes (Tarefa 4)** — `tests/test_idor.py` (6 casos): não-dono sem permissão → 403;
403 antes do 404 mesmo sem arquivo; dono baixa o próprio; usuário com `certificado.usar` acessa;
admin acessa; anônimo redirecionado ao login.

**Critérios de aceite — situação**
- [x] Rotas que servem documento por id verificam autorização sobre o objeto antes do `send_file`.
- [x] Acesso indevido retorna **403** (não 404) e é logado.
- [x] Padrão de `certificado.desativar` replicado/estendido (via helper `autorizar_recurso`).
- [x] Nomes de download não expõem PII (usam `codigo_validacao`/`numero`, não nome do paciente).

**Verificação**
- `pytest tests/` → **17 passed** (11 de S-01 + 6 de S-02).
- `create_app` registra 145 rotas sem erro; módulos compilam.

**Decisão de escopo (transparência)**
- Em um PEP hospitalar, a equipe clínica legitimamente precisa de acesso entre pacientes para
  a assistência. Portanto a **fronteira de autorização é a permissão de módulo + propriedade do
  objeto**, não um vínculo 1:1 usuário↔paciente. O que a S-02 fecha é o IDOR real: um usuário
  **sem** a permissão de módulo (ex.: recepção) não consegue mais iterar ids e baixar documentos.
- Um controle mais fino (ex.: só o médico responsável pela internação) exigiria uma regra de
  negócio adicional não especificada nesta story — registrar como evolução se o negócio exigir.

---

## QA (@qadv) — APROVADO ✅

**Data:** 2026-08-28 · **Veredito:** Aprovado (quality gate passou)

Verificação independente (não baseada apenas no relatório do @dev):

| Verificação | Método | Resultado |
|-------------|--------|-----------|
| Testes passam | `pytest tests/` no container | **17 passed** (6 de S-02, sem regressão nas 11 de S-01) |
| Cobertura de `send_file` | varredura de todas as rotas com `send_file` | `certificado.baixar_documento` (helper de objeto) + `internacao.baixar_laudo_alta` (permissão de módulo) protegidos; `main.guia` é página estática sem PII (fora de escopo) |
| Ordem 403 antes de 404 | leitura do código + teste `test_403_antes_de_checar_existencia_do_arquivo` | `autorizar_recurso()` roda **antes** do `os.path.exists` → não vaza existência |
| Lógica da helper | probe direto de `autorizar_recurso` (dono / permissão / nenhum / default) | dono→ok, permissão→ok, nenhum→403, **default deny→403** |
| Nomes de download | inspeção | usam `codigo_validacao`/`numero`, sem nome de paciente |

**Critérios de aceite:** todos atendidos.

**Ressalvas (não bloqueantes):**
- Escopo de autorização = permissão de módulo + propriedade do objeto (equipe clínica tem
  acesso entre pacientes por necessidade assistencial). Controle mais fino (só o médico
  responsável) fica como evolução futura, se o negócio exigir — não é requisito desta story.
- Cobertura de teste do `internacao.baixar_laudo_alta` fica coberta indiretamente pelo RBAC de
  S-01; um teste dedicado de IDOR nesse endpoint seria um bônus (baixo risco).

**Encaminhamento:** S-02 concluída. Duas das quatro P0 fechadas (S-01, S-02).
Faltam **S-03** (HTTPS/HSTS) e **S-04** (validação de config) para o `@si` reauditar e
levantar o veto de pré-produção.

---

## QA — reconfirmação (@qadv `*qa 2`, 2026-08-29)

Já **Concluída/Aprovada** em 2026-08-28. Reexecutei o QA a pedido para confirmar
que as mudanças posteriores **não regrediram** a proteção IDOR — relevante porque
S-07 (auditoria) e S-09 (rate limit/upload) tocaram `certificado.baixar_documento`:

- `autorizar_recurso(dono_id=doc.assinante_id, permissoes=("certificado.usar",))`
  continua **antes** do `os.path.exists`/`send_file`; o hook de auditoria (S-07)
  foi inserido **depois** da autorização (acesso negado não gera log falso).
- `certificado.desativar` mantém `autorizar_recurso(dono_id=cert.usuario_id)`.
- `pytest tests/test_idor.py` → **6 passed** no codebase atual.

**Veredito mantido:** ✅ APROVADO. Sem novas ressalvas.
