# Story S-07 — Log de acesso a prontuário (trilha de auditoria LGPD)

**Épico:** Gestão e Compliance (NFR-03)
**Prioridade:** P1
**Status:** Concluído
**Origem:** @si M-04 (Médio)

---

## Contexto
Há logs de escrita (`criado_por_id`) e de login, mas **não há registro de leitura** de dados
de paciente. A LGPD (dado sensível de saúde) e as boas práticas de PEP recomendam registrar
**quem acessou qual prontuário e quando**. Além disso, `criado_por_id` é `nullable` na maioria
dos models, enfraquecendo a trilha.

## Descrição
Como **encarregado de dados (DPO)/gestor**, quero uma trilha de auditoria de acesso a
prontuários, para atender à LGPD e responder a solicitações de titulares e auditorias.

## Critérios de Aceite
- [x] Visualização/download de dado de paciente gera registro de auditoria (usuário, paciente, recurso, ação, timestamp, IP, user-agent). Instrumentados: `pacientes.detalhe`, `internacao.prontuario`, `internacao.baixar_laudo_alta`, `certificado.baixar_documento`.
- [x] Relatório "quem acessou o prontuário do paciente X" (e "o que o usuário Y acessou") em `/auditoria/`, protegido por `auditoria.ver`.
- [x] Escrita com autor confiável: `Paciente.criado_por_id` agora **NOT NULL** (preenchido do usuário logado).
- [x] Logs protegidos (append-only pela app; sem rota de edição/exclusão) e com **política de retenção** (`AUDITORIA_RETENCAO_DIAS=1825` + CLI `purgar-auditoria`).

## Tarefas
1. [x] Modelo `LogAcesso` (tabela `logs_acesso`) + `AcaoAuditoria`; registrado em `models/__init__`.
2. [x] Serviço `auditoria_service.registrar_acesso()` (resiliente) instrumentado nas 4 rotas de leitura/download.
3. [x] Blueprint `auditoria` + tela `auditoria/trilha.html` (por paciente e por usuário).
4. [x] `criado_por_id` NOT NULL (fluxo `pacientes.novo` já preenchia com `current_user.id`).
5. [x] Retenção + proteção documentadas em `docs/security/auditoria-lgpd.md`.

## Implementação (resumo @dev)
- `models/auditoria.py`: `LogAcesso` (usuario_id + snapshot username, paciente_id, acao, recurso/recurso_id, ip, user_agent, registrado_em) — indexado por paciente/usuário/data.
- `services/auditoria_service.py`: `registrar_acesso()` **nunca** quebra o request (captura exceção + rollback); `trilha_por_paciente/usuario`; `purgar_logs_vencidos()`.
- Hooks: `pacientes.detalhe`, `internacao.prontuario`, `internacao.baixar_laudo_alta`, `certificado.baixar_documento` (usa `doc.paciente_id`). O hook do download roda **após** a autorização (S-02), então acessos negados não geram log falso.
- `routes/auditoria.py` + template: consulta protegida por `auditoria.ver` (perfis Gestor e Administrador).
- `security/permissoes.py`: nova permissão `auditoria.ver` (catálogo + GESTOR).
- `config.py`: `AUDITORIA_RETENCAO_DIAS=1825`; CLI `flask purgar-auditoria`.

## Verificação
- `pytest`: **44 passed** (8 novos em `test_auditoria_lgpd.py` + 36 existentes, sem regressão).
- Cobertos: geração de log em visualização (com IP/paciente/usuário), múltiplos acessos, relatório por paciente (admin vê acesso da recep), 403 sem permissão, 302 anônimo, consulta por serviço, resiliência do serviço, `criado_por_id` NOT NULL.

## Notas / pendências para @qadv e @si
- **Migração em produção:** o `entrypoint.sh` roda `flask db migrate`/`upgrade` automaticamente. O projeto é **greenfield** (sem dados vivos), então o `criado_por_id` NOT NULL é seguro. Em base já povoada, o ALTER exigiria backfill antes — alinhar com **S-10** (migração segura).
- **Escopo de "dado sensível"** a validar com `@si`: cobri prontuário, cadastro do paciente e documento clínico assinado; exames/maternidade podem ser instrumentados em evolução.
- **Hardening do banco (produção):** conceder à app apenas INSERT/SELECT em `logs_acesso` (purga com papel separado) — documentado.
- Próximo passo: **@qadv `*qa 7`**.

---

## QA — @qadv (`*qa 7`)

**Resultado:** ✅ **APROVADO** na primeira rodada.

### Método
Revisão de código + suíte completa (independente) + **probes de borda** próprios,
incluindo um teste de resiliência mais forte do que o entregue.

### Evidências
| Critério | Verificação | Resultado |
|----------|-------------|-----------|
| Visualização/download gera log (usuário/paciente/ação/IP/UA) | `test_visualizar_paciente_gera_log` + hooks nas 4 rotas | ✅ |
| Relatório "quem acessou o paciente X" | `/auditoria/?paciente_id=` (admin vê acesso da recep) | ✅ |
| Relatório protegido | 403 sem `auditoria.ver`; 302 anônimo | ✅ |
| Escrita com autor confiável | `Paciente.criado_por_id` NOT NULL | ✅ |
| Append-only + retenção | sem rota de edição/exclusão; `AUDITORIA_RETENCAO_DIAS` + CLI `purgar-auditoria` | ✅ |
| Regressão | suíte completa | **44 passed** |

### Probes adicionais do @qadv (além dos testes do @dev)
1. **Resiliência real:** forçando exceção dentro de `registrar_acesso` (não só o
   caminho "sem usuário"), a rota `/pacientes/<id>` ainda respondeu **200** e nada
   propagou. Cobre a lacuna do teste original, que só exercitava o early-return.
2. **403 não gera log falso:** download negado a quem não tem `certificado.usar`/
   não é dono → 403 **sem** criar registro de auditoria (hook após a autorização).
3. **404 não gera log:** internação inexistente → 404 antes do audit, sem registro.

### Observações (não bloqueantes)
- **Proteção do log** é append-only por convenção da app; o enforcement forte
  (grants INSERT/SELECT-only, WORM/pgaudit) é tarefa de **deploy/DBA**, corretamente
  documentada em `docs/security/auditoria-lgpd.md`. Aceitável no escopo da story.
- **`criado_por_id` NOT NULL** é seguro por ser greenfield; em base povoada exigiria
  backfill — já sinalizado para **S-10**.
- **Escopo de "dado sensível"**: cobre prontuário/cadastro/documento assinado;
  exames e maternidade podem ser instrumentados em evolução — **alinhar com @si**.
