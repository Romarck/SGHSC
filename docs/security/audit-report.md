# Relatório de Auditoria de Segurança — SGHSC

**Agente:** @si (Segurança & Compliance)
**Comando:** `*audit-code` (7 fases)
**Data:** 2026-08-28
**Tipo de projeto:** greenfield · Sistema de Gestão Hospitalar
**Escopo de compliance:** LGPD + normas de saúde (CFM/PEP, ANVISA).
**Fora de escopo (por decisão do solicitante):** BCB 85/2021, FEBRABAN/CNAB, B3/CVM —
não se aplicam; o sistema não processa dados bancários, pagamentos ou mercado de capitais.

---

## Parecer geral

> ⚠️ **RESSALVAS — pode prosseguir com plano de correção, mas NÃO liberado para produção
> com dados reais de pacientes até que os achados CRÍTICOS/ALTOS sejam resolvidos.**

O código é limpo em várias frentes clássicas (sem SQL injection, sem `eval/exec`, sem SSTI,
Jinja2 com autoescape íntegro, senhas com Bcrypt, CSRF global, `.gitignore` protege segredos
e certificados). Os riscos concentram-se em **autorização (RBAC não aplicado)**, **transporte
sem HTTPS**, **segredos/validação de produção** e **dependências desatualizadas com CVEs**.

**Contagem de achados:** 1 Crítico · 5 Altos · 4 Médios · 3 Baixos/Informativos.

---

## Fase 1 — Autenticação e Gestão de Sessão

**Analisado:** `routes/auth.py`, `models/usuario.py`, `extensions.py`, `config.py`.

Pontos fortes:
- Bcrypt para hash de senha (property `senha`, sem armazenar texto puro).
- `login_manager.session_protection = "strong"`; cookie `HTTPOnly`.
- Bloqueio de conta após 5 tentativas por 30 min; desbloqueio automático após o prazo.
- Troca de senha obrigatória no 1º acesso; mínimo de 8 caracteres.
- Log de tentativas de login (sucesso, falha, usuário inexistente).
- Mensagem de erro genérica ("Usuário ou senha inválidos") — bom contra enumeração...

Achados:
- **[ALTO] A-01 — Cookie de sessão sem `Secure` fora de produção + HTTPS desativado.**
  `SESSION_COOKIE_SECURE=True` só em `ProductionConfig`, e o bloco HTTPS do Nginx está
  comentado. Sem TLS, a sessão trafega em claro (interceptação em rede hospitalar).
- **[MÉDIO] M-01 — Contador de tentativas revela existência do usuário.** A mensagem de
  senha incorreta inclui "Tentativas restantes: N", só emitida para usuário existente.
  Mitiga parcialmente o benefício da mensagem genérica. Recomenda-se não expor o contador.
- **[MÉDIO] M-02 — Política de senha fraca.** Apenas comprimento ≥ 8; sem exigência de
  complexidade, verificação contra senhas comuns ou rotação. Para dados de saúde, elevar.
- **[BAIXO] B-01 — `remember me` com cookie persistente** sob sessão de 8h; avaliar o
  impacto em estações compartilhadas (hospital).

---

## Fase 2 — Autorização e Controle de Acesso

**Analisado:** todas as rotas em `app/routes/`, `models/usuario.py` (RBAC).

- **[CRÍTICO] C-01 — RBAC modelado mas NÃO aplicado.** O modelo
  `Usuario→Perfil→Permissao` e o método `tem_permissao()` existem, porém **não há uma única
  chamada** a `tem_permissao` nas rotas (verificado por varredura). Todas as rotas usam
  apenas `@login_required`. **Consequência:** qualquer usuário autenticado (ex.: recepção)
  pode acessar prescrição médica, alta, faturamento, RH e financeiro. Viola o princípio do
  menor privilégio e o sigilo profissional do prontuário.
  **Remediação:** criar decorator `@requer_permissao("modulo.acao")` e aplicá-lo; semear
  as `Permissao` por perfil. **Bloqueia produção com dados reais.**
- **[ALTO] A-02 — IDOR/BOLA em downloads e recursos por id.** Rotas como
  `/internacao/<id>/alta/pdf`, `/certificado/documento/<id>/pdf` usam `get_or_404(id)` sem
  verificar se o `current_user` tem vínculo/permissão sobre aquele paciente/documento. Um
  usuário logado pode baixar o laudo de qualquer paciente iterando o `id`.
  **Remediação:** validar propriedade/permissão antes de `send_file` (nota: `desativar`
  certificado já faz a checagem `cert.usuario_id != current_user.id` — replicar o padrão).

---

## Fase 3 — Validação de Entrada e Injeções

**Analisado:** rotas, formulários Flask-WTF, uso de ORM, templates.

- **SQL Injection:** não encontrado. Todo acesso a dados é via SQLAlchemy ORM
  (`filter_by`, `query`, `get_or_404`) — parametrizado. Nenhum `execute()`/`text()` cru.
- **XSS:** Jinja2 com **autoescape ativo**; nenhum uso de `|safe` nem
  `render_template_string`. Baixo risco de XSS refletido/armazenado via templates.
- **Execução de código:** nenhum `eval`/`exec`/`pickle`/`subprocess`/`os.system`.
- **[MÉDIO] M-03 — Upload de certificado sem limite de tamanho explícito na rota e sem
  verificação de conteúdo além da extensão.** `routes/certificado.py::upload` valida só a
  extensão (`.p12/.pfx`) e salva antes de inspecionar. Há `MAX_CONTENT_LENGTH=16MB` global
  (bom), mas convém validar o `Content-Type`, salvar em área temporária e mover só após a
  inspeção bem-sucedida (hoje remove após falha — aceitável, porém melhorável).
- **[BAIXO] B-02 — Nome de arquivo de upload.** Usa `secure_filename` (bom); mantém o nome
  original do usuário no path — preferir nome totalmente gerado (uuid) para evitar colisões
  e vazamento de informação no filesystem.

**Path traversal:** os dois `send_file` (`main.py` guia estático; `internacao.py` e
`certificado.py` por id) usam caminhos **controlados pelo servidor** (config/DB), não
entrada do usuário — sem traversal explorável. (Ver A-02 para o problema de autorização.)

---

## Fase 4 — Proteção de Dados (em trânsito e em repouso) — foco LGPD

**Dados pessoais sensíveis** (art. 5º, II da LGPD): dados de saúde de pacientes — prontuário,
diagnósticos (CID-10), prescrições, exames, dados de RN/parto, CPF/CNS.

- **[ALTO] A-03 — Sem criptografia em trânsito.** HTTPS/HSTS comentado no Nginx (ver A-01).
  Dado de saúde exige TLS obrigatório. **Ação:** ativar 443 + redirect 80→443 + HSTS antes
  de produção.
- **[ALTO] A-04 — Dados em repouso sem criptografia adicional.** Prontuário e documentos
  ficam em PostgreSQL/volume e PDFs no filesystem sem criptografia de coluna/disco. Para
  LGPD/saúde, avaliar criptografia de disco (volume) e/ou de campos sensíveis, além de
  backup cifrado.
- **[MÉDIO] M-04 — Ausência de trilha de auditoria de acesso (quem leu o quê).** Há
  `criado_por_id`/logs de escrita e de login, mas não há registro de **leitura** de
  prontuário (acesso a dados de paciente). A LGPD e as boas práticas de PEP recomendam log
  de acesso a dado sensível. `criado_por_id` é `nullable` na maioria dos models — reduz a
  força da trilha.
- **Bom:** certificado e `.env` estão no `.gitignore`; senha de certificado não é persistida.

---

## Fase 5 — Dependências (SCA)

**Analisado:** `requirements.txt` (versões pinadas — boa prática). CVEs relevantes para as
versões fixadas (referências ao final; conteúdo reformulado para conformidade de licença):

| Pacote | Versão fixada | Achado | Severidade |
|--------|---------------|--------|------------|
| Werkzeug | 3.1.3 | Path traversal em `safe_join` (nomes reservados do Windows), corrigido em 3.1.4 — [CVE-2025-66221](https://www.sentinelone.com/vulnerability-database/cve-2025-66221/) | ALTO |
| Flask | 3.1.1 | Assinatura de sessão com chave de fallback obsoleta (impacta quem usa `SECRET_KEY_FALLBACKS`) — [CVE-2025-47278](https://www.sentinelone.com/vulnerability-database/cve-2025-47278/); e info disclosure `Vary: Cookie` — [CVE-2026-27205](https://www.sentinelone.com/vulnerability-database/cve-2026-27205/) | MÉDIO |
| cryptography | 43.0.3 | Buffer overflow com buffers não contíguos — [CVE-2026-39892](https://github.com/advisories/GHSA-p423-j2cm-9vmq) | ALTO |
| Pillow | 11.1.0 | Série de CVEs corrigidos em 12.x (ex.: execução de código local [CVE-2025-48379](https://access.redhat.com/security/cve/cve-2025-48379)) | MÉDIO |

- **[ALTO] A-05 — Atualizar Werkzeug (≥3.1.4) e cryptography** para versões corrigidas.
- **[MÉDIO] M-05 (agrupado)** — Atualizar Flask e Pillow; revisar cadeia pyHanko.
- **Recomendação:** adotar varredura automática contínua (`pip-audit`/Dependabot) no CI
  (`@si *scan-deps` semanal, conforme `security-first.md`).

> Não foram identificados indícios de **pacote malicioso/typosquatting** — todos são
> bibliotecas conhecidas e amplamente usadas.

---

## Fase 6 — Segredos e Configuração

**Analisado:** `config.py`, `.env.example`, `entrypoint.sh`, `docker-compose.yml`.

- **[ALTO] A-06 — `SECRET_KEY` com fallback fraco hardcoded** (`"troque-antes-de-produção"`)
  e `ProductionConfig.validate()` **nunca é chamado** no factory. Em produção mal
  configurada, a chave fraca permanece — compromete a assinatura da sessão (agravado por
  CVE-2025-47278).
  **Ação:** invocar `ProductionConfig.validate()` em `create_app` quando
  `FLASK_ENV=production` (falhar rápido sem `SECRET_KEY`/`DATABASE_URL`/`POSTGRES_PASSWORD`).
- **[MÉDIO] M-06 — Admin seed com senha fixa `Admin@123`** no `entrypoint.sh`. Aceitável
  como bootstrap porque `deve_trocar_senha=True`, mas é previsível; documentar e garantir a
  troca imediata; evitar em ambientes expostos.
- **Bom:** `entrypoint.sh` não permite certificado de teste em produção (checa `current_app.debug`
  na rota `gerar-teste`); segredos vêm de env vars; `.env` fora do git.
- **[INFO] I-01 — `flask db migrate` no boot.** O `entrypoint.sh` roda `migrate` automático
  no start — risco de migração não revisada em produção. Usar apenas `upgrade` em produção.

---

## Fase 7 — Exposição de Rede e Superfície Externa

**Analisado:** blueprints, rota pública, chamadas externas.

- **Endpoints externos de saída:** TSA (`CERT_TIMESTAMP_URL`, Safeweb) para carimbo de
  tempo — com degradação graciosa; ViaCEP (lado cliente). Não há exfiltração de dados de
  paciente para terceiros. RNDS é stub (sem transmissão real).
- **[MÉDIO] M-07 — Rota pública `/certificado/validar/<codigo>` sem rate limiting.** Correta
  em não exigir login (destino do QR), mas o `codigo` (`secrets.token_hex(8)` = 64 bits, bom)
  merece **rate limiting** para evitar enumeração e garantir que a página exponha apenas o
  mínimo (evitar PII clínica desnecessária — LGPD).
- **[BAIXO] B-03 — Nginx:** `server_tokens off` (bom); falta cabeçalhos de segurança no
  bloco ativo (CSP, `X-Content-Type-Options`, `X-Frame-Options`) — presentes só no bloco
  HTTPS comentado.

---

## Resumo dos achados e plano de remediação

| ID | Sev. | Achado | Fase | Ação | Bloqueia produção? |
|----|------|--------|------|------|--------------------|
| C-01 | 🔴 Crítico | RBAC não aplicado nas rotas | 2 | Decorator `@requer_permissao` + seed de permissões | **Sim** |
| A-01 | 🟠 Alto | Cookie sem Secure + HTTPS off | 1 | Ativar TLS/HSTS no Nginx | Sim |
| A-02 | 🟠 Alto | IDOR/BOLA em downloads por id | 2 | Checar vínculo/permissão antes de servir | Sim |
| A-03 | 🟠 Alto | Sem criptografia em trânsito (LGPD) | 4 | TLS obrigatório | Sim |
| A-04 | 🟠 Alto | Dados em repouso sem cifra | 4 | Cifra de volume/campo + backup cifrado | Plano |
| A-05 | 🟠 Alto | Werkzeug/cryptography com CVE | 5 | Atualizar versões | Plano |
| A-06 | 🟠 Alto | SECRET_KEY fraca + validate() não chamado | 6 | Chamar `validate()` no factory | Sim |
| M-01 | 🟡 Médio | Contador de tentativas revela usuário | 1 | Remover contador da mensagem | Plano |
| M-02 | 🟡 Médio | Política de senha fraca | 1 | Reforçar complexidade | Plano |
| M-03 | 🟡 Médio | Validação de upload de cert | 3 | Temp + verificar conteúdo | Plano |
| M-04 | 🟡 Médio | Sem log de acesso a prontuário | 4 | Auditoria de leitura (LGPD/PEP) | Plano |
| M-05 | 🟡 Médio | Flask/Pillow com CVE | 5 | Atualizar | Plano |
| M-06 | 🟡 Médio | Admin seed com senha fixa | 6 | Forçar troca / documentar | Plano |
| M-07 | 🟡 Médio | Rota pública sem rate limit | 7 | Rate limiting + expor mínimo | Plano |
| B-01..B-03 / I-01 | ⚪ Baixo/Info | remember-me, nome de upload, headers Nginx, migrate no boot | — | Higiene | Não |

---

## Veto de pré-produção (Artigo II da Constituição)

Conforme a autoridade do `@si`, **veto a liberação para produção com dados reais de
pacientes** enquanto **C-01** e os **Altos que bloqueiam produção** (A-01, A-02, A-03, A-06)
não forem resolvidos e reauditados. Achados marcados como "Plano" podem seguir com issue de
remediação rastreada.

## Próximos passos

1. Abrir stories de remediação (via `@po`) para C-01 e Altos.
2. `@dev` implementa; `@si` reauditа (`*audit-code`) após correção.
3. Adicionar `pip-audit`/Dependabot + verificações no CI (ver `security-first.md`).
4. Registrar o plano em `docs/security/remediations.md`.

---

## Referências (fontes externas)

- CVE-2025-66221 (Werkzeug): https://www.sentinelone.com/vulnerability-database/cve-2025-66221/
- CVE-2025-47278 (Flask): https://www.sentinelone.com/vulnerability-database/cve-2025-47278/
- CVE-2026-27205 (Flask): https://www.sentinelone.com/vulnerability-database/cve-2026-27205/
- CVE-2026-39892 (cryptography): https://github.com/advisories/GHSA-p423-j2cm-9vmq
- CVE-2025-48379 (Pillow): https://access.redhat.com/security/cve/cve-2025-48379
- LGPD — Lei 13.709/2018

*Conteúdo das fontes externas foi reformulado para conformidade com restrições de licenciamento.*

---

*Gerado pelo PDA-SQUAD v1.0.0 — comando `@si *audit-code`*
