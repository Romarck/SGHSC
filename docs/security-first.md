# 🔐 Guia de Segurança: Projetos Regulados

**Projeto:** SGHSC | **Tipo:** greenfield | **Gerado em:** 2026-08-28

---

## Quando Usar Este Guia

Este documento é obrigatório se seu projeto:

- [ ] Está sujeito a regulação do **Banco Central (BCB)** — Resolução 85/2021
- [ ] Processa dados de **clientes bancários** ou **pagamentos** (FEBRABAN/CNAB)
- [ ] Acessa dados de **mercado de capitais, ordens ou carteiras** (B3/CVM)
- [ ] Processa dados **pessoais regulados** (LGPD)
- [ ] Será hospedado em ambiente produtivo sujeito a auditorias

Se qualquer item acima está marcado ✅, siga este guia.

---

## Fluxo Obrigatório para Projetos Regulados

### 1️⃣ Fase 0: Auditoria de Segurança (ANTES de qualquer desenvolvimento)

```bash
# Brownfield (projeto existente):
@security *audit-code
@security *compliance BCB        # ou FEBRABAN/B3-CVM conforme aplicável
@security *report

# Espere resultado: ✅ APROVADO ou ⚠️ RESSALVAS
# Se ❌ REPROVADO, resolva achados críticos antes de prosseguir
```

**Resultado esperado em `docs/security/audit-report.md`:**
- Tabela de vulnerabilidades encontradas
- Análise de dependências maliciosas
- Endpoints externos mapeados
- Parecer de compliance com status

### 2️⃣ Adicionar Conformidade ao Desenvolvento

Ao implementar stories, adicione verificações de segurança:

```bash
# Para cada story que toca em dados sensíveis:
@dev *develop N

# Antes de QA:
@security *check-code "secrets|credentials|tokens|passwords"

# Depois:
@ship *qa N
```

### 3️⃣ Pré-Produção (Obrigatório)

```bash
# Auditoria final antes de deploy:
@security *audit-code

# Confirme compliance:
@security *compliance BCB

# Gere relatório para auditores:
@security *report
```

---

## Checklist de Segurança por Regulador

### 🏛️ Banco Central (Resolução BCB 85/2021)

- [ ] Código auditado sem vulnerabilidades críticas
- [ ] Dependências verificadas e pinadas
- [ ] Endpoints externos documentados
- [ ] Não há exfiltração de dados sensíveis
- [ ] Não há hardcoding de secrets (usar env vars)
- [ ] Relatório de auditoria disponível em `docs/security/`

**Comando:** `@security *compliance BCB`

### 🏦 FEBRABAN (Segurança Bancária)

- [ ] Credenciais de acesso protegidas (sem hardcode)
- [ ] Autenticação segura (OAuth, JWT, mTLS)
- [ ] Criptografia em trânsito (HTTPS, TLS 1.2+)
- [ ] Validação de integridade de mensagens CNAB
- [ ] Logs de auditoria de transações
- [ ] Sem exposição de dados de clientes

**Comando:** `@security *compliance FEBRABAN`

### 📊 B3 / CVM (Mercado de Capitais)

- [ ] Dados de mercado não exfiltrados
- [ ] Integridade de ordens e carteiras garantida
- [ ] LGPD — consentimento de dados de investidores
- [ ] Auditoria de acesso a dados de clientes
- [ ] Sem cache em local inseguro
- [ ] Relatório regulatório disponível

**Comando:** `@security *compliance B3-CVM`

---

## Fluxo de Remediação

Se `@security` encontrar achados:

### 🔴 Crítico
❌ **BLOQUEIA** desenvolvimento/deploy

```bash
# 1. Corrigir imediatamente
# 2. Re-auditar:
@security *audit-code

# 3. Confirmar resolução:
@security *report
```

### 🟠 Alto
⚠️ **Pode prosseguir com plano de correção**

```bash
# 1. Abrir issue rastreando a correção
# 2. Adicionar story para remediação no próximo sprint
# 3. Documentar em docs/security/remediations.md
# 4. Re-auditar após correção
```

### 🟡 Médio
ℹ️ **Apenas para conhecimento**

```bash
# 1. Documentar em docs/security/notes.md
# 2. Revisar em próxima auditoria periódica
```

---

## Monitonamento Contínuo

### Auditorias Periódicas

**Semanal (recomendado):**
```bash
@security *scan-deps  # Verificar novas vulnerabilidades em dependências
```

**Mensal:**
```bash
@security *check-network  # Verificar endpoints e comunicação externa
```

**Trimestral:**
```bash
@security *audit-code     # Auditoria completa
@security *compliance [seu-regulador]
@security *report         # Gerar para registros de compliance
```

---

## Estrutura de Documentação de Segurança

Seus relatórios de segurança ficarão em:

```
docs/security/
├── audit-report.md              # Auditoria completa
├── compliance-bcb.md            # Parecer BCB
├── compliance-febraban.md       # Parecer FEBRABAN
├── compliance-b3-cvm.md         # Parecer B3/CVM
├── remediations.md              # Plano de correções
├── notes.md                     # Anotações de segurança
└── .gitkeep
```

**Estes arquivos devem estar disponíveis para auditores!**

---

## Integração com CI/CD

Recomendado adicionar verificações de segurança ao pipeline:

```yaml
# .github/workflows/security.yml (exemplo)
name: Security Audit

on: [pull_request, push]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Security Audit
        run: |
          # Executar @security via CLI ou API
          @security *scan-deps
          @security *check-code "secrets|credentials"
```

---

## Contato e Suporte

Se encontrar questões de segurança:

1. **Comunique ao `@security`** — relatar achado
2. **Escale se crítico** — não prossiga até resolver
3. **Documente** — adicionar ao plano de remediações
4. **Re-audite** — confirmar correção antes de produção

---

## Referências

- **BCB Resolução 85/2021:** Segurança da informação em ambientes de TI
- **FEBRABAN:** Guias de segurança para integração bancária
- **B3/CVM:** Conformidade para mercado de capitais
- **LGPD:** Proteção de dados pessoais (Lei 13.709/2018)

---

*Documento gerado automaticamente pelo PDA-SQUAD — Não edite diretamente*
*Última atualização: 2026-08-28*
