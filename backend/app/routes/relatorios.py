"""routes/relatorios.py — Dashboard gerencial e indicadores."""

from flask import Blueprint, render_template, request
from flask_login import login_required

from ..services.indicadores_service import dashboard_gerencial
from ..utils.authz import requer_permissao

bp = Blueprint("relatorios", __name__)


@bp.route("/")
@login_required
@requer_permissao("relatorios.ver")
def dashboard():
    dias = request.args.get("dias", 30, type=int)
    dados = dashboard_gerencial(dias)
    return render_template("relatorios/dashboard.html", dados=dados, dias=dias)
