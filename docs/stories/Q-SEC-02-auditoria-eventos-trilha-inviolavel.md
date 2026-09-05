# Story Q-SEC-02 — Auditoria de eventos de segurança + trilha inviolável

**Épico:** Segurança ISO 27001 (FR-SEC-02/03) — Controles **A.8.15** (logging) e **A.5.28** (coleta de evidências)
**Prioridade:** P0
**Status:** A fazer
**Origem:** `docs/iso27001-gap-analysis.md`, consultoria do cliente
**Branch:** `quiron`
**Depende de:** Q-MT-00 (usuário/empresa), complementa a S-07 (auditoria LGPD existente)

---

## Contexto
A trilha atual (`LogAcesso`, S-07) cobre **acesso a dados de paciente**. A ISO 27001 (A.8.15)
exige registrar também **eventos de segurança** (login, gestão de usuários/permissões,
gestão de empresas). Além disso, a norma valoriza **logs invioláveis** — hoje a trilha é
append-only por convenção, sem prova criptográfica de não-adulteração.

## Descrição
Como **auditor/DPO**, quero uma trilha completa de eventos de segurança, resistente a
adulteração, para investigação de incidentes e conformidade.

## Critérios de Aceite
- [ ] Eventos de segurança registrados: login (sucesso/falha), logout, bloqueio por tentativas,
  troca de senha, ativação/uso de 2FA, CRUD de usuário, mudança de perfil/permissão,
  cadastro/edição/mudança de status de empresa.
- [ ] Registro estruturado (quem, o quê, quando, IP, user-agent, empresa quando aplicável).
- [ ] **Trilha inviolável:** cada registro guarda o **hash do registro anterior**
  (encadeamento tipo cadeia) — qualquer alteração/remoção no meio quebra a cadeia e é detectável.
- [ ] Comando de **verificação de integridade** da cadeia (`flask verificar-auditoria`) que
  aponta o ponto de quebra, se houver.
- [ ] Append-only mantido (sem rota de edição/exclusão; purga só pela CLI de retenção, que
  preserva a verificabilidade ou registra o corte).
- [ ] Escopo por tenant: eventos de empresa ficam vinculados à empresa; eventos de Super-Admin também são logados.
- [ ] Testes: geração de eventos, encadeamento de hash, detecção de adulteração, verificação de integridade.

## Tarefas
1. Estender a auditoria: `LogSeguranca` (ou ampliar `AcaoAuditoria`) para eventos de segurança.
2. Instrumentar os pontos: `auth.py` (login/logout/senha/2FA), `usuarios`, `perfis`, `admin_saas`.
3. Encadeamento por hash (SHA-256 do registro atual + hash do anterior) no serviço de auditoria.
4. CLI `verificar-auditoria` (percorre a cadeia e valida).
5. Ajustar a política de retenção/purga para não invalidar a verificação indevidamente.
6. Testes (`tests/test_auditoria_seguranca.py`).

## Notas
- Reusar `services/auditoria_service.py` e o padrão resiliente da S-07 (auditoria nunca quebra o request).
- Integridade forte a nível de banco (grants, pgaudit/WORM) é hardening de DBA — documentar; aqui entregamos a cadeia de hash na aplicação.
- Não-repúdio de documentos clínicos (assinatura PAdES) já existe; esta story cobre a trilha operacional.
