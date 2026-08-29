"""
tests/test_fluxo_clinico.py — Fluxo clínico ponta a ponta (Story S-08).

Exercita o ciclo: admissão → prescrição → visualização do prontuário → alta,
usando os modelos reais + a rota de prontuário (integração com RBAC e auditoria)
+ a geração do laudo de alta em PDF (reportlab).

Foco: travar regressão do fluxo clínico crítico e dos controles de segurança que
o cercam (permissão internacao.ver, trilha de auditoria).
"""

from datetime import date, datetime, timezone

from app.extensions import db
from app.models.auditoria import AcaoAuditoria, LogAcesso
from app.models.internacao import (
    CondicaoAlta,
    FrequenciaAdministracao,
    Internacao,
    ItemPrescricao,
    Leito,
    PrescricaoMedica,
    StatusInternacao,
    StatusLeito,
    TipoAlta,
    TipoInternacao,
    TipoItemPrescricao,
    TipoLeito,
    ViaAdministracao,
)
from app.models.paciente import Paciente, Sexo
from app.models.prontuario import Prontuario
from app.models.usuario import Usuario


def _setup_admissao():
    """Cria paciente + prontuário + leito + internação ativa. Retorna a internação."""
    admin = Usuario.query.filter_by(username="admin").first()
    medico = Usuario.query.filter_by(username="medico").first()

    paciente = Paciente(
        nome="MARIA DA SILVA", data_nascimento=date(1980, 5, 10),
        sexo=Sexo.FEMININO, criado_por_id=admin.id,
    )
    db.session.add(paciente)
    db.session.flush()

    # Prontuário do paciente (o laudo referencia paciente.prontuario)
    db.session.add(Prontuario(numero="PRT0001", paciente_id=paciente.id,
                              aberto_por_id=admin.id))

    leito = Leito(numero="ENF-01", tipo=TipoLeito.ENFERMARIA, status=StatusLeito.LIVRE)
    db.session.add(leito)
    db.session.flush()

    internacao = Internacao(
        numero="INT0001", paciente_id=paciente.id, leito_id=leito.id,
        medico_responsavel_id=medico.id, tipo=TipoInternacao.URGENCIA,
        motivo="Dor abdominal aguda", hipotese_diagnostica="Apendicite",
        cid10_principal="K35", admitido_por_id=admin.id,
        status=StatusInternacao.ATIVA,
    )
    leito.status = StatusLeito.OCUPADO
    db.session.add(internacao)
    db.session.commit()
    return internacao


def test_admissao_prescricao_prontuario_alta(client, login):
    """Fluxo completo: admissão → prescrição → prontuário (rota) → alta + PDF."""
    internacao = _setup_admissao()
    medico = Usuario.query.filter_by(username="medico").first()

    # --- Prescrição médica com um item ---
    presc = PrescricaoMedica(
        numero="RX0001", internacao_id=internacao.id, medico_id=medico.id,
        data_prescricao=date.today(), ativa=True,
    )
    db.session.add(presc)
    db.session.flush()
    db.session.add(ItemPrescricao(
        prescricao_id=presc.id, ordem=1, tipo=TipoItemPrescricao.MEDICAMENTO,
        descricao="Dipirona 1g", dose="1g", via=ViaAdministracao.ENDOVENOSA,
        frequencia=FrequenciaAdministracao.CADA_6H, duracao="3 dias",
    ))
    db.session.commit()
    assert internacao.prescricoes_medicas.count() == 1
    assert internacao.prescricao_ativa.itens[0].descricao == "Dipirona 1g"

    # --- Visualização do prontuário via ROTA (RBAC medico + auditoria) ---
    login("medico")
    resp = client.get(f"/internacao/{internacao.id}")
    assert resp.status_code == 200
    # A visualização gerou trilha de auditoria (S-07) para este paciente
    log = LogAcesso.query.filter_by(paciente_id=internacao.paciente_id).first()
    assert log is not None and log.acao == AcaoAuditoria.VISUALIZAR

    # --- Alta ---
    internacao.status = StatusInternacao.ALTA
    internacao.alta_em = datetime.now(timezone.utc)
    internacao.tipo_alta = TipoAlta.ALTA_MEDICA
    internacao.condicao_alta = CondicaoAlta.CURADO
    internacao.diagnostico_principal_alta = "Pós-apendicectomia, sem complicações"
    internacao.resumo_alta = "Paciente evoluiu bem. Alta em bom estado geral."
    internacao.dado_alta_por_id = medico.id
    internacao.leito.status = StatusLeito.LIVRE
    db.session.commit()

    assert internacao.status == StatusInternacao.ALTA
    assert internacao.leito.status == StatusLeito.LIVRE
    assert internacao.dias_internado >= 0


def test_laudo_alta_pdf_gerado(client, app):
    """A geração do laudo de alta (reportlab) produz um PDF válido."""
    import os

    from app.services import pdf_service

    internacao = _setup_admissao()
    internacao.status = StatusInternacao.ALTA
    internacao.alta_em = datetime.now(timezone.utc)
    internacao.tipo_alta = TipoAlta.ALTA_MEDICA
    internacao.condicao_alta = CondicaoAlta.MELHORADO
    internacao.resumo_alta = "Alta com melhora."
    internacao.dado_alta_por_id = internacao.medico_responsavel_id
    db.session.commit()

    caminho = pdf_service.gerar_laudo_alta(internacao)
    assert os.path.exists(caminho) and os.path.getsize(caminho) > 0
    with open(caminho, "rb") as f:
        assert f.read(4) == b"%PDF"  # assinatura de arquivo PDF
    os.remove(caminho)


def test_prontuario_sem_permissao_recebe_403(client, login):
    """Recepcionista não tem internacao.ver → 403 no prontuário clínico."""
    internacao = _setup_admissao()
    login("recep")
    resp = client.get(f"/internacao/{internacao.id}")
    assert resp.status_code == 403
