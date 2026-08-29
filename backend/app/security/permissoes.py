"""
security/permissoes.py — Catálogo de permissões RBAC e seed idempotente.

Story S-01 — @si C-01 / @architect S1.

- CATALOGO: lista de permissões no formato 'modulo.acao' com descrição e módulo.
- PERFIL_PERMISSOES: mapeia cada TipoPerfil ao conjunto de permissões.
    - ADMINISTRADOR não é listado aqui: tem acesso total (tratado no decorator).
    - Curinga 'modulo.*' concede todas as permissões do módulo.
- seed_permissoes(): cria/atualiza Permissao e associa aos Perfis. Idempotente —
  pode rodar a cada boot sem duplicar.
"""

from ..extensions import db
from ..models.usuario import Perfil, Permissao, TipoPerfil

# ---------------------------------------------------------------------------
# Catálogo de permissões (modulo.acao) → descrição
# ---------------------------------------------------------------------------

CATALOGO: dict[str, str] = {
    # Pacientes / prontuário
    "pacientes.ver": "Visualizar pacientes e prontuário",
    "pacientes.criar": "Cadastrar/editar pacientes",
    # Emergência
    "emergencia.ver": "Visualizar fila da emergência",
    "emergencia.triar": "Registrar chegada e triagem",
    "emergencia.atender": "Atender (conduta médica) na emergência",
    # Ambulatório
    "ambulatorio.ver": "Visualizar agenda/consultas",
    "ambulatorio.agendar": "Agendar consultas",
    "ambulatorio.atender": "Atender consulta ambulatorial",
    # Internação
    "internacao.ver": "Visualizar internações e leitos",
    "internacao.admitir": "Admitir/transferir/gerir leitos",
    "internacao.prescrever": "Prescrição médica",
    "internacao.prescrever_enfermagem": "Prescrição/evolução de enfermagem e controles",
    "internacao.evoluir": "Evolução médica",
    "internacao.alta": "Dar alta hospitalar",
    # Exames
    "exames.ver": "Visualizar exames",
    "exames.solicitar": "Solicitar exames",
    "exames.coletar": "Coletar/executar exames",
    "exames.resultado": "Lançar resultado/laudo de exame",
    # Farmácia
    "farmacia.ver": "Visualizar farmácia/estoque",
    "farmacia.gerir": "Cadastrar medicamento e entrada de estoque",
    "farmacia.dispensar": "Dispensar medicamentos",
    # Nutrição
    "nutricao.ver": "Visualizar mapa de dietas",
    "nutricao.prescrever": "Prescrição dietética",
    # CCIH
    "ccih.ver": "Visualizar painel da CCIH",
    "ccih.gerir": "Notificar infecção / gerir isolamento",
    # Cirurgias
    "cirurgias.ver": "Visualizar mapa/escala cirúrgica",
    "cirurgias.gerir": "Solicitar/agendar/descrever cirurgia",
    # Maternidade
    "maternidade.ver": "Visualizar maternidade",
    "maternidade.gerir": "Pré-natal, parto e recém-nascido",
    # Certificado digital
    "certificado.usar": "Gerir certificado e assinar documentos",
    # Estoque / almoxarifado
    "estoque.ver": "Visualizar estoque",
    "estoque.gerir": "Movimentar estoque, requisições e inventário",
    # Compras
    "compras.ver": "Visualizar compras",
    "compras.gerir": "Solicitações, cotações, pedidos e recebimento",
    # Financeiro
    "financeiro.ver": "Visualizar financeiro",
    "financeiro.gerir": "Contas, baixas e categorias",
    # Faturamento SUS
    "faturamento.ver": "Visualizar faturamento",
    "faturamento.gerir": "Guias AIH/APAC/BPA e procedimentos",
    # Convênios
    "convenios.ver": "Visualizar convênios",
    "convenios.gerir": "Guias TISS e catálogo CBHPM",
    # Patrimônio
    "patrimonio.ver": "Visualizar patrimônio",
    "patrimonio.gerir": "Cadastrar/movimentar bens",
    # RH
    "rh.ver": "Visualizar RH",
    "rh.gerir": "Funcionários, setores e escalas",
    # Manutenção
    "manutencao.ver": "Visualizar ordens de serviço",
    "manutencao.gerir": "Abrir/executar ordens de serviço",
    # Relatórios / gestão
    "relatorios.ver": "Visualizar dashboard gerencial",
    # Auditoria / LGPD
    "auditoria.ver": "Consultar trilha de auditoria de acesso (LGPD)",
    # Resíduos (PGRSS)
    "residuos.ver": "Visualizar resíduos",
    "residuos.gerir": "Registrar resíduos e coletas",
    # RNDS
    "rnds.ver": "Visualizar fila RNDS",
    "rnds.gerir": "Gerar/enviar recursos FHIR",
    # Administração de usuários
    "usuarios.gerir": "Gerir usuários, perfis e permissões",
}


def _modulos() -> set[str]:
    return {c.split(".", 1)[0] for c in CATALOGO}


def _expandir(codigos: set[str]) -> set[str]:
    """Expande curingas 'modulo.*' para todas as permissões do módulo."""
    resultado: set[str] = set()
    for c in codigos:
        if c.endswith(".*"):
            modulo = c[:-2]
            resultado |= {k for k in CATALOGO if k.startswith(f"{modulo}.")}
        else:
            resultado.add(c)
    return resultado


# ---------------------------------------------------------------------------
# Mapeamento Perfil → permissões (ADMINISTRADOR = acesso total, não listado)
# ---------------------------------------------------------------------------

PERFIL_PERMISSOES: dict[TipoPerfil, set[str]] = {
    TipoPerfil.MEDICO: {
        "pacientes.ver", "pacientes.criar",
        "emergencia.ver", "emergencia.atender",
        "ambulatorio.ver", "ambulatorio.atender",
        "internacao.ver", "internacao.admitir", "internacao.prescrever",
        "internacao.evoluir", "internacao.alta",
        "exames.ver", "exames.solicitar", "exames.resultado",
        "ccih.ver", "ccih.gerir",
        "cirurgias.*", "maternidade.*",
        "certificado.usar", "relatorios.ver",
    },
    TipoPerfil.ENFERMEIRO: {
        "pacientes.ver", "pacientes.criar",
        "emergencia.ver", "emergencia.triar",
        "ambulatorio.ver",
        "internacao.ver", "internacao.admitir", "internacao.prescrever_enfermagem",
        "exames.ver", "exames.coletar",
        "ccih.ver", "ccih.gerir",
        "maternidade.ver", "certificado.usar",
    },
    TipoPerfil.TECNICO_ENFERMAGEM: {
        "pacientes.ver", "emergencia.ver", "emergencia.triar",
        "internacao.ver", "internacao.prescrever_enfermagem",
        "exames.ver", "exames.coletar",
    },
    TipoPerfil.FARMACEUTICO: {
        "pacientes.ver", "internacao.ver",
        "farmacia.*", "estoque.ver", "certificado.usar",
    },
    TipoPerfil.RECEPCIONISTA: {
        "pacientes.ver", "pacientes.criar",
        "emergencia.ver", "emergencia.triar",
        "ambulatorio.ver", "ambulatorio.agendar",
    },
    TipoPerfil.FATURAMENTO: {
        "pacientes.ver", "faturamento.*", "convenios.*", "relatorios.ver",
    },
    TipoPerfil.FINANCEIRO: {
        "financeiro.*", "compras.ver", "relatorios.ver",
    },
    TipoPerfil.ALMOXARIFE: {
        "estoque.*", "compras.*", "patrimonio.ver",
    },
    TipoPerfil.NUTRICIONISTA: {
        "pacientes.ver", "internacao.ver", "nutricao.*", "certificado.usar",
    },
    TipoPerfil.FISIOTERAPEUTA: {
        "pacientes.ver", "internacao.ver", "internacao.evoluir", "certificado.usar",
    },
    TipoPerfil.ASSISTENTE_SOCIAL: {
        "pacientes.ver", "pacientes.criar", "internacao.ver",
    },
    TipoPerfil.LABORATORISTA: {
        "pacientes.ver", "exames.ver", "exames.coletar", "exames.resultado",
        "certificado.usar",
    },
    TipoPerfil.RADIOLOGISTA: {
        "pacientes.ver", "exames.ver", "exames.resultado", "certificado.usar",
    },
    TipoPerfil.GESTOR: {
        "relatorios.ver", "auditoria.ver",
        "pacientes.ver", "internacao.ver", "faturamento.ver", "convenios.ver",
        "financeiro.ver", "estoque.ver", "compras.ver", "patrimonio.ver",
        "rh.ver", "manutencao.ver", "residuos.ver", "rnds.ver", "ccih.ver",
    },
}


# ---------------------------------------------------------------------------
# Seed idempotente
# ---------------------------------------------------------------------------

def seed_permissoes() -> dict:
    """
    Cria/atualiza as Permissao do catálogo e associa aos Perfis conforme o
    mapeamento. Idempotente: não duplica e reconcilia associações a cada execução.

    Retorna um resumo com contagens (para log).
    """
    # 1) Garante que toda permissão do catálogo existe
    existentes = {p.codigo: p for p in Permissao.query.all()}
    criadas = 0
    for codigo, descricao in CATALOGO.items():
        modulo = codigo.split(".", 1)[0]
        p = existentes.get(codigo)
        if p is None:
            p = Permissao(codigo=codigo, descricao=descricao, modulo=modulo)
            db.session.add(p)
            existentes[codigo] = p
            criadas += 1
        else:
            # mantém descrição/módulo em dia
            p.descricao = descricao
            p.modulo = modulo
    db.session.flush()

    # 2) Reconcilia associações por perfil (apenas perfis de tipo conhecido)
    perfis_atualizados = 0
    for perfil in Perfil.query.filter(Perfil.tipo.isnot(None)).all():
        if perfil.tipo == TipoPerfil.ADMINISTRADOR:
            # Administrador tem acesso total via decorator; não precisa de vínculos.
            continue
        desejadas = _expandir(PERFIL_PERMISSOES.get(perfil.tipo, set()))
        objetos = [existentes[c] for c in desejadas if c in existentes]
        atual = {p.codigo for p in perfil.permissoes}
        if atual != desejadas:
            perfil.permissoes = objetos
            perfis_atualizados += 1

    db.session.commit()

    return {
        "permissoes_totais": len(CATALOGO),
        "permissoes_criadas": criadas,
        "perfis_atualizados": perfis_atualizados,
    }
