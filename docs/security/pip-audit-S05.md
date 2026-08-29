# Relatório pip-audit — Story S-05 (Atualização de dependências com CVE)

**Agente:** @dev · **Comando:** `*develop 5` · **Data:** 2026-08-28
**Ferramenta:** `pip-audit` (base de dados PyPI Advisory / OSV)
**Ambiente:** imagem do app (`backend/Dockerfile`, Python 3.12)

---

## Resultado final

```
pip-audit
No known vulnerabilities found        (exit 0)
```

✅ **Sem achados** após as atualizações. Critério de aceite (sem CRÍTICOS/ALTOS) atendido —
na prática, **zero** vulnerabilidades conhecidas no conjunto instalado.

---

## Antes → Depois (versões pinadas)

| Pacote | Antes | Depois | CVE/Advisory endereçado |
|--------|-------|--------|-------------------------|
| Flask | 3.1.1 | **3.1.3** | CVE-2025-47278, CVE-2026-27205 |
| Werkzeug | 3.1.3 | **3.1.8** | CVE-2025-66221 (path traversal `safe_join`) |
| cryptography | 43.0.3 | **50.0.1** | CVE-2026-39892 (buffer overflow) |
| Pillow | 11.1.0 | **12.3.0** | CVE-2025-48379 (série 12.x) |
| pyOpenSSL | 24.3.0 | **26.4.0** | compat. com cryptography <51,>=49 |
| pyhanko | 0.25.1 | **0.36.2** | compat. cadeia de assinatura |
| pyhanko-certvalidator | 0.26.5 | **0.31.4** | compat. cadeia de assinatura |
| Flask-Cors | 5.0.1 | **6.0.0** | PYSEC-2026-1383/1384/1385 |
| marshmallow | 3.26.1 | **3.26.2** | PYSEC-2026-1605 |
| python-dotenv | 1.0.1 | **1.2.2** | PYSEC-2026-2270 |
| pytest | 8.3.5 | **9.0.3** | PYSEC-2026-1845 (dev/test) |
| pip (base image) | 25.0.1 | **26.2.1** | PYSEC-2026-196/1795/1796/2875/2876/3721 |

> A primeira execução do `pip-audit` (só com os 4 pacotes da story atualizados) ainda
> apontou 13 vulnerabilidades em 5 pacotes (flask-cors, marshmallow, python-dotenv, pytest,
> pip). Esses foram tratados na mesma story para zerar o audit.

---

## Compatibilidade verificada (cadeia de assinatura ICP-Brasil)

Restrições de `cryptography` na cadeia pyHanko (risco destacado pela story):

- `pyhanko 0.36.2` → `cryptography <51,>=49.0.0`
- `pyhanko-certvalidator 0.31.4` → `cryptography >=48.0.0`
- `pyOpenSSL 26.4.0` → `cryptography <51,>=49.0.0`

`cryptography 50.0.1` satisfaz as três. A instalação completa resolveu **sem conflitos**
(`pip install -r requirements.txt` no build da imagem).

---

## Como reproduzir

```bash
docker build -t sghsc_app ./backend
docker run --rm --entrypoint sh sghsc_app -c 'pip install -q pip-audit && pip-audit'
```

---

## Pendências (fora do escopo desta story)

- **Varredura contínua no CI** (Dependabot / `pip-audit` no pipeline) — endereçada na **S-08**.
