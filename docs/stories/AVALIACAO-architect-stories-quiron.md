# Avaliação Arquitetural — Stories QUÍRON (Q-MT-* / Q-SEC-*)

**Data:** 2026-09-05
**Autor:** @architect
**Comando:** `*review` (avaliação de backlog)
**Objeto:** `docs/stories/Q-MT-00..05`, `Q-SEC-01..07`, `README-quiron.md`
**Base de verificação:** código real (`app/routes/auth.py`, `models/usuario.py`, `models/paciente.py`, `utils/authz.py`, `config.py`, `extensions.py`, migrations)

---

## Veredito

**APROVADO COM RESSALVAS.** O backlog é coerente, bem particionado e alinhado ao
`plano-quiron-multitenant.md`, ao PRD v2.0 e ao gap analysis ISO. A abordagem de
multi-tenancy (coluna discriminadora + isolamento na camada de dados) é a escolha correta
para este monólito Flask (ADR-003) e o custo/benefício é adequado ao público.

Há, porém, **8 ajustes** a incorporar antes/durante a execução — 3 deles **bloqueantes**
(B) porque tocam correção do isolamento ou dependências invertidas, e 5 recomendações (R).

---

## Pontos fortes

- **Isolamento na camada de dados, não por rota** (Q-MT-02): decisão acertada. Confiar em
  154 rotas lembrarem do `.filter(empresa_id=...)` é frágil; o mixin + event listener é o
  padrão certo.
- **Fatiamento incremental** com app subindo a cada fase e Pedralva como backfill — reduz risco.
- **Separação Super-Admin sem `empresa_id`** e sem queries de negócio: bom para privacidade/LGPD.
- **2FA restrito a papéis privilegiados**: decisão pragmática para estações compartilhadas.
- **Cobertura ISO** por controle do Anexo A, com honestidade sobre o que é app x infra.

---

## Ressalvas bloqueantes (B)

### B1 — Login não tem como resolver o tenant depois que `username` deixa de ser único global
**Onde:** Q-MT-01 (unicidade composta) vs Q-MT-03/`auth.py`.
**Fato no código:** `auth.login` faz `Usuario.query.filter_by(username=...).first()`. Ao
tornar `username` único **por empresa** (`(empresa_id, username)`), esse filtro fica
**ambíguo** (pode haver `admin` em N empresas) e o login quebra ou loga o usuário errado.
**Ação:** decidir e documentar a **estratégia de identificação do tenant no login**. Opções:
- (a) **e-mail global único** como credencial de login (mantém `username` cosmético por empresa);
- (b) campo/slug da empresa na tela de login;
- (c) host/subdomínio por tenant (hoje **fora de escopo** no plano).
Recomendo **(a)** para o MVP (menor atrito, sem subdomínio). Deve entrar como critério de
aceite explícito em **Q-MT-01** e no fluxo de **Q-MT-03**. Hoje nenhuma story trata disso.

### B2 — Dependência invertida entre Q-SEC-01 (2FA) e Q-SEC-03 (criptografia)
**Onde:** README ordena Q-SEC-01 (#2) antes de Q-SEC-03 (#6), mas Q-SEC-01 exige
`totp_secret` **cifrado** e a própria Q-SEC-03 diz "o `totp_secret` deve nascer cifrado".
**Ação:** inverter a ordem — **Q-SEC-03 (tipo de coluna cifrada) antes de Q-SEC-01**, ou
implementar o `EncryptedType` como um pré-requisito compartilhado no início. Sem isso, a
Q-SEC-01 entrega um segredo TOTP em claro no banco — o oposto do objetivo ISO.

### B3 — Comportamento do filtro automático fora do contexto de request
**Onde:** Q-MT-02 (event listener usando `g.empresa_id`).
**Fato no código:** há caminhos que rodam **sem request**: `entrypoint.sh` (seed do admin,
`seed_permissoes`), CLIs (`purgar-auditoria`), **migrations** (backfill da Pedralva) e testes.
Se o listener filtra por `g.empresa_id` e `g` não existe, o comportamento é indefinido
(pode filtrar por `None` e "sumir" com dados, ou vazar). A story cita a preocupação nas
"Notas", mas **não a eleva a critério de aceite**.
**Ação:** definir política explícita e testá-la: **sem tenant no contexto → a query exige
escopo explícito (`unscoped()`/escopo manual) ou falha alto (erro), nunca filtra por `None`
silenciosamente.** Adicionar critério de aceite e teste em Q-MT-02 cobrindo seed/CLI/migração.

---

## Recomendações (R) — não bloqueiam, mas devem ser incorporadas

### R1 — Login multi-etapas (senha → TOTP) e `session_protection="strong"`
**Onde:** Q-SEC-01.
`login_user()` só deve ocorrer **após** o 2º fator. O estado intermediário ("usuário passou
na senha, aguarda TOTP") precisa ser guardado com cuidado (sessão temporária), e o rate
limit do login (S-09) deve cobrir também a etapa de verificação do código. Tornar isso
critério de aceite evita uma implementação que autentica antes do 2º fator.

### R2 — `criado_por_id` NOT NULL e a migração da Pedralva
**Onde:** Q-MT-01.
Vários models têm `criado_por_id`/`aberto_por_id`. Ao criar a empresa e o backfill, garanta
a ordem: empresa → usuários (recebem `empresa_id`) → demais tabelas. O backfill de `empresa_id`
deve ser transacional e idempotente (a S-07/S-10 já estabeleceram o cuidado com NOT NULL em
base povoada — reaproveitar a lição).

### R3 — Escopo de tabelas com `empresa_id`: decidir catálogos SIGTAP/CBHPM
**Onde:** Q-MT-01 (o plano marca esses catálogos como "a avaliar").
Recomendo **por-empresa** (tabelas de preço/procedimento variam por contrato), mas isso
precisa ser **decidido** antes da migração, não durante. Fixar na story.

### R4 — Índices e performance do filtro de tenant
**Onde:** Q-MT-01/Q-MT-02.
Todo `empresa_id` deve ser **indexado**, e os índices compostos existentes (ex.: buscas por
nome/CPF/CNS em `pacientes`) devem passar a **liderar por `empresa_id`** (`(empresa_id, nome)`),
senão o filtro automático degrada as buscas. Adicionar como critério de aceite (NFR-07, p95 < 2s).

### R5 — ADR-007 deve ser pré-requisito, não item de encerramento
**Onde:** hoje o ADR-007 aparece só na Q-MT-05 (fechamento).
A decisão de multi-tenancy é **estruturante**; o ADR deve ser escrito **no início** (junto da
Q-MT-00) para congelar a decisão antes do código, e apenas *revisado* na Q-MT-05.

---

## Conformidade com o restante da arquitetura

- **ADR-001 (Jinja2/HTMX):** Chart.js via CDN (Q-MT-04) respeita o estilo server-side e a CSP
  da S-09 — coerente. Sem SPA. OK.
- **ADR-003 (monólito):** multi-tenant por coluna preserva o monólito — OK; ADR-007 deve
  referenciar e não contradizer o ADR-003.
- **ADR-005 (sessão + RBAC):** o eixo de tenant é **ortogonal** ao RBAC — bem modelado.
  Atenção ao fluxo de sessão no 2FA (R1).
- **S-07 (auditoria):** Q-SEC-02 estende corretamente; `logs_acesso` recebendo `empresa_id`
  (citado na Q-MT-01) é coerente.

---

## Estimativa de complexidade (relativa)

| Story | Complexidade | Risco |
|-------|-------------|-------|
| Q-MT-00 | Média | Baixo |
| Q-MT-01 | **Alta** | **Alto** (migração de dados + uniques + índices) |
| Q-MT-02 | **Alta** | **Crítico** (isolamento; furo B3) |
| Q-MT-03 | Média | Médio (login/tenant — B1) |
| Q-MT-04 | Baixa-Média | Baixo |
| Q-SEC-01 | Média | Médio (fluxo de sessão — R1; dep. B2) |
| Q-SEC-02 | Média | Médio (encadeamento de hash + purga) |
| Q-SEC-03 | **Alta** | Alto (busca em campo cifrado; chave/rotação) |
| Q-SEC-04 | Média | Médio (infra/ops) |
| Q-SEC-05 | Baixa | Baixo |
| Q-SEC-06 | Baixa-Média | Baixo |
| Q-SEC-07 | Média | Médio (ops) |

---

## Ordem recomendada (ajustada) para as ressalvas

1. **Q-MT-00** + **ADR-007** (R5) + **tipo de coluna cifrada / base da Q-SEC-03** (B2).
2. **Q-MT-01** (com B1 decidido, R2, R3, R4).
3. **Q-MT-02** (com B3 como critério de aceite/teste).
4. **Q-SEC-01** (com R1) — agora que a cifra de coluna existe.
5. **Q-SEC-02**, **Q-MT-03**, **Q-MT-04**, demais Q-SEC, **Q-MT-05** (merge).

---

## Encaminhamento

Recomendo ao **@po** incorporar B1, B2 e B3 como **critérios de aceite** nas stories
correspondentes (Q-MT-01, Q-SEC-01/03, Q-MT-02) e mover o ADR-007 para o início. Com esses
ajustes, o backlog está pronto para execução. O **@si** deve revisar especificamente a
Q-MT-02 (isolamento) e a Q-SEC-03 (criptografia/chaves) antes do go-live.

---

## Histórico

| Data | Mudança | Autor |
|------|---------|-------|
| 2026-09-05 | Avaliação inicial do backlog Q-* | @architect |
