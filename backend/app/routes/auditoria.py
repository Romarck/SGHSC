"""
routes/auditoria.py — Consulta da trilha de auditoria de acesso (Story S-07 / LGPD).

Permite ao gestor/DPO responder "quem acessou o prontuário do paciente X?" e
"quais acessos o usuário Y realizou?". Somente leitura; protegido por
'auditoria.ver' (Administrador tem acesso total).
"""

from flask import Blueprint, render_template, request
from flask_login import login_required

from ..extensions import db
from ..models.paciente import Paciente
from ..models.usuario import Usuario
from ..services.auditoria_service import trilha_por_paciente, trilha_por_usuario
from ..utils.authz import requer_permissao

bp = Blueprint("auditoria", __name__)


@bp.route("/")
@login_required
@requer_permissao("auditoria.ver")
def trilha():
    """
    Trilha de auditoria. Filtra por paciente (?paciente_id=) ou por usuário
    (?usuario_id=). Sem filtro, apenas mostra o formulário de busca.
    """
    paciente_id = request.args.get("paciente_id", type=int)
    usuario_id = request.args.get("usuario_id", type=int)

    logs = []
    paciente = None
    usuario = None

    if paciente_id:
        paciente = db.session.get(Paciente, paciente_id)
        logs = trilha_por_paciente(paciente_id)
    elif usuario_id:
        usuario = db.session.get(Usuario, usuario_id)
        logs = trilha_por_usuario(usuario_id)

    return render_template(
        "auditoria/trilha.html",
        logs=logs,
        paciente=paciente,
        usuario=usuario,
        paciente_id=paciente_id,
        usuario_id=usuario_id,
    )
