# Story Q-SEC-06 — DevSecOps no pipeline (SAST, secret scanning, sanitização)

**Épico:** Segurança ISO 27001 (FR-SEC-06) — Controles **A.8.25/A.8.28** (desenvolvimento e codificação seguros)
**Prioridade:** P1
**Status:** A fazer
**Origem:** `docs/iso27001-gap-analysis.md`, consultoria do cliente
**Branch:** `quiron`

---

## Contexto
O CI já roda lint (ruff) + testes (pytest) + `pip-audit`. Falta **SAST** (análise estática de
segurança), **secret scanning** (evitar segredos commitados) e sanitização explícita de texto
livre renderizado com `| safe`/HTMX. A ISO 27001 (A.8.28) pede segurança no ciclo de vida.

## Descrição
Como **engenheiro de segurança**, quero que o pipeline barre vulnerabilidades e segredos
antes do deploy, e que texto livre digitado por profissionais seja sanitizado.

## Critérios de Aceite
- [ ] **SAST** com `bandit` no `ci.yml`, falhando o build em achado de severidade relevante.
- [ ] **Secret scanning** com `gitleaks` (ou `detect-secrets`) no `ci.yml`, falhando em segredo detectado.
- [ ] Sanitização com **`bleach`** aplicada onde texto livre (anamnese, evolução, observações)
  é renderizado sem escape (`| safe`); revisão de todos os usos de `| safe`.
- [ ] Proteção da branch **`main`** no GitHub: PR obrigatório + revisão + CI verde antes do merge.
- [ ] Documentar DAST periódico (ex.: OWASP ZAP contra homolog) — processo, pode ser manual no início.
- [ ] CI segue verde com as novas etapas (ajustar falsos-positivos com baseline se necessário).

## Tarefas
1. Adicionar `bandit` e `gitleaks` como etapas no `.github/workflows/ci.yml` (com baseline/allowlist quando preciso).
2. Adicionar `bleach` ao `requirements.txt`; helper de sanitização + aplicar nos pontos de `| safe`.
3. Auditar templates por usos de `| safe` e corrigir.
4. Configurar branch protection na `main` (via GitHub Settings — documentar; não é código).
5. `docs/security/devsecops.md`: SAST/secret scanning/DAST + como tratar achados.
6. Rodar o pipeline e estabilizar.

## Notas
- Manter `pip-audit` (S-05) — as etapas são complementares (SCA + SAST + secret scan).
- Branch protection é configuração do repositório (Settings → Branches), fora do código; documentamos o passo.
