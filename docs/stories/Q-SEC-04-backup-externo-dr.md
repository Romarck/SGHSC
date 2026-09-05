# Story Q-SEC-04 — Backup externo criptografado + Disaster Recovery

**Épico:** Segurança ISO 27001 (FR-SEC-05) — Controles **A.8.13** (backup), **A.5.29/A.5.30** (continuidade/prontidão TIC)
**Prioridade:** P0
**Status:** A fazer
**Origem:** `docs/iso27001-gap-analysis.md`, consultoria do cliente
**Branch:** `quiron`

---

## Contexto
Aplicação e banco compartilham a mesma VPS. Um ransomware ou perda da VPS destruiria os dois
juntos. Não há hoje backup **externo** automatizado. A ISO 27001 (A.8.13/A.5.29-30) exige
backup e capacidade de recuperação — e um hospital não pode parar.

## Descrição
Como **operador do SAAS**, quero backups diários automáticos, criptografados e armazenados
fora da VPS, com procedimento testado de restauração, para sobreviver a um desastre.

## Critérios de Aceite
- [ ] Rotina automatizada (script/container) de **`pg_dump` diário** do PostgreSQL.
- [ ] Dump **criptografado** antes de sair da VPS (chave/pass fora do repositório).
- [ ] Envio automático para **armazenamento externo isolado** da VPS (S3/GCS/compatível), configurável por env.
- [ ] Política de retenção do backup (ex.: diários por N dias, semanais por M semanas).
- [ ] Procedimento de **restore** documentado e **testado** (restaurar dump cifrado em ambiente limpo).
- [ ] Documento de **Disaster Recovery** com RTO/RPO alvo e passo a passo.
- [ ] Verificação de sucesso do backup (log/alerta em caso de falha).

## Tarefas
1. Script de backup (`ops/backup/` ou serviço no compose): `pg_dump` → cifra (gpg/openssl) → upload (aws-cli/rclone).
2. Agendamento (cron no host ou container agendador) — documentar a opção adotada.
3. Configuração por env (destino, credenciais do bucket, chave de cifra) com segredos protegidos.
4. Retenção e verificação/alerta de falha.
5. `docs/security/backup-dr.md`: procedimento de restore + DR (RTO/RPO) + teste.
6. Teste de restauração ponta a ponta (registrar evidência).

## Notas
- Credenciais do bucket e chave de cifra **nunca** no repositório — env/secret protegido na VPS.
- Isolamento do destino: idealmente **outro provedor/região** para não cair junto com a VPS.
- Complementa o `docker-compose.prod.yml` (VPS) sem publicar portas novas.
