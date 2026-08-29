# SGHSC — Estado do Projeto e Guia de Continuação

**Sistema de Gestão Hospitalar para Santas Casas**
Santa Casa de Misericórdia de Pedralva - MG

> Este arquivo serve como ponto de referência para retomar o desenvolvimento em qualquer nova sessão.
> Leia-o antes de continuar qualquer tarefa.

---

## Stack Tecnológica

| Camada      | Tecnologia                                  |
|-------------|---------------------------------------------|
| Backend     | Python 3.12 + Flask 3.1                     |
| ORM         | SQLAlchemy 2 + Flask-Migrate (Alembic)      |
| Banco       | PostgreSQL 16 (container Docker)            |
| Frontend    | Jinja2 + HTMX + Bootstrap 5 + Bootstrap Icons |
| Servidor    | Nginx 1.25 (proxy reverso)                  |
| Containers  | Docker + Docker Compose                     |
| Assinatura  | pyHanko (ICP-Brasil, PAdES)                 |
| PDF         | ReportLab + pyHanko                         |
| QR Code     | qrcode (validação de documentos assinados)  |

---

## Ambiente de Desenvolvimento Local

```bash
# Subir tudo
cd /home/romarck/Documentos/Projetos/SGHSC
docker compose up -d

# Ver logs
docker compose logs -f app

# Rodar migração após alterar modelos
docker compose exec app flask db migrate -m "descrição"
docker compose exec app flask db upgrade

# Acessar o sistema
http://localhost          # via Nginx
http://localhost:5050     # Flask direto
# Login: admin / Admin@123 (obriga troca no primeiro acesso)
```

**Portas em uso no ambiente:**
- `80` → Nginx
- `5050` → Flask (porta externa; interna é 5000)
- `5444` → PostgreSQL (porta externa; evita conflito com outros projetos)

---

## Estrutura do Projeto

```
SGHSC/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App factory — registra blueprints aqui
│   │   ├── config.py            # Dev / Test / Prod
│   │   ├── extensions.py        # db, migrate, login_manager, bcrypt, csrf
│   │   ├── models/
│   │   │   ├── __init__.py      # Exporta TODOS os models (Alembic precisa)
│   │   │   ├── usuario.py       # Usuario, Perfil, Permissao (RBAC)
│   │   │   ├── paciente.py      # Paciente
│   │   │   ├── prontuario.py    # Prontuario, EntradaProntuario
│   │   │   ├── emergencia.py    # AtendimentoEmergencia, TriagemManchester
│   │   │   ├── ambulatorio.py   # AgendaAmbulatorio, ConsultaAmbulatorial
│   │   │   ├── internacao.py    # Leito, Internacao, Prescricao, Controles, Evolucoes
│   │   │   ├── certificado.py   # CertificadoDigital, DocumentoAssinado
│   │   │   ├── exame.py         # ExameCatalogo, SolicitacaoExame, ItemExame, ResultadoExame
│   │   │   ├── farmacia.py      # MedicamentoFarmacia, LoteEstoque, Dispensacao, MovimentoEstoque
│   │   │   ├── nutricao.py      # PrescricaoDietetica
│   │   │   ├── ccih.py          # NotificacaoInfeccao, IsolamentoPaciente
│   │   │   ├── cirurgia.py      # SalaCirurgica, Cirurgia
│   │   │   ├── maternidade.py   # PreNatal, ConsultaPreNatal, Parto, RecemNascido
│   │   │   ├── estoque.py       # ProdutoEstoque, SaldoEstoque, Requisicao, Inventario
│   │   │   ├── compras.py       # Fornecedor, SolicitacaoCompra, PedidoCompra, Recebimento
│   │   │   ├── financeiro.py    # Conta, LancamentoCaixa, CategoriaFinanceira
│   │   │   ├── faturamento.py   # GuiaFaturamento (AIH/APAC/BPA), ProcedimentoSIGTAP
│   │   │   ├── convenios.py     # Convenio, GuiaConvenio, ProcedimentoCBHPM
│   │   │   ├── patrimonio.py    # BemPatrimonial, MovimentacaoBem
│   │   │   ├── rh.py            # Setor, Funcionario, EscalaPlantao
│   │   │   ├── manutencao.py    # OrdemServico
│   │   │   ├── residuos.py      # RegistroResiduo, ColetaResiduo (PGRSS)
│   │   │   └── rnds.py          # RegistroRNDS (FHIR R4)
│   │   ├── routes/
│   │   │   ├── auth.py          # /auth/login, /auth/logout, /auth/trocar-senha
│   │   │   ├── main.py          # /, /dashboard, /dashboard/contadores
│   │   │   ├── pacientes.py     # /pacientes/
│   │   │   ├── emergencia.py    # /emergencia/
│   │   │   ├── ambulatorio.py   # /ambulatorio/
│   │   │   ├── internacao.py    # /internacao/
│   │   │   ├── certificado.py   # /certificado/ (inclui validação pública)
│   │   │   ├── exames.py        # /exames/
│   │   │   ├── farmacia.py      # /farmacia/
│   │   │   ├── nutricao.py      # /nutricao/
│   │   │   ├── ccih.py          # /ccih/
│   │   │   ├── cirurgias.py     # /cirurgias/
│   │   │   ├── maternidade.py   # /maternidade/
│   │   │   ├── estoque.py       # /estoque/
│   │   │   ├── compras.py       # /compras/
│   │   │   ├── financeiro.py    # /financeiro/
│   │   │   ├── faturamento.py   # /faturamento/
│   │   │   ├── convenios.py     # /convenios/
│   │   │   ├── patrimonio.py    # /patrimonio/
│   │   │   ├── rh.py            # /rh/
│   │   │   ├── manutencao.py    # /manutencao/
│   │   │   ├── relatorios.py    # /relatorios/ (dashboard gerencial)
│   │   │   ├── residuos.py      # /residuos/ (PGRSS)
│   │   │   └── rnds.py          # /rnds/ (FHIR R4)
│   │   ├── services/            # Lógica de negócio
│   │   │   ├── pdf_service.py   # Geração de PDFs (laudos, prescrições, evoluções)
│   │   │   ├── cert_service.py  # Assinatura digital ICP-Brasil (pyHanko) + timestamp + QR
│   │   │   └── indicadores_service.py  # Indicadores gerenciais (dashboard)
│   │   ├── schemas/             # Marshmallow (a popular)
│   │   ├── templates/
│   │   │   ├── layout.html      # Base com navbar completa
│   │   │   ├── auth/            # login.html, trocar_senha.html
│   │   │   ├── main/            # dashboard.html, _contadores.html
│   │   │   ├── errors/          # 400, 403, 404, 500
│   │   │   ├── pacientes/       # lista, _tabela, _resultado_busca, form, detalhe
│   │   │   ├── emergencia/      # fila, registrar_chegada, triagem, atendimento, saida
│   │   │   ├── ambulatorio/     # agenda, agendas, form_agenda, agendar, consulta
│   │   │   ├── internacao/      # mapa_leitos, form_leito, lista, admissao, prontuario,
│   │   │   │                    # prescricao, controles, evolucoes, transferencia, alta
│   │   │   ├── certificado/     # painel, upload, validar (público)
│   │   │   ├── exames/          # lista, fila, solicitar, detalhe, resultado, catalogo
│   │   │   ├── farmacia/        # estoque, form_medicamento, entrada, movimentos, dispensar
│   │   │   ├── nutricao/        # mapa, prescrever
│   │   │   ├── ccih/            # painel, notificar, detalhe_notificacao, isolar, relatorio
│   │   │   ├── cirurgias/       # escala, mapa, solicitar, detalhe, agendar, descricao, salas
│   │   │   └── maternidade/     # painel, form_prenatal, detalhe_prenatal, form_parto, detalhe_parto
│   │   └── static/
│   │       └── css/sghsc.css    # Estilos customizados
│   ├── migrations/              # Alembic — NÃO apagar
│   ├── entrypoint.sh            # Init automático: wait DB → migrate → seed → start
│   ├── wsgi.py
│   ├── Dockerfile
│   └── requirements.txt
├── nginx/nginx.conf
├── docker-compose.yml
├── .env                         # NÃO commitar
├── .env.example
└── docs/
    └── PROJECT_STATE.md         # ESTE ARQUIVO
```

---

## Padrões de Código

### Novo módulo — checklist
1. Criar `app/models/novo_modulo.py` com os models SQLAlchemy
2. Importar no `app/models/__init__.py`
3. Criar `app/routes/novo_modulo.py` com Blueprint
4. Registrar blueprint em `app/__init__.py` dentro de `_register_blueprints()`
5. Criar `app/templates/novo_modulo/` com os templates Jinja2
6. Rodar `docker compose exec app flask db migrate -m "add novo_modulo"`
7. Rodar `docker compose exec app flask db upgrade`
8. Adicionar item no menu da navbar em `templates/layout.html`
9. Adicionar card no dashboard `templates/main/dashboard.html`

### Convenções
- **Enumerações:** sempre usar Python `enum.Enum`, nunca strings soltas
- **Auditoria:** todo model deve ter `criado_em`, `atualizado_em`, `criado_por_id`
- **Numeração de documentos:** padrão `PREFIXOAAAAMMDDNNNN` (ex: `PA202608280001`)
- **Busca HTMX:** usar `hx-get`, `hx-trigger="keyup changed delay:400ms"`, `hx-target`
- **Formulários:** sempre usar Flask-WTF com `{{ form.hidden_tag() }}` (CSRF)
- **Permissões:** usar `current_user.tem_permissao("modulo.acao")` (RBAC)
- **Nomes em português** nos modelos, rotas e templates

---

## Status das Fases

### ✅ Fase 1 — Base do sistema (CONCLUÍDA)

**O que foi feito:**
- Docker Compose: app (Flask) + db (PostgreSQL 16) + nginx
- App factory Flask com blueprints, config por ambiente (dev/test/prod)
- Sistema de autenticação completo: login, logout, troca de senha obrigatória
- Bloqueio automático após 5 tentativas inválidas (30 min)
- RBAC: modelo `Usuario`, `Perfil`, `Permissao` com 15 tipos de perfil pré-definidos
- `user_loader` do Flask-Login configurado
- Template base (layout.html) com navbar, flash messages, footer
- Telas de erro customizadas (400, 403, 404, 500)
- CSS customizado (`sghsc.css`) com estilos de leitos, Manchester, certificado digital, impressão
- Logging rotativo configurado
- `entrypoint.sh`: aguarda banco → `flask db init/migrate/upgrade` → cria admin → inicia app
- Admin padrão: `admin` / `Admin@123` (obriga troca no primeiro acesso)

**Arquivos-chave:**
```
app/__init__.py, app/config.py, app/extensions.py
app/models/usuario.py
app/routes/auth.py, app/routes/main.py
templates/layout.html, templates/auth/
```

---

### ✅ Fase 2 — Porta de entrada (CONCLUÍDA)

**O que foi feito:**

**Pacientes:**
- Model `Paciente` com 30+ campos: dados pessoais, documentos (CPF, RG, CNS), saúde (alergias, plano), endereço, contato, filiação, responsável
- Propriedades calculadas: `idade`, `nome_exibicao`, `endereco_formatado`
- CRUD completo: listagem paginada, busca em tempo real (HTMX) por nome/CPF/CNS, cadastro, edição, detalhe
- Preenchimento automático de endereço via ViaCEP (JavaScript)
- Prontuário aberto automaticamente ao cadastrar paciente

**Prontuário (base):**
- Model `Prontuario` (número único por instituição, formato `ANO-NNNNNN`)
- Model `EntradaProntuario` (qualquer tipo de registro clínico com suporte a assinatura digital)
- Campo `assinatura_hash` e `pdf_path` para documentos assinados com ICP-Brasil

**Pronto-Atendimento / Emergência:**
- Model `AtendimentoEmergencia` com fluxo completo: chegada → triagem → atendimento → saída
- Model `TriagemManchester` com todas as 5 cores (vermelho/laranja/amarelo/verde/azul), sinais vitais completos, queixa, discriminador
- Painel de fila com contadores por status e cor
- Registro de chegada com busca HTMX de paciente
- Triagem com seletor visual de cor Manchester
- Atendimento médico: anamnese, exame físico, hipótese diagnóstica, CID-10, conduta
- Saída: alta médica, internação, transferência, óbito, evasão

**Ambulatório:**
- Model `AgendaAmbulatorio` (grade de horários por médico/dia/especialidade)
- Model `ConsultaAmbulatorial` com status completo, sinais vitais, CID-10, prescrição, retorno
- Agenda do dia com navegação por data e contadores
- Agendamento com busca HTMX de paciente
- Atendimento médico completo (anamnese, exame, conduta, receituário)
- Finalização e cancelamento de consultas

**Dashboard:**
- Contadores em tempo real via HTMX (total pacientes, fila PA, consultas hoje, atendimentos hoje)
- Cards de acesso rápido com links ativos para Pacientes, Emergência e Ambulatório
- Navbar com menus dropdown para cada módulo

**Arquivos criados:**
```
app/models/paciente.py, prontuario.py, emergencia.py, ambulatorio.py
app/routes/pacientes.py, emergencia.py, ambulatorio.py
templates/pacientes/ (5 arquivos)
templates/emergencia/ (5 arquivos)
templates/ambulatorio/ (5 arquivos)
templates/main/_contadores.html
```

---

### ✅ Fase 3 — Internação (CONCLUÍDA)

**O que foi feito:**

**Models (`app/models/internacao.py`):**
- `Leito` — número, tipo (9 tipos: enfermaria, UTI adulto/neonatal, isolamento, maternidade, pediatria, observação, cirúrgico, semi-intensivo), andar/ala/quarto, status (livre/ocupado/reservado/limpeza/manutenção/bloqueado), flag de isolamento CCIH; propriedades `internacao_ativa` e `cor_status`
- `Internacao` — ciclo completo admissão → leito → alta; vínculo com paciente/leito/médico, origem do PA, campos de alta; propriedades `dias_internado` e `prescricao_ativa`
- `TransferenciaLeito` — histórico de transferências de leito
- `PrescricaoMedica` + `ItemPrescricao` — prescrição diária com itens (medicamento/solução/dieta/cuidado/procedimento/consultoria/exame/hemoderivado), dose, via, frequência, diluição, horários; suporte a assinatura ICP-Brasil
- `PrescricaoEnfermagem` — cuidados de enfermagem
- `ControlesPaciente` — sinais vitais + balanço hídrico (entradas/saídas) + eliminações; propriedades `total_entradas`, `total_saidas`, `balanco_hidrico`
- `EvolucaoMedica` (SOAP) e `EvolucaoEnfermagem` (por turno)

**Routes (`app/routes/internacao.py`):**
- `/internacao/leitos` — mapa visual por ala/andar
- `/internacao/leitos/novo` — cadastro de leito
- `/internacao/admitir` — admissão com busca HTMX de paciente
- `/internacao/<id>` — prontuário central (abas prescrição/evolução/controles/enfermagem)
- `/internacao/<id>/prescricao/nova` — nova prescrição médica (itens dinâmicos, copia a anterior)
- `/internacao/<id>/controles` — sinais vitais + balanço hídrico
- `/internacao/<id>/evolucao-medica`, `/evolucao-enfermagem`, `/prescricao-enfermagem`
- `/internacao/<id>/transferir` — transferência de leito
- `/internacao/<id>/alta` — alta hospitalar (gera laudo PDF)
- `/internacao/<id>/alta/pdf` — download do laudo
- `/internacao/` — lista de internações ativas

**Templates (`app/templates/internacao/`, 13 arquivos):**
- `mapa_leitos.html` — grid por ala, cores por status, marcação de isolamento (CCIH), polling HTMX 60s
- `form_leito.html`, `lista.html`, `admissao.html`, `prontuario.html` (4 abas)
- `prescricao.html` (tabela de itens dinâmica via JS), `controles.html` (balanço em tempo real)
- `evolucao_medica.html` (SOAP), `evolucao_enfermagem.html`, `prescricao_enfermagem.html`
- `transferencia.html`, `alta.html`

**Serviço de PDF (`app/services/pdf_service.py`):**
- `gerar_laudo_alta(internacao)` — laudo de alta em PDF via ReportLab (cabeçalho institucional, identificação do paciente, dados da internação, diagnóstico, resumo, condições de alta, orientações, tabela de medicamentos em uso, assinatura, rodapé)

**Integrações:**
- Blueprint registrado em `app/__init__.py`; navbar e dashboard atualizados com o módulo Internação
- Migração `5a50c2fd4cf2` aplicada — 9 tabelas criadas

**Detalhes implementados:**
- Mapa de leitos atualiza via HTMX (polling 60s), leitos de isolamento com marcação visual (CCIH)
- Status de leito atualizado automaticamente na admissão/transferência/alta
- Balanço hídrico: entradas (soro, medicação EV, ingesta oral, outros) vs saídas (diurese, drenos, vômitos, outros)
- Alta gera laudo em PDF via ReportLab
- Campos de assinatura ICP-Brasil (pyHanko) presentes nos models; a assinatura efetiva será integrada na Fase 4

---

### ✅ Fase 4 — Apoio Clínico (CONCLUÍDA)

**O que foi feito:** 7 submódulos, na ordem: Certificação Digital (transversal) → Exames → Farmácia → Nutrição → CCIH → Cirurgias → Maternidade.

**Certificação Digital (`/certificado/`):**
- Service `app/services/cert_service.py` com pyHanko: `assinar_pdf` (PAdES), `verificar_assinatura` (integridade + cobertura via `SignatureCoverageLevel.ENTIRE_FILE` — detecta adulteração), `gerar_qrcode_validacao/base64`, `inspecionar_certificado`, `gerar_certificado_teste` (autoassinado RSA-2048 para desenvolvimento)
- Models `CertificadoDigital` e `DocumentoAssinado` (hash SHA-256 + `codigo_validacao` para QR + vínculo polimórfico `origem_tipo/origem_id`)
- Upload de A1 (.p12/.pfx), geração de cert de teste (só em DEBUG), painel do usuário
- Helper reutilizável `assinar_documento()` em `routes/certificado.py` (assina + registra + gera QR) — pronto para os demais módulos consumirem
- Rota **pública** `/certificado/validar/<codigo>` (sem login) — destino do QR Code

**Exames (`/exames/`):** catálogo, solicitação médica com itens, fila de coleta (laboratório), lançamento de resultado/laudo (marca alterado), visualização. Models `ExameCatalogo`, `SolicitacaoExame`, `ItemExame`, `ResultadoExame`.

**Farmácia (`/farmacia/`):** cadastro de medicamento, controle de estoque por lote com validade (FEFO), entrada, dispensação vinculada à `PrescricaoMedica` da internação, histórico de movimentos (auditoria). Models `MedicamentoFarmacia`, `LoteEstoque`, `Dispensacao`, `ItemDispensacao`, `MovimentoEstoque`.

**Nutrição (`/nutricao/`):** prescrição dietética da nutricionista e mapa de dietas por ala. Model `PrescricaoDietetica`.

**CCIH (`/ccih/`):** notificação de infecção, painel de notificações + isolamentos ativos, início/encerramento de isolamento (marca `Leito.isolamento`), relatório base para SCIRAS. Models `NotificacaoInfeccao`, `IsolamentoPaciente`.

**Cirurgias (`/cirurgias/`):** solicitação, escala, mapa cirúrgico por sala, agendamento, fluxo de sala com carimbo de tempos (entrada/início/fim/saída), descrição cirúrgica, cadastro de salas. Models `SalaCirurgica`, `Cirurgia`.

**Maternidade (`/maternidade/`):** pré-natal com consultas de acompanhamento, registro de parto com múltiplos recém-nascidos (Apgar, peso, condição). Models `PreNatal`, `ConsultaPreNatal`, `Parto`, `RecemNascido`.

**Integração:** 7 blueprints registrados, dropdown "Apoio Clínico" na navbar, 7 cards no dashboard. Migração `d125303c4dd3` aplicada — 20 tabelas criadas.

**Verificação:** app sobe, 30 templates renderizam com dados reais, fluxo de assinatura testado ponta a ponta (assinar → registrar → validação pública íntegra).

**Assinatura digital plugada nas telas clínicas (✅):**
- Botão "Assinar" na **prescrição médica** (prontuário), em cada **evolução médica** e no **laudo de exame**. O fluxo gera um PDF do documento (`pdf_service.gerar_pdf_prescricao/evolucao_medica/laudo_exame`), assina via `assinar_documento()` e sela o registro.
- **Travamento pós-assinatura:** prescrição assinada não é reeditada; laudo assinado bloqueia novo lançamento de resultado. O PDF assinado detecta qualquer alteração posterior (cobertura PAdES).
- **Carimbo de tempo (TSA):** `assinar_pdf` usa `CERT_TIMESTAMP_URL` (Safeweb por padrão) com **degradação graciosa** — se o TSA estiver inacessível, assina sem timestamp e registra aviso no log, sem quebrar o fluxo. Em produção com internet liberada, o carimbo é aplicado automaticamente.
- Cada documento assinado gera QR Code e é validável publicamente em `/certificado/validar/<codigo>`.

**Pendências conhecidas (evoluir quando houver certificado real):**
- **Fluxo de senha (PIN) do certificado A1 em produção:** hoje o cert de teste usa senha fixa. Para o A1 real, será preciso solicitar a senha ao profissional no momento de assinar (o campo `cert_senha` no POST já é lido pelo helper).
- Validação da **cadeia** ICP-Brasil (`trust_roots`) não está ativada — só a integridade. Ativar carregando as ACs raiz da ICP-Brasil no `ValidationContext` quando houver certificado real.
- Assinatura plugada em **todos** os documentos clínicos assináveis: prescrição médica, evolução médica, laudo de exame, evolução de enfermagem, prescrição de enfermagem e descrição cirúrgica. Cada um gera PDF, assina, sela e gera QR de validação. Migração `75fb9b22d82e` adicionou `pdf_path` às tabelas de enfermagem.

**Certificado em nuvem (fase futura):**
- Integração com certificadoras em nuvem (BirdID, RemoteID, etc.) e A3 (token/smartcard) — permite assinar autorizando via app no celular (biometria/OTP). Depende de contratar uma certificadora e usar a API/protocolo dela. Documentado como evolução futura.

---

## Como Adquirir um Certificado ICP-Brasil (para produção)

O sistema já assina documentos; falta apenas trocar o certificado de teste por um real.

- **Tipo recomendado:** **A1 e-CNPJ** (arquivo `.p12`/`.pfx`, validade 1 ano). Permite ao servidor assinar automaticamente, sem token físico. Evite A3 (token/smartcard) no servidor — exige o dispositivo plugado.
- **Onde comprar:** Autoridades Certificadoras credenciadas pela ICP-Brasil (Serasa, Certisign, Valid, Soluti, AC Safeweb, etc.). Exige validação presencial ou por vídeo. Custo aproximado de um A1 e-CNPJ: R$ 150–250/ano (confirmar com a AC).
- **Para prontuário eletrônico (PEP):** considere futuramente a certificação **SBIS/CFM**, que permite dispensa do papel com conformidade plena.
- **Como instalar no SGHSC:** faça upload do `.p12` em `/certificado/upload` (ou aponte `CERT_STORAGE_PATH` para o arquivo). Nenhuma mudança de código é necessária — o fluxo de assinatura já está pronto.

---

### ✅ Fase 5 — Administrativo (CONCLUÍDA)

8 submódulos administrativos. Ordem seguida: Estoque → Compras → Financeiro → Faturamento SUS → Convênios → Patrimônio → RH → Manutenção.

**Estoque / Almoxarifado (`/estoque/`):** produtos (materiais e medicamentos), locais de estoque, saldo por local, movimentações (entrada/saída/transferência/ajuste), requisições de material, inventário com divergência. Ponto de pedido (estoque mínimo). Models: `LocalEstoque`, `ProdutoEstoque`, `SaldoEstoque`, `MovimentoEstoqueAlmox`, `RequisicaoMaterial`+`ItemRequisicao`, `Inventario`+`ItemInventario`.

**Compras (`/compras/`):** fornecedores, solicitações de compra, cotações, pedidos, recebimento. **O recebimento alimenta o estoque automaticamente** (cria saldo + movimento de entrada). Models: `Fornecedor`, `SolicitacaoCompra`, `Cotacao`, `PedidoCompra`, `Recebimento`.

**Financeiro (`/financeiro/`):** contas a pagar/receber com vencimento e baixa, fluxo de caixa (a baixa de conta lança no caixa automaticamente), categorias/plano de contas. Models: `CategoriaFinanceira`, `Conta`, `LancamentoCaixa`.

**Faturamento SUS (`/faturamento/`):** guias AIH/APAC/BPA com procedimentos, competência, valores; catálogo SIGTAP. Models: `ProcedimentoSIGTAP`, `GuiaFaturamento`+`ItemGuiaFaturamento`.
> ⚠️ A **exportação no layout magnético oficial do DATASUS** (SISAIH01, BPA-MAG) é um stub — depende das tabelas SIGTAP oficiais e do layout binário específico. Os dados estruturados estão prontos; o gerador de arquivo será implementado quando as tabelas oficiais forem importadas.

**Convênios (`/convenios/`):** operadoras, catálogo CBHPM/TUSS, guias TISS (consulta/SP-SADT/internação/honorário) com autorização e glosa. Models: `Convenio`, `ProcedimentoCBHPM`, `GuiaConvenio`+`ItemGuiaConvenio`.

**Patrimônio (`/patrimonio/`):** bens/equipamentos, localização, movimentação, **depreciação linear** (valor atual estimado calculado). Models: `BemPatrimonial`, `MovimentacaoBem`.

**RH (`/rh/`):** funcionários (vinculáveis a `Usuario`), setores, escalas de plantão. Models: `Setor`, `Funcionario`, `EscalaPlantao`.

**Manutenção (`/manutencao/`):** ordens de serviço (abertura → execução → encerramento com carimbo de tempos), corretiva/preventiva (com recorrência), vínculo opcional a bem patrimonial. Model: `OrdemServico`.

**Integração:** 8 blueprints registrados, dropdown "Administrativo" na navbar, 8 cards no dashboard. Migração `f26b8ccb9b91` aplicada — 31 tabelas criadas.

**Verificação:** app sobe, 34 templates renderizam com dados reais, rotas respondem, fluxos integrados testados (recebimento→estoque, baixa→caixa, depreciação).

---

### ✅ Fase 6 — Gestão e Compliance (CONCLUÍDA)

**Dashboard gerencial (`/relatorios/`):** indicadores agregados dos módulos assistenciais via `services/indicadores_service.py` — taxa de ocupação e distribuição de leitos, giro de leitos, média de permanência, altas/óbitos, produção (atendimentos PA, consultas, novos pacientes). Filtro por período (7/30/90 dias). Model: nenhum (consome dados existentes).

**PGRSS (`/residuos/`):** gestão de resíduos por grupo (A infectante, B químico, C radioativo, D comum, E perfurocortante — RDC ANVISA 222/2018), pesagem, painel com totais por grupo, coletas externas com manifesto (MTR) e destinação final. Models: `RegistroResiduo`, `ColetaResiduo`.

**RNDS (`/rnds/`):** fila de envio no padrão FHIR R4, geração do recurso `Patient` (mapeamento CNS/CPF/nome/sexo/nascimento), status de envio, payload FHIR visível. Model: `RegistroRNDS`.
> ⚠️ O **envio efetivo ao barramento nacional da RNDS** é um stub — requer certificado ICP-Brasil credenciado, cadastro no DATASUS e conexão autenticada (X.509 + OAuth) com o endpoint oficial. A geração do payload FHIR e a fila estão prontas; a transmissão real será plugada com as credenciais oficiais.

**Integração:** 3 blueprints registrados, dropdown "Gestão" na navbar, 3 cards no dashboard. Migração `352f70fe1d77` aplicada — 3 tabelas criadas.

**Verificação:** app sobe, 7 templates renderizam, rotas respondem, fluxos testados (resíduo→coleta, geração FHIR Patient com gender male/female correto).

---

## 🎉 Roadmap concluído

As 6 fases planejadas estão implementadas. O SGHSC cobre o ciclo hospitalar completo:
base/autenticação → porta de entrada (pacientes/emergência/ambulatório) → internação →
apoio clínico (exames/farmácia/nutrição/CCIH/cirurgias/maternidade/certificação digital) →
administrativo (estoque/compras/financeiro/faturamento/patrimônio/RH/manutenção) →
gestão e compliance (indicadores/PGRSS/RNDS).

**Pendências que dependem de credenciais/tabelas externas (documentadas nas fases):**
- Certificado ICP-Brasil real (A1) para assinatura com validade jurídica plena + fluxo de PIN em produção
- Validação da cadeia ICP-Brasil (`trust_roots`) na verificação de assinatura
- Exportação DATASUS no layout magnético oficial (depende das tabelas SIGTAP)
- Transmissão real à RNDS (depende de credenciamento no DATASUS)

---

## Integrações Externas Planejadas

| Integração | Quando | Biblioteca/API |
|------------|--------|----------------|
| ViaCEP | Fase 2 ✅ | Fetch JS (lado cliente) |
| DATASUS / SIGTAP | Fase 5 (estrutura ✅; export magnético pendente) | Tabelas locais + download periódico |
| CNES (dados da unidade) | Fase 5 | API CNES (DataSUS) |
| ICP-Brasil (assinatura) | Fase 4 ✅ (cert real pendente) | pyHanko + cryptography |
| RNDS | Fase 6 (payload FHIR ✅; envio pendente de credenciamento) | FHIR R4 REST API (certificado gov.br) |
| CID-10 | Fase 3 (campo livre por ora; tabela na Fase 4) | Tabela local (CSV importado) |
| CBHPM / TUSS | Fase 5 ✅ | Tabela local |

---

## Decisões Técnicas Tomadas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Frontend | Jinja2 + HTMX | Sem build step, tudo no Flask, interatividade sem JS pesado |
| Assinatura digital | pyHanko | Pure Python, sem compilação Cython, suporta PAdES/ICP-Brasil |
| PKCS#11 (token A3) | Driver do fabricante via SO | python-pkcs11 não compila no Python 3.12; integração via OS |
| Porta PostgreSQL | 5444 externa | Porta 5432 e 5433 ocupadas por outros projetos no dev local |
| Porta Flask | 5050 externa | Porta 5000 ocupada por outro projeto |
| Número de prontuário | `ANO-NNNNNN` | Simples, legível, único por instituição |
| Número de atendimento PA | `PAAAAAMMDDNNNN` | Rastreabilidade por data |
| Número de internação | `INTAAAAMMDDNNNN` | Rastreabilidade por data |
| Número de prescrição | `RXAAAAMMDDNNNN` | Rastreabilidade por data |
| Laudo de alta | ReportLab (PDF) | Simples, sem dependências pesadas |
| Assinatura digital | A1 (arquivo) no servidor | Assinatura automática sem token físico; A3 inviável no backend |
| Cert. de desenvolvimento | Autoassinado RSA-2048 | Valida o fluxo pyHanko sem custo; trocar por A1 real em produção |
| Validação de documento | Hash SHA-256 + QR público | Qualquer um confere autenticidade sem login |

---

## Como Retomar em Nova Sessão

1. Leia este arquivo (`docs/PROJECT_STATE.md`)
2. Verifique a última fase concluída na seção "Status das Fases"
3. Leia os arquivos da próxima fase listados em "O que precisa ser feito"
4. Confira a estrutura atual com `ls backend/app/models/` e `ls backend/app/routes/`
5. Suba o ambiente com `docker compose up -d` e confirme que está rodando
6. Comece pela criação dos models, depois routes, depois templates (nessa ordem)

**Frase para nova sessão:**
> "Estou trabalhando no SGHSC. Leia o arquivo `/home/romarck/Documentos/Projetos/SGHSC/docs/PROJECT_STATE.md` e me diga qual é a próxima fase a implementar."
