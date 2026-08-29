# Trilha de Auditoria de Acesso (LGPD) — Story S-07

**Agente:** @dev · **Origem:** @si M-04 · **Base legal:** LGPD (accountability / art. 37)

Registra **quem acessou qual prontuário/dado de paciente, quando e de onde**,
atendendo ao princípio da responsabilização para dados sensíveis de saúde.

---

## O que é registrado

Modelo `LogAcesso` (tabela `logs_acesso`), um registro por evento:

| Campo | Descrição |
|-------|-----------|
| `usuario_id` / `usuario_username` | quem acessou (id + snapshot do login) |
| `paciente_id` | paciente cujos dados foram acessados (quando aplicável) |
| `acao` | `visualizar`, `baixar_documento`, `exportar` |
| `recurso` / `recurso_id` | rota/objeto acessado (ex.: `internacao.prontuario#42`) |
| `ip` / `user_agent` | contexto de rede da requisição |
| `registrado_em` | timestamp UTC (indexado) |

### Pontos instrumentados (leitura de dado sensível)
- `pacientes.detalhe` — visualização dos dados do paciente + resumo do prontuário.
- `internacao.prontuario` — visualização do prontuário clínico da internação.
- `internacao.baixar_laudo_alta` — download do laudo de alta (PDF).
- `certificado.baixar_documento` — download de documento clínico assinado.

O registro é **resiliente**: se a gravação da auditoria falhar, o request principal
não é interrompido (o erro é apenas logado). Ver `services/auditoria_service.py`.

---

## Consulta da trilha

Tela protegida por permissão `auditoria.ver` (perfis **Gestor** e **Administrador**):

- `GET /auditoria/?paciente_id=<id>` — "quem acessou o prontuário do paciente X".
- `GET /auditoria/?usuario_id=<id>` — "o que o usuário Y acessou".

---

## Trilha de escrita

`Paciente.criado_por_id` passou a ser **NOT NULL** (preenchido a partir do usuário
autenticado em `pacientes.novo`), fortalecendo a rastreabilidade de autoria das
operações de escrita feitas por usuário logado.

---

## Proteção e retenção

**Proteção (append-only):** a aplicação apenas **insere** em `logs_acesso`. Não há
rota nem serviço para editar ou apagar registros individuais. Recomendações de
hardening no banco (produção):
- Conceder ao usuário da aplicação apenas `INSERT`/`SELECT` na tabela `logs_acesso`
  (sem `UPDATE`/`DELETE`); a purga de retenção roda com um papel administrativo
  separado (via CLI/rotina, não pela app).
- Considerar `pgaudit` / WORM/backup imutável para retenção legal reforçada.

**Retenção:** padrão de **1825 dias (5 anos)** via `AUDITORIA_RETENCAO_DIAS`
(ajustável pelo DPO/jurídico). Purga em bloco dos registros vencidos:

```bash
flask purgar-auditoria
```

Agende (cron/rotina) conforme a política definida. A purga é a **única** operação
de remoção prevista e não é exposta à aplicação comum.

---

## Escopo de "dado sensível" (alinhar com @si)

Incluídos nesta entrega: prontuário clínico, dados cadastrais do paciente e
documentos clínicos assinados. Evoluções futuras podem instrumentar exames,
maternidade e demais visualizações que exponham dado de saúde.
