"""
routes/rnds.py — Integração RNDS (FHIR R4).

Fila de envio, geração do payload FHIR e status.

NOTA: o envio efetivo ao barramento nacional exige certificado ICP-Brasil
credenciado + OAuth no ambiente do DATASUS. A função de envio abaixo é um stub:
marca como enviado localmente e registra que a transmissão real está pendente
de credenciais oficiais.
"""

import json
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models.paciente import Paciente
from ..models.rnds import RegistroRNDS, StatusEnvioRNDS, TipoRecursoFHIR
from ..utils.authz import requer_permissao

bp = Blueprint("rnds", __name__)


def _fhir_patient(paciente) -> dict:
    """Mapeia um Paciente para um recurso FHIR R4 Patient (simplificado)."""
    return {
        "resourceType": "Patient",
        "identifier": [
            {"system": "https://saude.gov.br/fhir/r4/NamingSystem/cns", "value": paciente.cns or ""},
            {"system": "https://saude.gov.br/fhir/r4/NamingSystem/cpf", "value": paciente.cpf or ""},
        ],
        "name": [{"text": paciente.nome}],
        "gender": {
            "MASCULINO": "male", "FEMININO": "female",
        }.get(paciente.sexo.name if paciente.sexo else "", "unknown"),
        "birthDate": paciente.data_nascimento.isoformat() if paciente.data_nascimento else None,
    }


@bp.route("/")
@bp.route("/fila")
@login_required
@requer_permissao("rnds.ver")
def fila():
    status = request.args.get("status")
    query = RegistroRNDS.query
    if status:
        try:
            query = query.filter_by(status=StatusEnvioRNDS[status])
        except KeyError:
            pass
    registros = query.order_by(RegistroRNDS.criado_em.desc()).limit(100).all()
    return render_template("rnds/fila.html", registros=registros,
                           status_atual=status, StatusEnvioRNDS=StatusEnvioRNDS)


@bp.route("/enfileirar-paciente/<int:paciente_id>", methods=["POST"])
@login_required
@requer_permissao("rnds.gerir")
def enfileirar_paciente(paciente_id):
    """Gera o recurso FHIR Patient e o coloca na fila de envio."""
    paciente = db.get_or_404(Paciente, paciente_id)
    payload = _fhir_patient(paciente)
    reg = RegistroRNDS(
        tipo_recurso=TipoRecursoFHIR.PACIENTE,
        paciente_id=paciente.id,
        origem_tipo="paciente",
        origem_id=paciente.id,
        payload_fhir=json.dumps(payload, ensure_ascii=False, indent=2),
        status=StatusEnvioRNDS.PENDENTE,
    )
    db.session.add(reg)
    db.session.commit()
    flash(f"Paciente {paciente.nome_exibicao} enfileirado para envio à RNDS.", "success")
    return redirect(url_for("rnds.fila"))


@bp.route("/registro/<int:id>")
@login_required
@requer_permissao("rnds.ver")
def detalhe(id):
    reg = db.get_or_404(RegistroRNDS, id)
    return render_template("rnds/detalhe.html", reg=reg)


@bp.route("/registro/<int:id>/enviar", methods=["POST"])
@login_required
@requer_permissao("rnds.gerir")
def enviar(id):
    """
    Envio à RNDS (STUB). O envio real exige certificado ICP-Brasil credenciado
    e conexão autenticada com o barramento do DATASUS. Aqui apenas simulamos
    o resultado localmente e sinalizamos que a transmissão real está pendente.
    """
    reg = db.get_or_404(RegistroRNDS, id)
    reg.tentativas += 1
    # Sem credenciais oficiais configuradas -> registra pendência
    reg.status = StatusEnvioRNDS.ENVIADO
    reg.enviado_em = datetime.now(timezone.utc)
    reg.protocolo_rnds = f"LOCAL-{reg.id}"
    reg.mensagem_retorno = ("Envio simulado localmente. A transmissão real ao "
                            "barramento RNDS requer certificado ICP-Brasil credenciado "
                            "e configuração do endpoint oficial do DATASUS.")
    db.session.commit()
    flash("Registro marcado como enviado (simulado). Transmissão real pendente de "
          "credenciais RNDS.", "info")
    return redirect(url_for("rnds.detalhe", id=reg.id))
