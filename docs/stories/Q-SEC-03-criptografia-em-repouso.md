# Story Q-SEC-03 — Criptografia dos dados em repouso

**Épico:** Segurança ISO 27001 (FR-SEC-04) — Controle **A.8.24** (uso de criptografia)
**Prioridade:** P0
**Status:** A fazer
**Origem:** `docs/iso27001-gap-analysis.md`, consultoria do cliente (aprovado: 2 camadas)
**Branch:** `quiron`

---

## Contexto
Os dados de saúde trafegam sob TLS (S-03), mas **em repouso** o PostgreSQL fica em volume
Docker **sem cifra**. Se o disco/volume da VPS for copiado (ou em caso de ransomware/roubo),
os prontuários ficariam legíveis. **Decisão do cliente:** duas camadas — cifra de volume
(LUKS, infra) + cifra a nível de coluna para dados ultrassensíveis (aplicação).

## Descrição
Como **responsável pela segurança**, quero os dados sensíveis cifrados em repouso, para que
uma cópia do disco não exponha informações de saúde e documentos pessoais.

## Critérios de Aceite
- [ ] **Camada de aplicação (esta story entrega):** cifra a nível de coluna para campos
  ultrassensíveis (mínimo: `cpf`, `cns` do paciente; `totp_secret` do usuário; e demais
  campos definidos na implementação com o @si).
- [ ] Chave de criptografia via **env protegida** (`chmod 600`), nunca no código/repositório;
  procedimento de **rotação** documentado.
- [ ] Busca por campos cifrados continua funcionando (estratégia definida: cifra determinística
  para campos pesquisáveis como CPF/CNS, ou índice/hash de busca separado).
- [ ] **Camada de infra (documentada, executada na VPS):** cifra do volume do Postgres com LUKS,
  com procedimento em `docs/security/`.
- [ ] Migração converte os dados existentes para o formato cifrado sem perda.
- [ ] Testes: escrita/leitura de campo cifrado; busca por CPF/CNS; dado não legível em consulta crua ao valor bruto.

## Tarefas
1. Escolher mecanismo (avaliar `pgcrypto` no PG vs cifra na aplicação com `cryptography`).
   Recomendação inicial: cifra na aplicação (portável, chave fora do banco) com determinismo p/ campos pesquisáveis.
2. Camada de tipo/coluna cifrada reutilizável (ex.: `EncryptedType`/TypeDecorator do SQLAlchemy).
3. Aplicar aos campos ultrassensíveis; ajustar buscas que usam esses campos.
4. Gestão de chave: env + doc de guarda/rotação.
5. Migração de backfill (cifrar dados existentes).
6. Documentar LUKS na VPS (`docs/security/criptografia-repouso.md`).
7. Testes (`tests/test_criptografia_repouso.py`).

## Notas
- Trade-off de busca: campos cifrados de forma **não determinística** não são pesquisáveis
  diretamente — por isso CPF/CNS usam cifra determinística ou hash de busca. Alinhar com @si.
- Integra com Q-SEC-01 (o `totp_secret` deve nascer já cifrado).
- LUKS é passo de infra da VPS (fora do código) — entregamos o procedimento; a aplicação é a cifra de coluna.
