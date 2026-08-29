"""
models/__init__.py — Exporta todos os modelos para o Flask-Migrate detectar.

Importe SEMPRE daqui para garantir que as migrações capturem todos os modelos.
"""

from .ambulatorio import (
    AgendaAmbulatorio,
    ConsultaAmbulatorial,
    DiaSemana,
    StatusConsulta,
    TipoConsulta,
)
from .auditoria import AcaoAuditoria, LogAcesso
from .ccih import (
    IsolamentoPaciente,
    NotificacaoInfeccao,
    StatusIsolamento,
    StatusNotificacao,
    TipoInfeccao,
    TipoPrecaucao,
)

# --- Fase 4: Apoio Clínico ---
from .certificado import (
    CertificadoDigital,
    DocumentoAssinado,
    StatusDocumento,
    TipoCertificado,
    TipoDocumentoAssinado,
)
from .cirurgia import (
    Cirurgia,
    PorteCirurgico,
    SalaCirurgica,
    StatusCirurgia,
    TipoAnestesia,
    TipoCirurgia,
)
from .compras import (
    Cotacao,
    Fornecedor,
    ItemPedidoCompra,
    ItemSolicitacaoCompra,
    PedidoCompra,
    Recebimento,
    SolicitacaoCompra,
    StatusPedido,
    StatusSolicitacaoCompra,
)
from .convenios import (
    Convenio,
    GuiaConvenio,
    ItemGuiaConvenio,
    ProcedimentoCBHPM,
    StatusGuia,
    TipoGuia,
)
from .emergencia import (
    AtendimentoEmergencia,
    ClassificacaoManchester,
    MotivoSaidaEmergencia,
    StatusAtendimentoEmergencia,
    TriagemManchester,
)

# --- Fase 5: Administrativo ---
from .estoque import (
    CategoriaProduto,
    Inventario,
    ItemInventario,
    ItemRequisicao,
    LocalEstoque,
    MovimentoEstoqueAlmox,
    ProdutoEstoque,
    RequisicaoMaterial,
    SaldoEstoque,
    StatusInventario,
    StatusRequisicao,
    TipoMovimento,
    UnidadeMedida,
)
from .exame import (
    CategoriaExame,
    ExameCatalogo,
    ItemExame,
    OrigemExame,
    PrioridadeExame,
    ResultadoExame,
    SolicitacaoExame,
    StatusSolicitacaoExame,
)
from .farmacia import (
    Dispensacao,
    FormaFarmaceutica,
    ItemDispensacao,
    LoteEstoque,
    MedicamentoFarmacia,
    MovimentoEstoque,
    StatusDispensacao,
    TipoMovimentoEstoque,
)
from .faturamento import (
    GuiaFaturamento,
    ItemGuiaFaturamento,
    ProcedimentoSIGTAP,
    StatusFaturamento,
    TipoProducao,
)
from .financeiro import (
    CategoriaFinanceira,
    Conta,
    LancamentoCaixa,
    StatusConta,
    TipoConta,
    TipoLancamento,
)
from .internacao import (
    CondicaoAlta,
    ControlesPaciente,
    EvolucaoEnfermagem,
    EvolucaoMedica,
    FrequenciaAdministracao,
    Internacao,
    ItemPrescricao,
    Leito,
    PrescricaoEnfermagem,
    PrescricaoMedica,
    StatusInternacao,
    StatusItemPrescricao,
    StatusLeito,
    TipoAlta,
    TipoInternacao,
    TipoItemPrescricao,
    TipoLeito,
    TransferenciaLeito,
    ViaAdministracao,
)
from .manutencao import OrdemServico, PrioridadeOS, StatusOS, TipoManutencao
from .maternidade import (
    ClassificacaoRisco,
    CondicaoNascimento,
    ConsultaPreNatal,
    Parto,
    PreNatal,
    RecemNascido,
    SexoRN,
    TipoParto,
)
from .nutricao import (
    ConsistenciaDieta,
    PrescricaoDietetica,
    StatusPrescricaoDieta,
    TipoDieta,
    ViaAlimentacao,
)
from .paciente import (
    EstadoCivil,
    Paciente,
    RacaCor,
    Sexo,
    StatusPaciente,
    TipoLogradouro,
    TipoSanguineo,
)
from .patrimonio import BemPatrimonial, EstadoConservacao, MovimentacaoBem, SituacaoBem
from .prontuario import EntradaProntuario, Prontuario, TipoEntradaProntuario

# --- Fase 6: Gestão e Compliance ---
from .residuos import ColetaResiduo, GrupoResiduo, RegistroResiduo, StatusColeta
from .rh import EscalaPlantao, Funcionario, Setor, StatusFuncionario, TipoVinculo, TurnoPlantao
from .rnds import RegistroRNDS, StatusEnvioRNDS, TipoRecursoFHIR
from .usuario import Perfil, Permissao, StatusUsuario, TipoPerfil, Usuario

__all__ = [
    # Usuários / RBAC
    "Usuario", "Perfil", "Permissao", "StatusUsuario", "TipoPerfil",
    # Paciente
    "Paciente", "Sexo", "RacaCor", "EstadoCivil", "TipoSanguineo",
    "StatusPaciente", "TipoLogradouro",
    # Prontuário
    "Prontuario", "EntradaProntuario", "TipoEntradaProntuario",
    # Emergência
    "AtendimentoEmergencia", "TriagemManchester",
    "ClassificacaoManchester", "MotivoSaidaEmergencia", "StatusAtendimentoEmergencia",
    # Ambulatório
    "AgendaAmbulatorio", "ConsultaAmbulatorial",
    "StatusConsulta", "TipoConsulta", "DiaSemana",
    # Internação
    "Leito", "Internacao", "TransferenciaLeito",
    "PrescricaoMedica", "ItemPrescricao",
    "PrescricaoEnfermagem", "ControlesPaciente",
    "EvolucaoMedica", "EvolucaoEnfermagem",
    "TipoLeito", "StatusLeito", "TipoInternacao", "TipoAlta", "CondicaoAlta", "StatusInternacao",
    "ViaAdministracao", "FrequenciaAdministracao", "TipoItemPrescricao", "StatusItemPrescricao",
    # Certificação digital
    "CertificadoDigital", "DocumentoAssinado",
    "TipoCertificado", "TipoDocumentoAssinado", "StatusDocumento",
    # Exames
    "ExameCatalogo", "SolicitacaoExame", "ItemExame", "ResultadoExame",
    "CategoriaExame", "PrioridadeExame", "StatusSolicitacaoExame", "OrigemExame",
    # Farmácia
    "MedicamentoFarmacia", "LoteEstoque", "Dispensacao", "ItemDispensacao", "MovimentoEstoque",
    "FormaFarmaceutica", "TipoMovimentoEstoque", "StatusDispensacao",
    # Nutrição
    "PrescricaoDietetica",
    "TipoDieta", "ConsistenciaDieta", "ViaAlimentacao", "StatusPrescricaoDieta",
    # CCIH
    "NotificacaoInfeccao", "IsolamentoPaciente",
    "TipoInfeccao", "TipoPrecaucao", "StatusNotificacao", "StatusIsolamento",
    # Cirurgias
    "SalaCirurgica", "Cirurgia",
    "TipoCirurgia", "PorteCirurgico", "TipoAnestesia", "StatusCirurgia",
    # Maternidade
    "PreNatal", "ConsultaPreNatal", "Parto", "RecemNascido",
    "TipoParto", "ClassificacaoRisco", "SexoRN", "CondicaoNascimento",
    # Estoque
    "LocalEstoque", "ProdutoEstoque", "SaldoEstoque", "MovimentoEstoqueAlmox",
    "RequisicaoMaterial", "ItemRequisicao", "Inventario", "ItemInventario",
    "CategoriaProduto", "UnidadeMedida", "TipoMovimento", "StatusRequisicao", "StatusInventario",
    # Compras
    "Fornecedor", "SolicitacaoCompra", "ItemSolicitacaoCompra", "Cotacao",
    "PedidoCompra", "ItemPedidoCompra", "Recebimento",
    "StatusSolicitacaoCompra", "StatusPedido",
    # Financeiro
    "CategoriaFinanceira", "Conta", "LancamentoCaixa",
    "TipoConta", "StatusConta", "TipoLancamento",
    # Faturamento SUS
    "ProcedimentoSIGTAP", "GuiaFaturamento", "ItemGuiaFaturamento",
    "TipoProducao", "StatusFaturamento",
    # Convênios
    "Convenio", "ProcedimentoCBHPM", "GuiaConvenio", "ItemGuiaConvenio",
    "TipoGuia", "StatusGuia",
    # Patrimônio
    "BemPatrimonial", "MovimentacaoBem", "SituacaoBem", "EstadoConservacao",
    # RH
    "Setor", "Funcionario", "EscalaPlantao",
    "TipoVinculo", "StatusFuncionario", "TurnoPlantao",
    # Manutenção
    "OrdemServico", "TipoManutencao", "PrioridadeOS", "StatusOS",
    # Resíduos (PGRSS)
    "RegistroResiduo", "ColetaResiduo", "GrupoResiduo", "StatusColeta",
    # RNDS
    "RegistroRNDS", "TipoRecursoFHIR", "StatusEnvioRNDS",
]
