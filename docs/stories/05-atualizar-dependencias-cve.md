# Story S-05 — Atualizar dependências com CVE conhecido

**Épico:** Base e Segurança (NFR-05)
**Prioridade:** P1 — plano de correção antes do go-live
**Status:** Concluído
**Origem:** @si A-05 (Alto) / M-05 (Médio)

---

## Contexto
Auditoria de dependências (`requirements.txt`, versões pinadas) identificou CVEs nas versões
fixadas:
- **Werkzeug 3.1.3** — path traversal em `safe_join` (CVE-2025-66221, corrigido em 3.1.4).
- **cryptography 43.0.3** — buffer overflow com buffers não contíguos (CVE-2026-39892).
- **Flask 3.1.1** — chave de fallback obsoleta na assinatura de sessão (CVE-2025-47278) e
  info disclosure `Vary: Cookie` (CVE-2026-27205).
- **Pillow 11.1.0** — série de CVEs corrigidos em 12.x (ex.: CVE-2025-48379).

## Descrição
Como **responsável de TI**, quero as dependências atualizadas para versões sem
vulnerabilidades conhecidas, para reduzir a superfície de ataque.

## Critérios de Aceite
- [x] Werkzeug ≥ 3.1.4 (→ **3.1.8**) e cryptography atualizada (→ **50.0.1**).
- [x] Flask (→ **3.1.3**) e Pillow (→ **12.3.0**) sem os CVEs listados.
- [x] Versões permanecem **pinadas** (exatas, `==`) no `requirements.txt`.
- [x] `pip-audit` roda **sem nenhum achado** (não só CRÍTICOS/ALTOS — zero).
- [x] App sobe e os fluxos-chave (login, assinatura PAdES, PDF/QR) continuam funcionando (suíte 22/22 + smoke da cadeia crypto/pyhanko/Pillow/reportlab).

## Tarefas
1. [x] Versões atualizadas no `requirements.txt`; imagem rebuildada (resolve sem conflitos).
2. [x] `pip-audit` executado; resultado registrado em `docs/security/pip-audit-S05.md`.
3. [x] Regressão da cadeia cryptography/pyHanko/Pillow/qrcode/reportlab (gerar cert → assinar PAdES → verificar → detectar adulteração → QR PNG/base64): **OK**.
4. [ ] Varredura contínua (Dependabot/`pip-audit` no CI) — **fora do escopo**, endereçada na **S-08**.

## Implementação (resumo @dev)
Atualizações pinadas (antes → depois):
- Flask `3.1.1→3.1.3`, Werkzeug `3.1.3→3.1.8`, cryptography `43.0.3→50.0.1`,
  Pillow `11.1.0→12.3.0`, pyOpenSSL `24.3.0→26.4.0`, pyhanko `0.25.1→0.36.2`,
  pyhanko-certvalidator `0.26.5→0.31.4`.
- Extras detectados pelo `pip-audit` e também corrigidos: Flask-Cors `5.0.1→6.0.0`,
  marshmallow `3.26.1→3.26.2`, python-dotenv `1.0.1→1.2.2`, pytest `8.3.5→9.0.3`.
- `Dockerfile`: `pip` do base image atualizado para `>=26.2.1` (corrige PYSEC-2026-* do pip).

Compatibilidade da cadeia de assinatura (risco destacado nas notas): pyhanko 0.36.2,
pyhanko-certvalidator 0.31.4 e pyOpenSSL 26.4.0 exigem `cryptography <51,>=49` /
`>=48` — **cryptography 50.0.1 satisfaz todos**; instalação sem conflitos.

## Verificação
- `pip-audit`: **No known vulnerabilities found** (antes: 13 vulns em 5 pacotes).
- `pytest`: **22 passed** na imagem atualizada (pytest 9.0.3).
- Smoke da cadeia crypto/PDF/QR: **OK** (assinatura íntegra, adulteração detectada, QR gerado).

## Notas
- Marshmallow mantido na série 3.x (3.26.2, patch) para evitar a quebra da major 4.x.
- Próximo passo: **@qadv `*qa 5`**.

---

## QA — @qadv (`*qa 5`)

**Resultado:** ✅ **APROVADO** na primeira rodada.

### Método (verificação independente)
Build **do zero** (`docker build --no-cache`) para garantir que o conjunto resolve
sem depender de camadas em cache, + `pip-audit` + suíte + smoke próprio da cadeia
de assinatura.

### Evidências
| Critério | Verificação | Resultado |
|----------|-------------|-----------|
| Werkzeug ≥ 3.1.4 + cryptography corrigida | `pip show` na imagem | Werkzeug **3.1.8**, cryptography **50.0.1** ✅ |
| Flask/Pillow sem CVE | `pip show` | Flask **3.1.3**, Pillow **12.3.0** ✅ |
| Versões pinadas (`==`) | `requirements.txt` | todas exatas ✅ |
| `pip-audit` sem CRÍTICOS/ALTOS | audit na imagem (pip 26.2.1) | **No known vulnerabilities found** ✅ |
| App + fluxos-chave | `pytest` + smoke crypto/PDF/QR | **22 passed**; smoke `QA5_SMOKE_OK` ✅ |
| Build reprodutível | `--no-cache` | resolve sem conflitos ✅ |

### Observações
- Os `PathBuildingError`/`InvalidCertificateError` que aparecem no log do smoke são
  **esperados e tratados** internamente (cert de teste autoassinado → validação de
  cadeia falha e o serviço degrada para checagem de integridade). Não são falhas.
- @dev foi além do escopo mínimo: o `pip-audit` revelou 5 pacotes vulneráveis além
  dos 4 da story (flask-cors, marshmallow, python-dotenv, pytest, pip) e todos foram
  corrigidos, zerando o audit. Decisão acertada de manter marshmallow em 3.x (patch).
- **Tarefa 4 (Dependabot/CI)** não é critério de aceite — deferida à **S-08**. Não bloqueia.

### Recomendação (não bloqueante)
- Fazer o rebuild da imagem de produção no deploy (a imagem antiga ainda tem as libs
  antigas até o próximo `docker compose build`).
