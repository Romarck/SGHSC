# Story Q-SEC-07 — Hardening de infraestrutura e rastreabilidade de controles ISO

**Épico:** Segurança ISO 27001 (NFR-ISO-05) — Controles **A.5.23** (nuvem), **A.8.20/A.8.22** (redes/segregação)
**Prioridade:** P1
**Status:** A fazer
**Origem:** `docs/iso27001-gap-analysis.md`, consultoria do cliente
**Branch:** `quiron`

---

## Contexto
Em produção o `docker-compose.prod.yml` já isola redes e não publica portas. Faltam melhorias
no **dev** (redes segregadas), o hardening documentado da VPS (SSH, firewall, WAF) e a
matriz de **responsabilidade compartilhada** com o provedor. Fecha os pontos de infra da ISO.

## Descrição
Como **operador da VPS**, quero o ambiente endurecido e os controles ISO rastreados, para
reduzir a superfície de ataque e demonstrar conformidade.

## Critérios de Aceite
- [ ] `docker-compose.yml` (dev) com **redes segregadas** (`frontend`: nginx↔app; `backend`: app↔db);
  o nginx não fala diretamente com o banco.
- [ ] **Usuário não-root** no container da app (`Dockerfile`: cria `appuser` e usa `USER appuser`),
  validando que a aplicação e o entrypoint funcionam sem root.
- [ ] `.env` com permissão restrita documentada (`chmod 600`) e fora do versionamento (já em `.gitignore` — confirmar).
- [ ] Documento de **responsabilidade compartilhada** (provedor x nós): firewall, SO, patching, backup, física.
- [ ] **Hardening SSH** documentado: acesso só por chave (sem senha), porta fechada à internet/via VPN, fail2ban.
- [ ] **WAF** na frente da VPS documentado (ex.: ModSecurity no proxy, ou serviço gerenciado).
- [ ] **Tabela de rastreabilidade** `docs/security/iso27001-controles.md`: controle do Anexo A →
  onde está implementado (código/config/doc) → status.

## Tarefas
1. Redes segregadas no `docker-compose.yml` (dev), preservando o funcionamento atual.
2. `Dockerfile`: usuário não-root (`appuser`), ajustar permissões de `entrypoint.sh`/pastas de runtime.
3. Confirmar `.gitignore` do `.env` e documentar `chmod 600`.
4. `docs/security/responsabilidade-compartilhada.md` e `docs/security/hardening-vps.md` (SSH/firewall/WAF).
5. `docs/security/iso27001-controles.md` — matriz de rastreabilidade consolidando S-01..S-10 + Q-SEC-01..07.
6. Validar app subindo com as mudanças (dev e prod).

## Notas
- Alguns itens (SSH, WAF, firewall da VPS) são **operacionais** — entregamos configuração de referência e documentação; a aplicação na VPS é passo de deploy.
- A matriz de rastreabilidade é o artefato que amarra tudo para uma futura auditoria/certificação da organização.
