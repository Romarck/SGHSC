# Modelo de Dados: SGHSC

**Data:** 2026-08-28
**Autor:** @architect
**Comando:** `*datamodel`
**Fonte:** SQLAlchemy models em `backend/app/models/` (24 arquivos)

> Documento gerado a partir de **leitura direta dos models**. Reflete o schema real
> mapeado pelo ORM. ORM: SQLAlchemy 2 / Flask-SQLAlchemy; migrações via Alembic (7 revisões).

---

## 1. Convenções gerais

- **PK:** toda tabela tem `id` inteiro autoincremental como chave primária.
- **Enums:** persistidos como `db.Enum(...)` a partir de `enum.Enum` do Python (armazenados
  pelo **nome** do membro no PostgreSQL).
- **Timestamps:** `DateTime(timezone=True)`, default UTC (`datetime.now(timezone.utc)`).
- **Auditoria:** convenção `criado_em` / `atualizado_em` (`onupdate`) / `criado_por_id`
  (FK → `usuarios.id`) nos models principais.
- **Numeração de documentos:** campo `numero` único e indexado, padrão `PREFIXOAAAAMMDDNNNN`
  ou `ANO-NNNNNN`.
- **Assinatura digital:** models clínicos assináveis têm `assinada`/`assinado`,
  `assinada_em`, `assinatura_hash` (SHA/PAdES) e `pdf_path`. Alguns referenciam
  `documentos_assinados.id`.
- **Nomenclatura:** tabelas e colunas em **português**.

### Totais (verificados)
| Item | Qtd |
|------|-----|
| Arquivos de model | 24 |
| Tabelas (models `db.Model`) | ~70 |
| Tabela associativa (M:N) | 1 (`perfil_permissao`) |
| Enums | ~80 |
| Migrações Alembic | 7 |

---

## 2. Visão por domínios

```
[Acesso/RBAC]  Usuario ─┬─ Perfil ─┬─(M:N)─ Permissao
                        │          
                        └── (criado_por_id em quase todas as tabelas)

[Paciente]     Paciente ─1:1─ Prontuario ─1:N─ EntradaProntuario
                  │
    ┌─────────────┼───────────────────────────────┐
[Porta de entrada]│                                 │
   AtendimentoEmergencia ─1:1─ TriagemManchester    ConsultaAmbulatorial ─N:1─ AgendaAmbulatorio
                  │
[Internação]   Internacao ─N:1─ Leito
                  ├─1:N─ PrescricaoMedica ─1:N─ ItemPrescricao
                  ├─1:N─ PrescricaoEnfermagem
                  ├─1:N─ ControlesPaciente
                  ├─1:N─ EvolucaoMedica / EvolucaoEnfermagem
                  ├─1:N─ TransferenciaLeito
                  └─1:N─ PrescricaoDietetica / NotificacaoInfeccao / IsolamentoPaciente / Cirurgia / Parto

[Apoio clínico] SolicitacaoExame ─1:N─ ItemExame ─1:1─ ResultadoExame
                MedicamentoFarmacia ─1:N─ LoteEstoque ; Dispensacao ─1:N─ ItemDispensacao ; MovimentoEstoque
                CertificadoDigital ─1:N─ DocumentoAssinado
                PreNatal ─1:N─ ConsultaPreNatal ; Parto ─1:N─ RecemNascido

[Administrativo] ProdutoEstoque ─1:N─ SaldoEstoque ; RequisicaoMaterial ─1:N─ ItemRequisicao ; Inventario ─1:N─ ItemInventario
                Fornecedor ; SolicitacaoCompra ─1:N─ Item ; Cotacao ; PedidoCompra ─1:N─ Item ; Recebimento
                CategoriaFinanceira ; Conta ; LancamentoCaixa
                GuiaFaturamento ─1:N─ ItemGuiaFaturamento ; ProcedimentoSIGTAP
                GuiaConvenio ─1:N─ ItemGuiaConvenio ; Convenio ; ProcedimentoCBHPM
                BemPatrimonial ─1:N─ MovimentacaoBem
                Setor ; Funcionario ─1:N─ EscalaPlantao ; OrdemServico

[Compliance]   RegistroResiduo ─N:1─ ColetaResiduo ; RegistroRNDS
```

---

## 3. Acesso e Controle (RBAC) — `usuario.py`

### `usuarios`
| Coluna | Tipo | Notas |
|--------|------|-------|
| id | Integer PK | |
| nome | String(150) | not null |
| email | String(150) | unique, not null, index |
| username | String(50) | unique, not null, index |
| senha_hash | String(255) | not null (property `senha` faz o Bcrypt) |
| cpf | String(14) | unique, nullable |
| conselho_tipo / conselho_numero / conselho_uf | String | CRM/COREN/CRF... |
| especialidade | String(100) | |
| cert_digital_path | String(500) | caminho .p12/.pfx |
| cert_validade | DateTime(tz) | |
| perfil_id | FK → perfis.id | not null |
| status | Enum `StatusUsuario` | default ATIVO |
| deve_trocar_senha | Boolean | default True |
| ultimo_login / tentativas_login / bloqueado_ate | | bloqueio após 5 falhas / 30 min |
| criado_em / atualizado_em / criado_por_id | auditoria | criado_por_id → usuarios.id (auto-ref) |

### `perfis`
`id`, `nome` (unique), `tipo` (Enum `TipoPerfil`), `descricao`, `ativo`, `criado_em`.
Relacionamentos: M:N com `permissoes`; 1:N com `usuarios`.

### `permissoes`
`id`, `codigo` (unique, index — ex: `pacientes.criar`), `descricao`, `modulo` (index).

### `perfil_permissao` (associativa M:N)
`perfil_id` (PK, FK), `permissao_id` (PK, FK).

**Enums:** `StatusUsuario` (ativo/inativo/bloqueado), `TipoPerfil` (15 tipos: administrador,
medico, enfermeiro, tecnico_enfermagem, farmaceutico, recepcionista, faturamento, financeiro,
almoxarife, nutricionista, fisioterapeuta, assistente_social, laboratorista, radiologista, gestor).

> ⚠️ **Nota de auditoria:** o método `Usuario.tem_permissao()` existe mas **não é chamado nas
> rotas** — a granularidade de permissão está modelada porém não aplicada (ver `architecture.md`, S1).

---

## 4. Paciente e Prontuário

### `pacientes` — `paciente.py`
Model central (~40 colunas). Grupos: identificação (`nome`, `nome_social`, `data_nascimento`,
`sexo`, `raca_cor`, `estado_civil`, `naturalidade`, `nacionalidade`, `tipo_sanguineo`, `status`),
documentos (`cpf` unique, `rg*`, `cns` unique, `cns_provisorio`, `certidao_nascimento`,
`titulo_eleitor`), saúde (`plano_saude`, `numero_carteirinha`, `alergias`, `observacoes_clinicas`,
`data_obito`, `causa_obito`), socioeconômicos (`escolaridade`, `ocupacao`, `religiao`), endereço
(`cep`, `tipo_logradouro`, `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `uf`, `zona`),
contato (`telefone`, `telefone2`, `email`), responsável, filiação (`nome_mae`, `nome_pai`) e auditoria.
Propriedades calculadas: `idade`, `nome_exibicao`, `endereco_formatado`.
Relações: 1:1 `prontuario`; 1:N `atendimentos_emergencia`, `consultas_ambulatoriais`.
**Enums:** `Sexo`, `RacaCor`, `EstadoCivil`, `TipoSanguineo`, `StatusPaciente`, `TipoLogradouro`.

### `prontuarios` — `prontuario.py`
`id`, `numero` (unique `ANO-NNNNNN`), `paciente_id` (FK unique → 1:1), `aberto_em`,
`aberto_por_id`, `observacoes`. Relação 1:N com `entradas_prontuario`.

### `entradas_prontuario`
`id`, `prontuario_id` (FK), `tipo` (Enum `TipoEntradaProntuario`), `titulo`, `conteudo`,
`registrado_em`, `registrado_por_id`, + campos de assinatura (`assinado`, `assinado_em`,
`assinado_por_id`, `assinatura_hash`, `pdf_path`).
**Enum:** `TipoEntradaProntuario` (anamnese, evolução médica/enfermagem, prescrição, resultado
exame, laudo, alta, transferência, óbito, nota cirúrgica, receituário, atestado, outro).

---

## 5. Porta de Entrada

### `atendimentos_emergencia` — `emergencia.py`
`numero` (unique), `paciente_id` (FK), `chegada_em`, `registrado_por_id`, `modo_chegada`,
`status` (Enum), `medico_id`, `inicio_atendimento_em`, `hipotese_diagnostica`, `cid10_principal`,
`conduta`, `anamnese`, `exame_fisico`, saída (`saida_em`, `motivo_saida`, `destino_internacao`,
`destino_transferencia`). 1:1 com `triagens_manchester` (cascade delete-orphan).
Propriedades: `tempo_espera_minutos`, `em_espera`.
**Enums:** `StatusAtendimentoEmergencia`, `MotivoSaidaEmergencia`.

### `triagens_manchester`
`atendimento_id` (FK), `queixa_principal`, `discriminador`, `classificacao` (Enum
`ClassificacaoManchester`: vermelho/laranja/amarelo/verde/azul), sinais vitais (PA sist/diast,
FC, FR, temperatura, SatO2, glicemia, peso, altura, escala_dor 0–10), `realizada_em`,
`realizada_por_id`, `observacoes`. Constante `TEMPO_ALVO_MANCHESTER` mapeia cor → minutos.

### `agendas_ambulatorio` — `ambulatorio.py`
`medico_id` (FK), `especialidade`, `dia_semana` (Enum `DiaSemana`), `hora_inicio`, `hora_fim`,
`duracao_consulta_min`, `vagas_total`, `vagas_reserva`, `ativo`, `local`. Propriedade
`vagas_disponiveis_hoje`.

### `consultas_ambulatoriais`
`numero` (unique), `paciente_id`, `medico_id`, `agenda_id` (FK), agendamento (`data`, `horario`,
`tipo` Enum `TipoConsulta`, `especialidade`, `status` Enum `StatusConsulta`, `agendado_por_id`),
atendimento (`anamnese`, `exame_fisico`, `hipotese_diagnostica`, `cid10_principal/secundario`,
`conduta`, `prescricao`, sinais vitais), retorno (`retorno_data`, `retorno_dias`), faturamento
(`procedimento_sus`, `cbo_medico`). Propriedade `duracao_minutos`.

---

## 6. Internação — `internacao.py`

### `leitos`
`numero` (unique), `tipo` (Enum `TipoLeito` — 9 tipos), `andar`, `ala`, `quarto`,
`status` (Enum `StatusLeito`), `isolamento` (bool CCIH), `motivo_bloqueio`, `ativo`, auditoria.
Propriedades: `internacao_ativa`, `cor_status`.

### `internacoes`
`numero` (unique), `paciente_id`, `leito_id`, `medico_responsavel_id`, admissão (`admissao_em`,
`tipo` Enum `TipoInternacao`, `motivo`, `hipotese_diagnostica`, `cid10_principal/secundario`,
`convenio`, `numero_aih`, `admitido_por_id`), origem (`origem_pa`, `atendimento_emergencia_id` FK),
`status` (Enum `StatusInternacao`), alta (`alta_em`, `tipo_alta`, `condicao_alta`,
`diagnostico_principal_alta`, `resumo_alta`, `orientacoes_alta`, `retorno_dias`, `alta_assinada`,
`alta_pdf_path`, `dado_alta_por_id`), auditoria.
Relações 1:N: `prescricoes_medicas`, `prescricoes_enfermagem`, `controles`, `evolucoes_medicas`,
`evolucoes_enfermagem`, `transferencias`. Propriedades: `dias_internado`, `prescricao_ativa`.

### `transferencias_leito`
`internacao_id`, `leito_origem_id`, `leito_destino_id`, `motivo`, `realizada_em`, `realizada_por_id`.

### `prescricoes_medicas` ─1:N─ `itens_prescricao`
- **prescricoes_medicas:** `numero` (unique), `internacao_id`, `medico_id`, `data_prescricao`,
  `validade_horas`, `observacoes`, `ativa`, assinatura ICP-Brasil, auditoria.
- **itens_prescricao:** `prescricao_id`, `ordem`, `tipo` (Enum `TipoItemPrescricao`),
  `descricao`, `dose`, `via` (Enum `ViaAdministracao`), `frequencia` (Enum
  `FrequenciaAdministracao`), `frequencia_custom`, `duracao`, `horarios`, `diluicao`,
  `velocidade_infusao`, `observacoes`, `status` (Enum `StatusItemPrescricao`), suspensão.

### `prescricoes_enfermagem`
`internacao_id`, `enfermeiro_id`, `data_prescricao`, `conteudo`, `observacoes`, `ativa`, assinatura.

### `controles_paciente`
`internacao_id`, `registrado_em`, `registrado_por_id`, sinais vitais (PA, FC, FR, temperatura,
SatO2, glicemia, escala_dor, nível de consciência), **balanço hídrico** entradas (`soro_ev`,
`medicacao_ev`, `ingesta_oral`, `outros_entrada`) e saídas (`diurese`, `drenos`, `vomitos`,
`outros_saida`), eliminações. Propriedades: `total_entradas`, `total_saidas`, `balanco_hidrico`.

### `evolucoes_medicas`
`internacao_id`, `medico_id`, `registrado_em`, SOAP (`subjetivo`, `objetivo`, `avaliacao`,
`plano`, `evolucao_livre`), `cid10_atual`, assinatura ICP-Brasil.

### `evolucoes_enfermagem`
`internacao_id`, `profissional_id`, `registrado_em`, `turno` (manha/tarde/noite), `conteudo`,
`observacoes`, assinatura.

**Enums do módulo:** `TipoLeito`, `StatusLeito`, `TipoInternacao`, `TipoAlta`, `CondicaoAlta`,
`StatusInternacao`, `ViaAdministracao`, `FrequenciaAdministracao`, `TipoItemPrescricao`,
`StatusItemPrescricao`.

---

## 7. Apoio Clínico

### Certificação digital — `certificado.py`
- **certificados_digitais:** `usuario_id`, `tipo` (Enum `TipoCertificado` A1/A3/teste), `titular`,
  `emissor`, `numero_serie`, `arquivo_path`, `valido_de/ate`, `ativo`. Propriedades: `vigente`,
  `dias_para_expirar`.
- **documentos_assinados:** `codigo_validacao` (unique — usado no QR público), `tipo` (Enum
  `TipoDocumentoAssinado`), `titulo`, `hash_documento` (SHA-256, index), `pdf_path`, `qrcode_path`,
  `assinante_id`, `assinante_nome`, `certificado_id` (FK), `paciente_id` (FK), referência
  **polimórfica** (`origem_tipo`, `origem_id`), `status` (Enum `StatusDocumento`), `assinado_em`.

### Exames — `exame.py`
- **exames_catalogo:** `codigo` (unique), `nome`, `categoria` (Enum `CategoriaExame`), `material`,
  `unidade_medida`, `valor_referencia`, `prazo_horas`, `ativo`.
- **solicitacoes_exame:** `numero` (unique), `paciente_id`, `solicitante_id`, `origem` (Enum
  `OrigemExame`), FKs opcionais `internacao_id`/`atendimento_emergencia_id`/`consulta_id`,
  `prioridade` (Enum), `status` (Enum `StatusSolicitacaoExame`), `indicacao_clinica`, `cid10`,
  coleta (`coletado_em`, `coletado_por_id`). Propriedades `total_itens`, `itens_com_resultado`.
- **itens_exame:** `solicitacao_id`, `exame_catalogo_id` (FK opcional), `nome_exame` (snapshot).
  1:1 com `resultados_exame`.
- **resultados_exame:** `item_id` (FK unique), `valor`, `unidade`, `valor_referencia`, `laudo`,
  `alterado`, `arquivo_path`, `responsavel_id`, `liberado_em`, `assinado`, `documento_assinado_id` (FK).

### Farmácia — `farmacia.py`
- **medicamentos_farmacia:** `codigo` (unique), `nome`, `principio_ativo`, `concentracao`,
  `forma` (Enum `FormaFarmaceutica`), `unidade_dispensacao`, `controlado` (Portaria 344/98),
  `tipo_receituario`, `codigo_sus`, `estoque_minimo`, `ativo`. Propriedades `estoque_total`,
  `abaixo_minimo`, `descricao_completa`.
- **lotes_estoque:** `medicamento_id`, `numero_lote`, `validade` (index — FEFO), `quantidade`,
  `fabricante`. Propriedade `vencido`.
- **dispensacoes:** `numero` (unique), `paciente_id`, `prescricao_id` (FK →
  `prescricoes_medicas`), `internacao_id`, `status` (Enum `StatusDispensacao`), `farmaceutico_id`,
  `dispensado_em`. 1:N `itens_dispensacao`.
- **itens_dispensacao:** `dispensacao_id`, `medicamento_id`, `lote_id`, `quantidade`,
  `item_prescricao_id` (FK opcional → item da prescrição de origem).
- **movimentos_estoque:** auditoria de estoque de farmácia — `medicamento_id`, `lote_id`,
  `tipo` (Enum `TipoMovimentoEstoque`), `quantidade` (±), `saldo_apos`, `motivo`,
  `dispensacao_id`, `responsavel_id`, `registrado_em`.

### Nutrição — `nutricao.py`
- **prescricoes_dieteticas:** `internacao_id`, `nutricionista_id`, `data_prescricao`,
  `tipo_dieta` (Enum `TipoDieta`), `consistencia` (Enum), `via` (Enum `ViaAlimentacao`),
  `valor_calorico`, `fracionamento`, `restricoes`, `suplementos`, `status` (Enum
  `StatusPrescricaoDieta`).

### CCIH — `ccih.py`
- **notificacoes_infeccao:** `numero` (unique), `paciente_id`, `internacao_id`, `notificante_id`,
  `tipo` (Enum `TipoInfeccao`), `topografia`, `microrganismo`, `antibiograma`, `cid10`,
  `status` (Enum `StatusNotificacao`), `data_notificacao`, `data_encerramento`.
- **isolamentos_paciente:** `internacao_id`, `notificacao_id` (FK opcional), `tipo_precaucao`
  (Enum `TipoPrecaucao`), `motivo`, `microrganismo`, `status` (Enum `StatusIsolamento`),
  `iniciado_em`, `encerrado_em`, `prescrito_por_id`. Propriedade `cor_precaucao`.

### Cirurgias — `cirurgia.py`
- **salas_cirurgicas:** `nome` (unique), `descricao`, `ativa`.
- **cirurgias:** `numero` (unique), `paciente_id`, `internacao_id`, `cirurgiao_id`,
  `solicitante_id`, solicitação (`procedimento`, `codigo_procedimento`, `tipo` Enum `TipoCirurgia`,
  `porte` Enum `PorteCirurgico`, `tipo_anestesia` Enum `TipoAnestesia`, `cid10`, `indicacao`,
  `lateralidade`), agendamento (`sala_id`, `data_agendada`, `duracao_estimada_min`,
  `anestesista_id`), `status` (Enum `StatusCirurgia`), fluxo de sala (`entrada_sala_em`,
  `inicio_cirurgia_em`, `fim_cirurgia_em`, `saida_sala_em`), descrição cirúrgica
  (`descricao_cirurgica`, `achados`, `procedimento_realizado`, `intercorrencias`, `equipe`,
  `material_utilizado`), assinatura (`descricao_assinada`, `documento_assinado_id`).
  Propriedades: `duracao_real_min`, `cor_status`.

### Maternidade — `maternidade.py`
- **prenatais:** `gestante_id` (FK → pacientes), `dum`, `dpp`, GPA (`gestacoes`, `partos`,
  `abortos`, `cesareas`), `classificacao_risco` (Enum), `tipo_sanguineo`, `medico_id`, `ativo`.
  1:N `consultas_prenatal`.
- **consultas_prenatal:** `prenatal_id`, `data_consulta`, `idade_gestacional_semanas`, `peso`,
  `pressao_arterial`, `altura_uterina`, `bcf`, `movimentacao_fetal`, `edema`.
- **partos:** `numero` (unique), `gestante_id`, `internacao_id`, `prenatal_id`, `tipo` (Enum
  `TipoParto`), `data_parto`, `idade_gestacional_semanas`, `medico_id`, `tipo_anestesia`,
  `intercorrencias`, `descricao`. 1:N `recem_nascidos`.
- **recem_nascidos:** `parto_id`, `paciente_id` (opcional), `sexo` (Enum `SexoRN`), `condicao`
  (Enum `CondicaoNascimento`), `peso_gramas`, `comprimento_cm`, `perimetro_cefalico_cm`,
  `apgar_1min`, `apgar_5min`, `hora_nascimento`, `reanimacao`, `intercorrencias`. Propriedade
  `apgar_resumo`.

---

## 8. Administrativo

### Estoque / Almoxarifado — `estoque.py`
- **locais_estoque:** `nome` (unique), `descricao`, `principal`, `ativo`.
- **produtos_estoque:** `codigo` (unique), `nome`, `descricao`, `categoria` (Enum
  `CategoriaProduto`), `unidade` (Enum `UnidadeMedida`), `estoque_minimo/maximo`, `valor_medio`,
  `ativo`. Propriedades `estoque_total`, `abaixo_minimo`.
- **saldos_estoque:** `produto_id`, `local_id`, `quantidade`. **UniqueConstraint**
  (`produto_id`, `local_id`).
- **movimentos_estoque_almox:** `produto_id`, `local_id`, `local_destino_id`, `tipo` (Enum
  `TipoMovimento`), `quantidade` (±), `valor_unitario`, `motivo`, `requisicao_id`,
  `responsavel_id`, `registrado_em`.
- **requisicoes_material** ─1:N─ **itens_requisicao:** requisição de setor
  (`numero`, `setor_solicitante`, `solicitante_id`, `status` Enum `StatusRequisicao`);
  item (`produto_id`, `quantidade_solicitada`, `quantidade_atendida`).
- **inventarios** ─1:N─ **itens_inventario:** contagem física por local
  (`local_id`, `status` Enum `StatusInventario`, `responsavel_id`); item (`produto_id`,
  `saldo_sistema`, `contagem_fisica`, propriedade `divergencia`).

### Compras — `compras.py`
- **fornecedores:** `razao_social`, `nome_fantasia`, `cnpj` (unique), contato, `ativo`.
- **solicitacoes_compra** ─1:N─ **itens_solicitacao_compra:** `numero`, `solicitante_id`,
  `justificativa`, `status` (Enum `StatusSolicitacaoCompra`); item (`produto_id` opcional,
  `descricao`, `quantidade`).
- **cotacoes:** `solicitacao_id`, `fornecedor_id`, `valor_total`, `prazo_entrega_dias`,
  `condicao_pagamento`, `vencedora`.
- **pedidos_compra** ─1:N─ **itens_pedido_compra:** `numero`, `solicitacao_id`, `fornecedor_id`,
  `cotacao_id`, `valor_total`, `status` (Enum `StatusPedido`), `emitido_por_id`; item
  (`produto_id`, `descricao`, `quantidade`, `quantidade_recebida`, `valor_unitario`).
- **recebimentos:** `pedido_id`, `nota_fiscal`, `local_id`, `recebido_por_id`, `recebido_em`
  (o recebimento alimenta o estoque).

### Financeiro — `financeiro.py`
- **categorias_financeiras:** `nome` (unique), `tipo` (Enum `TipoLancamento`), `ativo`.
- **contas:** `descricao`, `tipo` (Enum `TipoConta` pagar/receber), `valor`, `vencimento`,
  `status` (Enum `StatusConta`), `categoria_id`, `fornecedor_id`, `pedido_compra_id`, `convenio`,
  `data_pagamento`, `valor_pago`. Propriedade `atrasada`.
- **lancamentos_caixa:** `descricao`, `tipo` (Enum `TipoLancamento`), `valor`, `data`,
  `categoria_id`, `conta_id` (baixa de conta lança no caixa), `registrado_por_id`.

### Faturamento SUS — `faturamento.py`
- **procedimentos_sigtap:** `codigo` (unique), `nome`, `complexidade`, `valor_sus`, `ativo`
  (tabela de referência).
- **guias_faturamento** ─1:N─ **itens_guia_faturamento:** `numero`, `tipo` (Enum `TipoProducao`
  AIH/APAC/BPA-I/BPA-C), `paciente_id`, `internacao_id`, `consulta_id`, `competencia` (AAAAMM),
  `cid_principal`, `procedimento_principal`, `valor_total`, `numero_aih_apac`, `status` (Enum
  `StatusFaturamento`); item (`procedimento_id`, `codigo_procedimento`, `descricao`,
  `quantidade`, `valor_unitario`, propriedade `valor_total`).
  > Exportação magnética DATASUS (SISAIH01/BPA-MAG) é stub documentado.

### Convênios — `convenios.py`
- **convenios:** `nome` (unique), `registro_ans`, `cnpj`, `tabela_preco`, `ativo`.
- **procedimentos_cbhpm:** `codigo` (unique TUSS), `nome`, `porte`, `valor_referencia`, `ativo`.
- **guias_convenio** ─1:N─ **itens_guia_convenio:** `numero`, `tipo` (Enum `TipoGuia`),
  `convenio_id`, `paciente_id`, `numero_carteirinha`, `senha_autorizacao`, `consulta_id`,
  `internacao_id`, `valor_total`, `valor_glosado`, `status` (Enum `StatusGuia`); item
  (`procedimento_id`, `codigo_procedimento`, `descricao`, `quantidade`, `valor_unitario`).

### Patrimônio — `patrimonio.py`
- **bens_patrimoniais:** `numero_patrimonio` (unique), `descricao`, `categoria`, `marca`,
  `modelo`, `numero_serie`, `localizacao`, `situacao` (Enum `SituacaoBem`), `estado` (Enum
  `EstadoConservacao`), `valor_aquisicao`, `data_aquisicao`, `vida_util_anos`. Propriedades
  `depreciacao_anual`, `valor_atual_estimado` (depreciação linear).
- **movimentacoes_bem:** `bem_id`, `localizacao_origem/destino`, `motivo`, `responsavel_id`, `data`.

### RH — `rh.py`
- **setores:** `nome` (unique), `responsavel_id`, `ativo`.
- **funcionarios:** `matricula` (unique), `nome`, `cpf` (unique), `cargo`, `setor_id`, `vinculo`
  (Enum `TipoVinculo`), `status` (Enum `StatusFuncionario`), conselho, contato, admissão/
  desligamento, `usuario_id` (FK opcional → usuarios).
- **escalas_plantao:** `funcionario_id`, `setor_id`, `data`, `turno` (Enum `TurnoPlantao`),
  `hora_inicio/fim`.

### Manutenção — `manutencao.py`
- **ordens_servico:** `numero` (unique), `titulo`, `descricao`, `tipo` (Enum `TipoManutencao`),
  `prioridade` (Enum `PrioridadeOS`), `status` (Enum `StatusOS`), `local`, `bem_id` (FK opcional),
  `solicitante_id`, `executor_id`, tempos (`aberta_em`, `iniciada_em`, `concluida_em`), `solucao`,
  `custo`, recorrência preventiva (`preventiva_intervalo_dias`, `proxima_preventiva`).
  Propriedade `cor_status`.

---

## 9. Gestão e Compliance

### Relatórios / Indicadores
Sem tabela própria. `services/indicadores_service.py` agrega dados dos módulos assistenciais
(ocupação de leitos, giro, permanência, altas/óbitos, produção).

### Resíduos (PGRSS) — `residuos.py`
- **registros_residuo:** `grupo` (Enum `GrupoResiduo` A–E, RDC ANVISA 222/2018), `origem_setor`,
  `peso_kg`, `descricao`, `acondicionamento`, `status` (Enum `StatusColeta`), `coleta_id` (FK),
  `registrado_por_id`, `gerado_em`. Propriedade `cor_grupo`.
- **coletas_residuo:** `numero` (unique), `empresa_coletora`, `numero_manifesto` (MTR),
  `peso_total_kg`, `destinacao_final`, `responsavel_id`, `coletado_em`. 1:N `registros_residuo`.

### RNDS (FHIR R4) — `rnds.py`
- **registros_rnds:** `tipo_recurso` (Enum `TipoRecursoFHIR`: Patient/Encounter/DiagnosticReport/
  Immunization/MedicationRequest/Condition), `paciente_id`, referência polimórfica (`origem_tipo`,
  `origem_id`), `payload_fhir` (JSON), `status` (Enum `StatusEnvioRNDS`), retorno do barramento
  (`protocolo_rnds`, `mensagem_retorno`, `tentativas`), `enviado_em`. Propriedade `cor_status`.
  > Envio real ao barramento nacional é stub (depende de credenciamento DATASUS + X.509/OAuth).

---

## 10. Observações e recomendações do modelo

1. **Referências polimórficas leves** (`origem_tipo`/`origem_id` em `documentos_assinados` e
   `registros_rnds`) não têm FK — a integridade referencial fica a cargo da aplicação. Aceitável,
   mas documentar o contrato dos valores possíveis.
2. **Snapshots de nome/código** (`nome_exame`, `codigo_procedimento`, `descricao` em itens de
   compra/faturamento) são intencionais para preservar histórico mesmo se o catálogo mudar — boa prática.
3. **Restrições de unicidade compostas:** apenas `saldos_estoque` (`produto_id`+`local_id`).
   Avaliar `UniqueConstraint` para `escalas_plantao` (funcionário+data+turno) e evitar duplicidade.
4. **Enums no PostgreSQL:** alterações em membros de Enum exigem migração cuidadosa (tipos ENUM
   nativos). Manter os `enum.Enum` estáveis ou padronizar como `String` + validação se houver
   volatilidade.
5. **CID-10 / SIGTAP / TUSS / CBHPM:** hoje em campos livres/tabelas de referência locais a
   popular. Documentado como integração externa (ver `architecture.md`).
6. **`criado_por_id`** é opcional (`nullable=True`) na maioria dos models — para trilha de
   auditoria completa (LGPD/PEP), avaliar torná-lo obrigatório nas operações com usuário logado.

---

## 11. Histórico de Mudanças

| Data | Mudança | Autor |
|------|---------|-------|
| 2026-08-28 | Versão inicial gerada a partir dos models | @architect (`*datamodel`) |

---

*Gerado pelo PDA-SQUAD v1.0.0 — comando `@architect *datamodel`*
