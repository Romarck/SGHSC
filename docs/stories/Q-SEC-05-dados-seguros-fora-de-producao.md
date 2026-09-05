# Story Q-SEC-05 — Dados seguros fora de produção (dev/homologação)

**Épico:** Segurança ISO 27001 (NFR-ISO-04) — Controles **A.8.31** (separação de ambientes), **A.8.33** (dados de teste)
**Prioridade:** P0
**Status:** A fazer
**Origem:** `docs/iso27001-gap-analysis.md`, consultoria do cliente
**Branch:** `quiron`

---

## Contexto
A ISO 27001 e a LGPD proíbem usar **dados reais de pacientes** em desenvolvimento e
homologação. É preciso garantir que dev/homolog usem dados **fictícios ou mascarados**.

## Descrição
Como **desenvolvedor/gestor**, quero uma regra e ferramentas que garantam que nenhum dado
real de paciente seja usado fora de produção.

## Critérios de Aceite
- [ ] `seed_demo.py` gera dados **100% fictícios** (nomes, CPF/CNS válidos em formato mas não reais)
  e cobre os cenários necessários para dev/homolog.
- [ ] Rotina de **anonimização/mascaramento** para gerar dump de homolog a partir de produção,
  quando necessário (mascara nome, CPF, CNS, contatos, endereço).
- [ ] Regra documentada: **proibido dado real em dev/homolog**; onde registrar/como pedir exceção.
- [ ] Ambientes claramente separados por config (`FLASK_ENV`), sem apontar dev para banco de produção.
- [ ] Verificação: `TestingConfig` usa SQLite em memória (já é o caso); dev usa seed fictício.

## Tarefas
1. Revisar/ampliar `backend/seed_demo.py` para dados fictícios abrangentes e realistas em formato.
2. Script de anonimização de dump (`ops/anonimizar_dump.*`) mascarando PII/dados sensíveis.
3. `docs/security/dados-nao-producao.md` com a política e o passo a passo.
4. Checagem no CI/boot que impeça dev/homolog de usar credenciais de produção (guard rail).
5. Teste do seed fictício (roda sem erro, gera volume mínimo esperado).

## Notas
- Casa com a cifra de coluna (Q-SEC-03): dados fictícios em dev não dependem da chave de produção.
- Anonimização é irreversível por design (não guardar mapa de reidentificação).
