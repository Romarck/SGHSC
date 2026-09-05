# Story Q-MT-00 — Fundação multi-tenant: model Empresa, papéis e rebranding QUÍRON

**Épico:** SAAS Multi-tenant (FR-MT-01 / FR-MT-06)
**Prioridade:** P0 — base de todas as demais fases
**Status:** A fazer
**Origem:** `docs/plano-quiron-multitenant.md` (Fase MT-0), PRD v2.0
**Branch:** `quiron`

---

## Contexto
O QUÍRON deixa de ser instância única (Santa Casa de Pedralva) para se tornar um SAAS
multi-tenant. Antes de tocar nos dados, precisamos da entidade **Empresa** (tenant), dos
novos eixos de acesso no `Usuario` (Super-Admin x usuário de empresa) e do rebranding —
sem quebrar o app atual, que continua operando como empresa única até a MT-1.

## Descrição
Como **operador do SAAS (Super-Admin)**, quero que exista o conceito de Empresa e o papel
de Super-Admin, para poder futuramente cadastrar e isolar empresas-clientes.

## Critérios de Aceite
- [ ] Model `Empresa` (`app/models/empresa.py`) com: `nome_fantasia`, `razao_social`,
  `cnpj` (único), `cnes`, `slug` (único), contato/endereço, `status`
  (`StatusEmpresa`: ATIVA/SUSPENSA/CANCELADA/TRIAL), `plano`
  (`PlanoEmpresa`: BASICO/PROFISSIONAL/ENTERPRISE), `data_contratacao`,
  `data_expiracao`, `logo_path` e auditoria (`criado_em/atualizado_em/criado_por_id`).
- [ ] `Usuario` ganha `empresa_id` (FK → `empresas.id`, **nullable**) e `is_super_admin` (bool).
- [ ] `Empresa` exportada em `app/models/__init__.py`.
- [ ] Migração Alembic cria a tabela `empresas` e as colunas novas em `usuarios` (sem quebrar seed atual).
- [ ] Rebranding **de produto/UX**: título, navbar, login, rodapé e docs passam a exibir
  **"QUÍRON — Inteligência Clínica, Segurança e Performance Hospitalar"**. Nome técnico
  interno (pacote/DB/containers `sghsc`) permanece para evitar migração de infra.
- [ ] `config.py`: nome amigável do produto configurável (mantém compatibilidade de env).
- [ ] App sobe normalmente após a migração; testes existentes continuam verdes.

## Tarefas
1. Criar `app/models/empresa.py` (`Empresa`, `StatusEmpresa`, `PlanoEmpresa`) + export em `models/__init__.py`.
2. Adicionar `empresa_id` (nullable) e `is_super_admin` ao `Usuario`.
3. Gerar migração Alembic (`empresas` + colunas em `usuarios`).
4. Rebranding: `templates/layout.html`, `auth/login.html`, rodapé; `config.py` (`PRODUTO_NOME`); `README.md`.
5. Ajustar mensagens/labels que citam "SGHSC"/"Santa Casa" fixas na UI para o nome do produto.
6. Rodar suíte + `flask db upgrade` local.

## Notas
- **Não** adicionar `empresa_id` às tabelas de negócio ainda — isso é a MT-1.
- Decisão do modelo de tenant registrada em **ADR-007** (criar junto).
- `username`/`email` únicos globais por enquanto; a unicidade composta por empresa vem na MT-1.
