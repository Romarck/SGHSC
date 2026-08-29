"""
routes/main.py — Blueprint principal (dashboard e páginas gerais).
"""

from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("main", __name__)


@bp.route("/")
@bp.route("/dashboard")
@login_required
def dashboard():
    """Painel principal do sistema."""
    return render_template("main/dashboard.html")


@bp.route("/guia")
@login_required
def guia():
    """Serve o Guia de Uso (HTML autocontido com botão de exportar PDF)."""
    import os

    from flask import abort, current_app, send_file
    caminho = os.path.join(current_app.static_folder, "guia", "guia_de_uso.html")
    if not os.path.exists(caminho):
        abort(404, description="Guia de uso ainda não gerado. "
                               "Rode: python gerar_guia_html.py")
    return send_file(caminho)


@bp.route("/dashboard/contadores")
@login_required
def contadores():
    """Partial HTMX: contadores em tempo real para o dashboard."""
    from ..extensions import db
    from ..models.ambulatorio import ConsultaAmbulatorial, StatusConsulta
    from ..models.emergencia import AtendimentoEmergencia, StatusAtendimentoEmergencia
    from ..models.paciente import Paciente, StatusPaciente

    hoje = date.today()

    total_pacientes = Paciente.query.filter_by(status=StatusPaciente.ATIVO).count()

    fila_pa = AtendimentoEmergencia.query.filter(
        AtendimentoEmergencia.status != StatusAtendimentoEmergencia.FINALIZADO
    ).count()

    consultas_hoje = ConsultaAmbulatorial.query.filter(
        ConsultaAmbulatorial.data == hoje,
        ConsultaAmbulatorial.status.notin_([StatusConsulta.CANCELADA])
    ).count()

    atend_hoje = AtendimentoEmergencia.query.filter(
        db.func.date(AtendimentoEmergencia.chegada_em) == hoje
    ).count()

    return render_template(
        "main/_contadores.html",
        total_pacientes=total_pacientes,
        fila_pa=fila_pa,
        consultas_hoje=consultas_hoje,
        atend_hoje=atend_hoje,
    )
