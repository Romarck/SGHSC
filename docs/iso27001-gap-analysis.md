# ISO/IEC 27001 — Gap Analysis e Plano de Adequação (QUÍRON)

**Data:** 2026-09-05
**Autor:** @po / @si (proposto para aprovação)
**Status:** 🟡 AGUARDANDO APROVAÇÃO
**Base:** ISO/IEC 27001:2022 (Anexo A) + consultoria fornecida pelo cliente
**Escopo:** controles **técnicos** aplicáveis ao produto QUÍRON (software + infra em VPS/Docker)

---

## 0. Nota importante sobre "ser ISO 27001"

Um software, isoladamente, **não é certificado ISO 27001**. A norma certifica a
**organização** e seu **SGSI** (Sistema de Gestão de Segurança da Informação) —
processos, políticas, pessoas, análise de risco e melhoria contínua. O que **este
projeto** pode (e vai) fazer é implementar os **controles técnicos do Anexo A** que
dependem do software e da infraestrutura, deixando o produto **auditável e aderente**
e removendo os bloqueios técnicos para uma futura certificação da organização.

As frentes puramente organizacionais (treinamento de equipe, gestão de fornecedores
de equipamentos médicos, política formal de SGSI, análise de risco documentada,
plano de continuidade testado) são **responsabilidade da operação/organização** —
este documento as sinaliza, mas o trabalho de engenharia entrega os controles técnicos.

---

## 1. Situação atual — o que o QUÍRON JÁ tem

A base v1.0 (stories de segurança S-01 a S-10) já cobre uma parte relevante:

| Já implementado | Evidência no código |
|-----------------|---------------------|
| Autenticação de sessão robusta (`session_protection="strong"`) | `extensions.py` |
| Hash de senha forte (Bcrypt) | `models/usuario.py` (property `senha`) |
| Bloqueio após 5 tentativas de login (anti-brute-force) | `Usuario.registrar_tentativa_falha` |
| Troca de senha obrigatória forçada globalmente | `__init__._forcar_troca_de_senha` |
| RBAC efetivo (`@requer_permissao`) em rotas sensíveis | `utils/authz.py` |
| Autorização a nível de objeto (anti-IDOR/BOLA) | `autorizar_recurso()` |
| Trilha de auditoria de acesso a dados de paciente (LGPD, append-only) | `models/auditoria.py` + `auditoria_service` |
| Política de retenção de logs (CLI de purga) | `purgar-auditoria` |
| CSRF global (Flask-WTF) | `extensions.py` |
| Rate limiting por rota (login/validação pública) | `extensions.py` + config |
| HTTPS/TLS 1.2+ + HSTS em produção | `nginx/conf.d/server-prod.conf.template` |
| Cabeçalhos de segurança (CSP, X-Frame-Options, nosniff, Referrer-Policy) | `nginx/conf.d/security-headers.conf` |
| Cookies de sessão `HTTPOnly` + `Secure`/`SameSite=Strict` em prod | `config.py` |
| Validação de config de produção (falha rápida sem segredos) | `config.ProductionConfig.validate` |
| Segredos apenas via env (`.env`), fora do código | `docker-compose.yml`, `config.py` |
| Isolamento de rede no Docker (redes internas, sem publicar portas) em prod | `docker-compose.prod.yml` |
| Assinatura digital PAdES/ICP-Brasil validada no backend + não-repúdio | `services/cert_service.py`, `models/certificado.py` |
| CI com lint (ruff) + testes (pytest) + migração + `pip-audit` | `.github/workflows/ci.yml` |
| SQL Injection mitigado (SQLAlchemy ORM, sem query concatenada) | padrão do projeto |
| XSS mitigado (auto-escape Jinja2) | padrão do projeto |

---

## 2. Gaps — o que falta ADOTAR (mapeado por controle do Anexo A)

Legenda de prioridade: **P0** (bloqueia go-live SAAS) · **P1** (importante) · **P2** (melhoria).

### A.8.2 / A.8.5 — Controle de acesso e autenticação segura

| Gap | Prioridade | Ação |
|-----|-----------|------|
| **2FA/MFA ausente** — hoje só usuário+senha | **P0** | Implementar TOTP (app autenticador) com `pyotp`; QR de enrollment; obrigatório ao menos para Super-Admin e Administradores; opcional/forçável por empresa |
| **Segregação de funções** já existe via RBAC, mas precisa validação formal por perfil (médico vê clínico; recepção vê cadastral) | P1 | Revisar matriz de permissões x perfil e documentar; cobrir com testes |
| Isolamento por tenant (Super-Admin sem dado clínico) | **P0** | Já previsto no plano multi-tenant (MT-2) — reforça A.8.3 |

### A.8.15 / A.8.16 — Logging e monitoramento

| Gap | Prioridade | Ação |
|-----|-----------|------|
| Trilha cobre acesso a paciente, mas **não** eventos de segurança (login sucesso/falha, criação/edição de usuário, mudança de permissão, cadastro/suspensão de empresa) | **P0** | Estender a auditoria para **eventos de segurança**; log estruturado |
| **Integridade da trilha ("logs invioláveis")** — hoje append-only por convenção, sem prova criptográfica | P1 | Encadeamento por **hash** (cada registro guarda hash do anterior — cadeia à prova de adulteração) e/ou export assinado; base para A.5.28 |
| Sem centralização/alerta (SIEM) | P1 (infra) | Enviar logs para arquivo estruturado + doc de integração com SIEM/host da VPS; alertas de tentativas de invasão |

### A.8.24 — Criptografia (em repouso)

| Gap | Prioridade | Ação |
|-----|-----------|------|
| **Dados em repouso não criptografados** — Postgres em volume Docker sem cifra | **P0** | Duas camadas: (a) **cifra de disco/volume** na VPS (LUKS) — infra; (b) **cifra a nível de coluna** para campos ultrassensíveis (ex.: CPF, CNS) com `pgcrypto` ou cifra na aplicação. Definir campos na implementação |
| Chaves de criptografia sem gestão formal | P1 | Documentar guarda de chave (env protegido/secret manager); rotação |

### A.8.20 / A.8.22 / A.8.23 — Segurança de redes e segregação

| Gap | Prioridade | Ação |
|-----|-----------|------|
| **`docker-compose.yml` (dev)** usa rede padrão e publica portas do banco/Flask | P1 | Redes `frontend`/`backend` separadas (nginx↔app, app↔db); nginx nunca fala com o banco. Em **prod** já está isolado |
| WAF ausente | P1 (infra) | Documentar WAF (ex.: no Caddy/Nginx com ModSecurity ou serviço gerenciado) na frente da VPS |
| Filtragem de saída / egress | P2 | Restringir egress do container app ao necessário (TSA, RNDS) |

### A.8.19 / A.8.31 — Ambientes e dados de dev/homologação

| Gap | Prioridade | Ação |
|-----|-----------|------|
| **Risco de dados reais em dev/homolog** | **P0** | Regra: **nunca** dados reais fora de produção. Melhorar `seed_demo.py` para dados 100% fictícios/mascarados; documentar; opção de **anonimização** de dump para homolog |

### A.8.25 – A.8.29 — Desenvolvimento seguro (DevSecOps)

| Gap | Prioridade | Ação |
|-----|-----------|------|
| CI tem lint + testes + `pip-audit`, mas **sem SAST** | **P1** | Adicionar **SAST** (`bandit` para Python) e **secret scanning** (`gitleaks`/`detect-secrets`) ao `ci.yml`; falhar build em achado |
| Sem DAST | P2 | Documentar DAST periódico (ex.: OWASP ZAP contra homolog) — pode ser manual no início |
| `| safe` / HTMX parciais sem sanitização explícita de texto livre | P1 | Sanitizar conteúdo livre (evoluções, anamnese) com **bleach** antes de render inseguro; revisar usos de `| safe` |
| Sem política de branch protegida/revisão obrigatória | P1 (processo) | Proteger `main` no GitHub (PR + revisão + CI verde). Já casa com o fluxo da branch `quiron` |

### A.5.29 / A.5.30 / A.8.13 — Continuidade e backup

| Gap | Prioridade | Ação |
|-----|-----------|------|
| **Backup geodistribuído automatizado ausente** — banco na mesma VPS | **P0** | Rotina (script/container) de `pg_dump` diário → **criptografado** → enviado para armazenamento externo (S3/GCS/outro provedor) isolado da VPS |
| Plano de Disaster Recovery não testado | P1 (processo) | Documentar RTO/RPO e procedimento de restore; teste periódico documentado |

### A.5.23 — Serviços em nuvem / responsabilidade compartilhada

| Gap | Prioridade | Ação |
|-----|-----------|------|
| Matriz de responsabilidade compartilhada não documentada | P1 (doc) | Documento: o que o provedor da VPS garante x o que é obrigação nossa (firewall, SO, patching, backup) |
| Acesso de gestão (SSH) sem endurecimento documentado | P1 (infra) | SSH só por chave (sem senha), porta fechada à internet pública / via VPN; documentar hardening |

### A.5.37 / A.8.32 — Procedimentos documentados e gestão de mudança

| Gap | Prioridade | Ação |
|-----|-----------|------|
| Falta um documento único de operação segura | P2 | Consolidar procedimentos (deploy, backup, restore, resposta a incidente) em `docs/security/` |

---

## 3. Frentes organizacionais (fora da engenharia — sinalizadas)

Estas são de responsabilidade da **organização/operação**, não resolvidas por código:

- Política formal do SGSI, escopo e declaração de aplicabilidade (SoA).
- Análise de risco formal documentada (metodologia, matriz, tratamento).
- Treinamento de equipe (uso seguro, engenharia social/phishing).
- Gestão de fornecedores (integradores de equipamentos médicos — tomografia, UTI).
- Gestão de incidentes (processo, comunicação à ANPD quando aplicável).

O QUÍRON dará **suporte técnico** a elas (ex.: trilha de auditoria alimenta a gestão
de incidentes; RBAC alimenta a segregação de funções), mas a governança é da operação.

---

## 4. Priorização consolidada (o que entra no desenvolvimento)

**P0 — antes do go-live do SAAS**
1. **2FA/TOTP** (A.8.5) — Super-Admin e Administradores.
2. **Auditoria de eventos de segurança** (A.8.15) — login, usuários, permissões, empresas.
3. **Criptografia em repouso** (A.8.24) — cifra de coluna para dados ultrassensíveis + orientação LUKS na VPS.
4. **Backup externo criptografado automatizado** (A.8.13) — `pg_dump` → cifra → nuvem externa.
5. **Sem dados reais fora de produção** (A.8.31) — seed fictício/anonimização.
6. **Isolamento de tenant** (A.8.3) — já no plano multi-tenant (MT-2).

**P1 — endurecimento**
7. SAST (`bandit`) + secret scanning (`gitleaks`) no CI (A.8.28).
8. Integridade da trilha por encadeamento de hash (A.5.28/A.8.15).
9. Sanitização com `bleach` em texto livre / revisão de `| safe` (A.8.28).
10. Redes Docker segregadas também em dev (A.8.22).
11. Proteção de branch `main` + revisão obrigatória (A.8.25).
12. Documentar responsabilidade compartilhada + hardening SSH/VPS (A.5.23).

**P2 — melhoria contínua**
13. WAF na frente da VPS; DAST periódico; documento único de operação segura.

---

## 5. Como isso entra no plano do QUÍRON

Estes controles serão executados como uma **trilha de segurança (fases SEC-x)** em
paralelo/depois das fases multi-tenant (MT-x), pois compartilham a mesma refatoração
(usuário, auditoria, config). Ver `docs/plano-quiron-multitenant.md` (seção atualizada)
e a tabela de rastreabilidade ISO em `docs/security/iso27001-controles.md` (a criar
na execução).

---

## 6. Histórico

| Data | Mudança | Autor |
|------|---------|-------|
| 2026-09-05 | Gap analysis inicial ISO 27001 a partir da consultoria + auditoria do código | @po/@si |
