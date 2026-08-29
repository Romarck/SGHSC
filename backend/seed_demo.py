"""
seed_demo.py — Popula o banco com dados mockados realistas para demonstração,
treinamento e geração das capturas de tela do guia de uso.

Uso:
    docker compose exec app python seed_demo.py

Idempotência: verifica marcadores antes de criar. Rodar mais de uma vez não
duplica os dados principais (usa códigos/números fixos com prefixo DEMO).

NÃO usar em produção — cria pacientes e registros fictícios.
"""

from datetime import date, datetime, timezone, timedelta, time

from app import create_app
from app.extensions import db
from app.models.usuario import Usuario, Perfil, TipoPerfil, StatusUsuario
from app.models.paciente import (
    Paciente, Sexo, RacaCor, EstadoCivil, TipoSanguineo, StatusPaciente, TipoLogradouro
)

import os

# Usa o ambiente atual (development/production/homolog). Antes era fixo em
# "development", o que falhava em produção/homologação.
app = create_app(os.environ.get("FLASK_ENV", "development"))


def obter_admin():
    """Usuário admin (autor padrão dos registros de demo)."""
    return Usuario.query.filter_by(username="admin").first()


def obter_perfil_medico():
    perfil = Perfil.query.filter_by(tipo=TipoPerfil.MEDICO).first()
    if not perfil:
        perfil = Perfil(nome="Médico", tipo=TipoPerfil.MEDICO, descricao="Perfil médico (demo)")
        db.session.add(perfil)
        db.session.flush()
    return perfil


def obter_medico(perfil):
    medico = Usuario.query.filter_by(username="dr.demo").first()
    if not medico:
        medico = Usuario(
            nome="Dr. Carlos Andrade", email="carlos.demo@sghsc.local",
            username="dr.demo", perfil_id=perfil.id, status=StatusUsuario.ATIVO,
            conselho_tipo="CRM", conselho_numero="54321", conselho_uf="MG",
            especialidade="Clínica Médica", deve_trocar_senha=False,
        )
        medico.senha = "Demo@123"
        db.session.add(medico)
        db.session.flush()
    return medico


PACIENTES = [
    ("Maria da Silva Souza", date(1985, 3, 12), Sexo.FEMININO, "111.111.111-11", "700111111111111", "Pedralva"),
    ("João Pereira Lima", date(1972, 7, 25), Sexo.MASCULINO, "222.222.222-22", "700222222222222", "Pouso Alegre"),
    ("Ana Beatriz Costa", date(1998, 11, 3), Sexo.FEMININO, "333.333.333-33", "700333333333333", "Pedralva"),
    ("Antônio Carlos Ferreira", date(1955, 1, 30), Sexo.MASCULINO, "444.444.444-44", "700444444444444", "Cambuí"),
    ("Rita de Cássia Oliveira", date(1990, 6, 18), Sexo.FEMININO, "555.555.555-55", "700555555555555", "Pedralva"),
    ("José Roberto Mendes", date(1968, 9, 9), Sexo.MASCULINO, "666.666.666-66", "700666666666666", "Itajubá"),
    ("Fernanda Alves Rocha", date(2001, 4, 22), Sexo.FEMININO, "777.777.777-77", "700777777777777", "Pedralva"),
    ("Pedro Henrique Santos", date(1979, 12, 5), Sexo.MASCULINO, "888.888.888-88", "700888888888888", "Maria da Fé"),
]


def seed_pacientes(autor):
    criados = []
    for nome, nasc, sexo, cpf, cns, cidade in PACIENTES:
        pac = Paciente.query.filter_by(cpf=cpf).first()
        if not pac:
            pac = Paciente(
                nome=nome, data_nascimento=nasc, sexo=sexo, cpf=cpf, cns=cns,
                raca_cor=RacaCor.PARDA, estado_civil=EstadoCivil.CASADO,
                naturalidade=cidade, tipo_sanguineo=TipoSanguineo.O_POS,
                status=StatusPaciente.ATIVO, cidade="Pedralva", uf="MG",
                tipo_logradouro=TipoLogradouro.RUA, logradouro="Rua das Flores",
                numero="100", bairro="Centro", cep="37538-000",
                telefone="(35) 99999-0000",
                alergias="Dipirona" if cpf.startswith("444") else None,
                criado_por_id=autor.id,  # NOT NULL desde S-07
            )
            db.session.add(pac)
            db.session.flush()
        criados.append(pac)
    return criados


def seed_emergencia(pacientes, medico):
    from app.models.emergencia import (
        AtendimentoEmergencia, TriagemManchester,
        ClassificacaoManchester, StatusAtendimentoEmergencia,
    )
    if AtendimentoEmergencia.query.filter(AtendimentoEmergencia.numero.like("PADEMO%")).first():
        return
    agora = datetime.now(timezone.utc)
    dados = [
        (pacientes[0], ClassificacaoManchester.AMARELO, "Dor abdominal intensa", StatusAtendimentoEmergencia.TRIADO),
        (pacientes[1], ClassificacaoManchester.VERMELHO, "Dor torácica, sudorese", StatusAtendimentoEmergencia.EM_ATENDIMENTO),
        (pacientes[4], ClassificacaoManchester.VERDE, "Cefaleia há 2 dias", StatusAtendimentoEmergencia.AGUARDANDO_TRIAGEM),
    ]
    for i, (pac, cor, queixa, status) in enumerate(dados, 1):
        at = AtendimentoEmergencia(
            numero=f"PADEMO{i:04d}", paciente_id=pac.id,
            chegada_em=agora - timedelta(hours=i), status=status,
            registrado_por_id=medico.id,
        )
        db.session.add(at)
        db.session.flush()
        if status != StatusAtendimentoEmergencia.AGUARDANDO_TRIAGEM:
            db.session.add(TriagemManchester(
                atendimento_id=at.id, classificacao=cor, queixa_principal=queixa,
                pressao_sistolica=130, pressao_diastolica=85, frequencia_cardiaca=88,
                temperatura=36.8, saturacao_o2=97, realizada_por_id=medico.id,
            ))


def seed_ambulatorio(pacientes, medico):
    from app.models.ambulatorio import (
        AgendaAmbulatorio, ConsultaAmbulatorial, StatusConsulta, TipoConsulta, DiaSemana,
    )
    if ConsultaAmbulatorial.query.filter(ConsultaAmbulatorial.numero.like("CONSDEMO%")).first():
        return
    hoje = date.today()
    for i, pac in enumerate(pacientes[:4], 1):
        db.session.add(ConsultaAmbulatorial(
            numero=f"CONSDEMO{i:04d}", paciente_id=pac.id, medico_id=medico.id,
            especialidade="Clínica Médica", data=hoje, horario=time(8 + i, 0),
            tipo=TipoConsulta.PRIMEIRA_VEZ, status=StatusConsulta.AGENDADA,
        ))


def seed_internacao(pacientes, medico):
    from app.models.internacao import (
        Leito, Internacao, PrescricaoMedica, ItemPrescricao, ControlesPaciente,
        EvolucaoMedica, TipoLeito, StatusLeito, TipoInternacao, StatusInternacao,
        ViaAdministracao, FrequenciaAdministracao, TipoItemPrescricao, StatusItemPrescricao,
    )
    # Leitos
    if not Leito.query.filter(Leito.numero.like("DEMO%")).first():
        leitos_def = [
            ("DEMO-101", TipoLeito.ENFERMARIA, "Ala A", StatusLeito.LIVRE, False),
            ("DEMO-102", TipoLeito.ENFERMARIA, "Ala A", StatusLeito.OCUPADO, False),
            ("DEMO-103", TipoLeito.ENFERMARIA, "Ala A", StatusLeito.LIMPEZA, False),
            ("DEMO-201", TipoLeito.UTI_ADULTO, "UTI", StatusLeito.OCUPADO, False),
            ("DEMO-202", TipoLeito.UTI_ADULTO, "UTI", StatusLeito.LIVRE, False),
            ("DEMO-301", TipoLeito.ISOLAMENTO, "Ala B", StatusLeito.RESERVADO, True),
            ("DEMO-401", TipoLeito.MATERNIDADE, "Maternidade", StatusLeito.LIVRE, False),
        ]
        for num, tipo, ala, status, iso in leitos_def:
            db.session.add(Leito(numero=num, tipo=tipo, ala=ala, andar="1º",
                                 status=status, isolamento=iso))
        db.session.flush()

    if Internacao.query.filter(Internacao.numero.like("INTDEMO%")).first():
        return

    leito_102 = Leito.query.filter_by(numero="DEMO-102").first()
    leito_201 = Leito.query.filter_by(numero="DEMO-201").first()
    agora = datetime.now(timezone.utc)

    for i, (pac, leito, dias) in enumerate([
        (pacientes[3], leito_102, 3), (pacientes[5], leito_201, 8)
    ], 1):
        intern = Internacao(
            numero=f"INTDEMO{i:04d}", paciente_id=pac.id, leito_id=leito.id,
            medico_responsavel_id=medico.id, tipo=TipoInternacao.URGENCIA,
            motivo="Pneumonia comunitária" if i == 1 else "Insuficiência cardíaca descompensada",
            cid10_principal="J18.0" if i == 1 else "I50.0", convenio="SUS",
            status=StatusInternacao.ATIVA, admissao_em=agora - timedelta(days=dias),
            admitido_por_id=medico.id,
        )
        db.session.add(intern)
        db.session.flush()

        rx = PrescricaoMedica(
            numero=f"RXDEMO{i:04d}", internacao_id=intern.id, medico_id=medico.id,
            data_prescricao=date.today(), ativa=True,
            observacoes="Reavaliar em 24h.",
        )
        db.session.add(rx)
        db.session.flush()
        db.session.add(ItemPrescricao(
            prescricao_id=rx.id, ordem=1, tipo=TipoItemPrescricao.MEDICAMENTO,
            descricao="Ceftriaxona 1g", dose="1g", via=ViaAdministracao.ENDOVENOSA,
            frequencia=FrequenciaAdministracao.CADA_12H, horarios="08h 20h",
            status=StatusItemPrescricao.ATIVO,
        ))
        db.session.add(ItemPrescricao(
            prescricao_id=rx.id, ordem=2, tipo=TipoItemPrescricao.DIETA,
            descricao="Dieta branda", status=StatusItemPrescricao.ATIVO,
        ))
        db.session.add(EvolucaoMedica(
            internacao_id=intern.id, medico_id=medico.id,
            subjetivo="Paciente refere melhora da dispneia.",
            objetivo="BEG, corado, hidratado. AP: MV+ com estertores em base D.",
            avaliacao="Pneumonia em melhora clínica.",
            plano="Manter antibioticoterapia. Solicitar RX de controle.",
        ))
        db.session.add(ControlesPaciente(
            internacao_id=intern.id, registrado_por_id=medico.id,
            pressao_sistolica=120, pressao_diastolica=80, frequencia_cardiaca=76,
            frequencia_respiratoria=18, temperatura=36.5, saturacao_o2=96,
            soro_ev=500, ingesta_oral=800, diurese=1200,
        ))


def seed_exames(pacientes, medico):
    from app.models.exame import (
        ExameCatalogo, SolicitacaoExame, ItemExame, ResultadoExame,
        CategoriaExame, PrioridadeExame, StatusSolicitacaoExame,
    )
    if not ExameCatalogo.query.filter_by(codigo="HEMOG").first():
        db.session.add_all([
            ExameCatalogo(codigo="HEMOG", nome="Hemograma completo", categoria=CategoriaExame.LABORATORIAL, material="Sangue"),
            ExameCatalogo(codigo="GLIC", nome="Glicemia de jejum", categoria=CategoriaExame.LABORATORIAL, material="Sangue"),
            ExameCatalogo(codigo="RXTX", nome="Radiografia de tórax", categoria=CategoriaExame.IMAGEM),
        ])
        db.session.flush()

    if SolicitacaoExame.query.filter(SolicitacaoExame.numero.like("EXDEMO%")).first():
        return
    sol = SolicitacaoExame(
        numero="EXDEMO0001", paciente_id=pacientes[3].id, solicitante_id=medico.id,
        prioridade=PrioridadeExame.URGENTE, indicacao_clinica="Investigação de pneumonia",
        status=StatusSolicitacaoExame.RESULTADO_DISPONIVEL,
    )
    db.session.add(sol)
    db.session.flush()
    it1 = ItemExame(solicitacao_id=sol.id, nome_exame="Hemograma completo")
    it2 = ItemExame(solicitacao_id=sol.id, nome_exame="Radiografia de tórax")
    db.session.add_all([it1, it2])
    db.session.flush()
    db.session.add(ResultadoExame(
        item_id=it1.id, valor="Leucócitos 14.500", unidade="/mm³",
        valor_referencia="4.000-11.000", alterado=True, responsavel_id=medico.id,
    ))
    db.session.add(ResultadoExame(
        item_id=it2.id, laudo="Opacidade em base pulmonar direita compatível com processo infeccioso.",
        responsavel_id=medico.id,
    ))


def seed_farmacia(medico):
    from app.models.farmacia import (
        MedicamentoFarmacia, LoteEstoque, FormaFarmaceutica,
    )
    if MedicamentoFarmacia.query.filter(MedicamentoFarmacia.codigo.like("MEDDEMO%")).first():
        return
    meds = [
        ("MEDDEMO01", "Ceftriaxona", "Ceftriaxona sódica", "1g", FormaFarmaceutica.FRASCO_AMPOLA, 20, 50),
        ("MEDDEMO02", "Dipirona", "Dipirona sódica", "500mg/mL", FormaFarmaceutica.AMPOLA, 30, 200),
        ("MEDDEMO03", "Soro Fisiológico 0,9%", "Cloreto de sódio", "500mL", FormaFarmaceutica.FRASCO, 40, 15),
        ("MEDDEMO04", "Omeprazol", "Omeprazol", "40mg", FormaFarmaceutica.FRASCO_AMPOLA, 25, 8),
    ]
    for cod, nome, pa, conc, forma, minimo, qtd in meds:
        m = MedicamentoFarmacia(codigo=cod, nome=nome, principio_ativo=pa,
                                concentracao=conc, forma=forma, estoque_minimo=minimo)
        db.session.add(m)
        db.session.flush()
        db.session.add(LoteEstoque(
            medicamento_id=m.id, numero_lote=f"L{cod[-2:]}2026",
            validade=date.today() + timedelta(days=365), quantidade=qtd,
            fabricante="Laboratório Demo",
        ))


def seed_nutricao(medico):
    from app.models.internacao import Internacao, StatusInternacao
    from app.models.nutricao import (
        PrescricaoDietetica, TipoDieta, ViaAlimentacao, StatusPrescricaoDieta,
    )
    intern = Internacao.query.filter(Internacao.numero.like("INTDEMO%")).first()
    if not intern or PrescricaoDietetica.query.filter_by(internacao_id=intern.id).first():
        return
    db.session.add(PrescricaoDietetica(
        internacao_id=intern.id, nutricionista_id=medico.id, data_prescricao=date.today(),
        tipo_dieta=TipoDieta.BRANDA, via=ViaAlimentacao.ORAL, valor_calorico=1800,
        fracionamento="6 refeições", restricoes="Hipossódica",
        status=StatusPrescricaoDieta.ATIVA,
    ))


def seed_ccih(pacientes, medico):
    from app.models.internacao import Internacao
    from app.models.ccih import (
        NotificacaoInfeccao, IsolamentoPaciente,
        TipoInfeccao, TipoPrecaucao, StatusNotificacao, StatusIsolamento,
    )
    if NotificacaoInfeccao.query.filter(NotificacaoInfeccao.numero.like("CCIHDEMO%")).first():
        return
    intern = Internacao.query.filter(Internacao.numero.like("INTDEMO%")).first()
    db.session.add(NotificacaoInfeccao(
        numero="CCIHDEMO0001", paciente_id=pacientes[5].id,
        internacao_id=intern.id if intern else None, notificante_id=medico.id,
        tipo=TipoInfeccao.IRAS, topografia="Trato respiratório",
        microrganismo="Klebsiella pneumoniae", cid10="J15.0",
        status=StatusNotificacao.EM_INVESTIGACAO,
        descricao="Paciente com sinais de infecção respiratória após 5 dias de internação.",
    ))
    if intern:
        db.session.add(IsolamentoPaciente(
            internacao_id=intern.id, tipo_precaucao=TipoPrecaucao.CONTATO,
            motivo="Klebsiella resistente", microrganismo="Klebsiella pneumoniae",
            prescrito_por_id=medico.id, status=StatusIsolamento.ATIVO,
        ))


def seed_cirurgias(pacientes, medico):
    from app.models.cirurgia import (
        SalaCirurgica, Cirurgia, TipoCirurgia, PorteCirurgico, TipoAnestesia, StatusCirurgia,
    )
    if not SalaCirurgica.query.filter(SalaCirurgica.nome.like("Sala Demo%")).first():
        db.session.add_all([
            SalaCirurgica(nome="Sala Demo 1", descricao="Centro cirúrgico principal"),
            SalaCirurgica(nome="Sala Demo 2", descricao="Pequenas cirurgias"),
        ])
        db.session.flush()
    if Cirurgia.query.filter(Cirurgia.numero.like("CIRDEMO%")).first():
        return
    sala = SalaCirurgica.query.filter(SalaCirurgica.nome.like("Sala Demo%")).first()
    agora = datetime.now(timezone.utc)
    db.session.add(Cirurgia(
        numero="CIRDEMO0001", paciente_id=pacientes[0].id, cirurgiao_id=medico.id,
        solicitante_id=medico.id, procedimento="Colecistectomia videolaparoscópica",
        tipo=TipoCirurgia.ELETIVA, porte=PorteCirurgico.MEDIO,
        tipo_anestesia=TipoAnestesia.GERAL, cid10="K80.2", sala_id=sala.id,
        data_agendada=agora + timedelta(days=1), duracao_estimada_min=90,
        status=StatusCirurgia.AGENDADA,
    ))


def seed_maternidade(pacientes, medico):
    from app.models.maternidade import (
        PreNatal, ConsultaPreNatal, Parto, RecemNascido,
        TipoParto, ClassificacaoRisco, SexoRN, CondicaoNascimento,
    )
    if PreNatal.query.filter_by(gestante_id=pacientes[2].id).first():
        return
    pn = PreNatal(
        gestante_id=pacientes[2].id, dum=date.today() - timedelta(days=200),
        dpp=date.today() + timedelta(days=80), gestacoes=1, partos=0, abortos=0,
        classificacao_risco=ClassificacaoRisco.HABITUAL, tipo_sanguineo="O+",
        medico_id=medico.id,
    )
    db.session.add(pn)
    db.session.flush()
    db.session.add(ConsultaPreNatal(
        prenatal_id=pn.id, data_consulta=date.today() - timedelta(days=15),
        idade_gestacional_semanas=26, peso=68.5, pressao_arterial="110/70",
        altura_uterina=25, bcf=140, movimentacao_fetal=True,
    ))
    # Parto de exemplo (outra paciente)
    parto = Parto(
        numero="PARTDEMO0001", gestante_id=pacientes[6].id, tipo=TipoParto.NORMAL,
        data_parto=datetime.now(timezone.utc) - timedelta(days=2),
        idade_gestacional_semanas=39, medico_id=medico.id,
    )
    db.session.add(parto)
    db.session.flush()
    db.session.add(RecemNascido(
        parto_id=parto.id, sexo=SexoRN.FEMININO, condicao=CondicaoNascimento.VIVO,
        peso_gramas=3250, comprimento_cm=49, apgar_1min=9, apgar_5min=10,
        hora_nascimento=parto.data_parto,
    ))


def seed_administrativo(medico):
    from app.models.estoque import (
        LocalEstoque, ProdutoEstoque, SaldoEstoque, CategoriaProduto, UnidadeMedida,
    )
    from app.models.compras import Fornecedor
    from app.models.financeiro import CategoriaFinanceira, Conta, TipoConta, StatusConta
    from app.models.patrimonio import BemPatrimonial, SituacaoBem, EstadoConservacao
    from app.models.rh import Setor, Funcionario, TipoVinculo, StatusFuncionario
    from app.models.manutencao import OrdemServico, TipoManutencao, PrioridadeOS, StatusOS

    # Estoque
    if not LocalEstoque.query.filter_by(nome="Almoxarifado Central").first():
        local = LocalEstoque(nome="Almoxarifado Central", principal=True)
        db.session.add(local)
        db.session.flush()
        for cod, nome, cat, minimo, qtd in [
            ("PRODDEMO01", "Luva de procedimento M", CategoriaProduto.MATERIAL_MEDICO, 50, 200),
            ("PRODDEMO02", "Seringa 10mL", CategoriaProduto.MATERIAL_MEDICO, 100, 40),
            ("PRODDEMO03", "Álcool 70% 1L", CategoriaProduto.MATERIAL_LIMPEZA, 20, 60),
        ]:
            p = ProdutoEstoque(codigo=cod, nome=nome, categoria=cat,
                               unidade=UnidadeMedida.UNIDADE, estoque_minimo=minimo)
            db.session.add(p)
            db.session.flush()
            db.session.add(SaldoEstoque(produto_id=p.id, local_id=local.id, quantidade=qtd))

    # Fornecedor
    if not Fornecedor.query.filter_by(razao_social="MedSupply Distribuidora LTDA").first():
        db.session.add(Fornecedor(
            razao_social="MedSupply Distribuidora LTDA", nome_fantasia="MedSupply",
            cnpj="12.345.678/0001-90", telefone="(35) 3333-4444", email="vendas@medsupply.demo",
        ))

    # Financeiro
    if not CategoriaFinanceira.query.filter_by(nome="Medicamentos").first():
        from app.models.financeiro import TipoLancamento
        cat = CategoriaFinanceira(nome="Medicamentos", tipo=TipoLancamento.SAIDA)
        db.session.add(cat)
        db.session.flush()
        db.session.add(Conta(
            descricao="Compra de antibióticos - MedSupply", tipo=TipoConta.PAGAR,
            valor=4500.00, vencimento=date.today() + timedelta(days=15),
            categoria_id=cat.id, status=StatusConta.ABERTA, criado_por_id=medico.id,
        ))
        db.session.add(Conta(
            descricao="Repasse SUS - competência anterior", tipo=TipoConta.RECEBER,
            valor=28000.00, vencimento=date.today() + timedelta(days=30),
            status=StatusConta.ABERTA, criado_por_id=medico.id, convenio="SUS",
        ))

    # Patrimônio
    if not BemPatrimonial.query.filter(BemPatrimonial.numero_patrimonio.like("PATDEMO%")).first():
        db.session.add_all([
            BemPatrimonial(numero_patrimonio="PATDEMO001", descricao="Monitor multiparâmetros",
                           categoria="Equipamento médico", marca="Mindray", modelo="uMEC12",
                           localizacao="UTI", situacao=SituacaoBem.ATIVO, estado=EstadoConservacao.BOM,
                           valor_aquisicao=18000, data_aquisicao=date(2022, 3, 1), vida_util_anos=10),
            BemPatrimonial(numero_patrimonio="PATDEMO002", descricao="Cama hospitalar elétrica",
                           categoria="Mobiliário", localizacao="Ala A", situacao=SituacaoBem.ATIVO,
                           estado=EstadoConservacao.NOVO, valor_aquisicao=9000,
                           data_aquisicao=date(2024, 1, 15), vida_util_anos=15),
        ])

    # RH
    if not Setor.query.filter_by(nome="Enfermagem").first():
        setor = Setor(nome="Enfermagem")
        db.session.add(setor)
        db.session.flush()
        db.session.add(Funcionario(
            matricula="FUNCDEMO01", nome="Enfª. Juliana Martins", cargo="Enfermeira",
            setor_id=setor.id, vinculo=TipoVinculo.CLT, status=StatusFuncionario.ATIVO,
            conselho_tipo="COREN", conselho_numero="123456", data_admissao=date(2021, 5, 10),
        ))

    # Manutenção
    if not OrdemServico.query.filter(OrdemServico.numero.like("OSDEMO%")).first():
        db.session.add(OrdemServico(
            numero="OSDEMO0001", titulo="Ar-condicionado da UTI com vazamento",
            descricao="Equipamento pingando água sobre o piso.",
            tipo=TipoManutencao.CORRETIVA, prioridade=PrioridadeOS.ALTA,
            local="UTI", solicitante_id=medico.id, status=StatusOS.ABERTA,
        ))


def seed_gestao(pacientes, medico):
    from app.models.residuos import RegistroResiduo, GrupoResiduo, StatusColeta
    from app.models.rnds import RegistroRNDS, TipoRecursoFHIR, StatusEnvioRNDS
    import json

    if not RegistroResiduo.query.filter(RegistroResiduo.origem_setor.like("Centro Cirúrgico%")).first():
        db.session.add_all([
            RegistroResiduo(grupo=GrupoResiduo.A, origem_setor="Centro Cirúrgico",
                            peso_kg=3.5, acondicionamento="Saco branco leitoso",
                            registrado_por_id=medico.id, status=StatusColeta.ARMAZENADO),
            RegistroResiduo(grupo=GrupoResiduo.E, origem_setor="UTI",
                            peso_kg=1.2, acondicionamento="Caixa perfurocortante",
                            registrado_por_id=medico.id, status=StatusColeta.ARMAZENADO),
            RegistroResiduo(grupo=GrupoResiduo.D, origem_setor="Administração",
                            peso_kg=8.0, acondicionamento="Saco preto",
                            registrado_por_id=medico.id, status=StatusColeta.ARMAZENADO),
        ])

    if not RegistroRNDS.query.filter_by(paciente_id=pacientes[0].id).first():
        pac = pacientes[0]
        payload = {
            "resourceType": "Patient",
            "name": [{"text": pac.nome}],
            "gender": "female",
            "birthDate": pac.data_nascimento.isoformat(),
        }
        db.session.add(RegistroRNDS(
            tipo_recurso=TipoRecursoFHIR.PACIENTE, paciente_id=pac.id,
            origem_tipo="paciente", origem_id=pac.id,
            payload_fhir=json.dumps(payload, ensure_ascii=False, indent=2),
            status=StatusEnvioRNDS.PENDENTE,
        ))


def main():
    with app.app_context():
        perfil = obter_perfil_medico()
        medico = obter_medico(perfil)
        # Autor dos registros: admin se existir, senão o médico demo.
        autor = obter_admin() or medico
        pacientes = seed_pacientes(autor)
        db.session.commit()

        for nome_fn, fn in [
            ("emergencia", lambda: seed_emergencia(pacientes, medico)),
            ("ambulatorio", lambda: seed_ambulatorio(pacientes, medico)),
            ("internacao", lambda: seed_internacao(pacientes, medico)),
            ("exames", lambda: seed_exames(pacientes, medico)),
            ("farmacia", lambda: seed_farmacia(medico)),
            ("nutricao", lambda: seed_nutricao(medico)),
            ("ccih", lambda: seed_ccih(pacientes, medico)),
            ("cirurgias", lambda: seed_cirurgias(pacientes, medico)),
            ("maternidade", lambda: seed_maternidade(pacientes, medico)),
            ("administrativo", lambda: seed_administrativo(medico)),
            ("gestao", lambda: seed_gestao(pacientes, medico)),
        ]:
            try:
                fn()
                db.session.commit()
                print(f"  [ok] {nome_fn}")
            except Exception as e:
                db.session.rollback()
                print(f"  [ERRO] {nome_fn}: {type(e).__name__}: {e}")

        print(f"OK: {len(pacientes)} pacientes | médico demo: {medico.username} / Demo@123")


if __name__ == "__main__":
    main()
