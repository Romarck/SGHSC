"""routes/manutencao.py — Manutenção predial e de equipamentos."""

from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.manutencao import (
    OrdemServico,
    PrioridadeOS,
    StatusOS,
    TipoManutencao,
)
from ..models.patrimonio import BemPatrimonial
from ..utils.authz import requer_permissao

bp = Blueprint("manutencao", __name__)


def _num():
    ultimo = db.session.query(db.func.max(OrdemServico.id)).scalar() or 0
    return f"OS{datetime.now().strftime('%Y%m%d')}{(ultimo + 1):04d}"


@bp.route("/")
@bp.route("/ordens")
@login_required
@requer_permissao("manutencao.ver")
def ordens():
    status = request.args.get("status")
    query = OrdemServico.query
    if status:
        try:
            query = query.filter_by(status=StatusOS[status])
        except KeyError:
            pass
    lista = query.order_by(OrdemServico.prioridade.desc(), OrdemServico.aberta_em.desc()).limit(150).all()
    return render_template("manutencao/ordens.html", ordens=lista, status_atual=status, StatusOS=StatusOS)


@bp.route("/ordens/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("manutencao.gerir")
def nova_ordem():
    bens = BemPatrimonial.query.filter_by(ativo=True).order_by(BemPatrimonial.descricao).all()
    if request.method == "POST":
        os_ = OrdemServico(
            numero=_num(),
            titulo=request.form["titulo"].strip(),
            descricao=request.form.get("descricao") or None,
            tipo=TipoManutencao[request.form.get("tipo", "CORRETIVA")],
            prioridade=PrioridadeOS[request.form.get("prioridade", "MEDIA")],
            local=request.form.get("local") or None,
            bem_id=int(request.form["bem_id"]) if request.form.get("bem_id") else None,
            solicitante_id=current_user.id,
            status=StatusOS.ABERTA,
        )
        if os_.tipo == TipoManutencao.PREVENTIVA and request.form.get("intervalo_dias"):
            os_.preventiva_intervalo_dias = int(request.form["intervalo_dias"])
            os_.proxima_preventiva = date.today() + timedelta(days=os_.preventiva_intervalo_dias)
        db.session.add(os_)
        db.session.commit()
        flash(f"Ordem de serviço {os_.numero} aberta.", "success")
        return redirect(url_for("manutencao.ordens"))
    return render_template("manutencao/nova_ordem.html", bens=bens,
                           tipos=TipoManutencao, prioridades=PrioridadeOS)


@bp.route("/ordens/<int:id>")
@login_required
@requer_permissao("manutencao.ver")
def detalhe_ordem(id):
    os_ = db.get_or_404(OrdemServico, id)
    return render_template("manutencao/detalhe_ordem.html", os=os_,
                           StatusOS=StatusOS)


@bp.route("/ordens/<int:id>/status", methods=["POST"])
@login_required
@requer_permissao("manutencao.gerir")
def mudar_status(id):
    os_ = db.get_or_404(OrdemServico, id)
    novo = StatusOS[request.form["status"]]
    os_.status = novo
    agora = datetime.now(timezone.utc)
    if novo == StatusOS.EM_EXECUCAO and not os_.iniciada_em:
        os_.iniciada_em = agora
        os_.executor_id = current_user.id
    elif novo == StatusOS.CONCLUIDA:
        os_.concluida_em = agora
        os_.solucao = request.form.get("solucao") or os_.solucao
        if request.form.get("custo"):
            os_.custo = float(request.form["custo"])
    db.session.commit()
    flash(f"OS atualizada para '{novo.value}'.", "success")
    return redirect(url_for("manutencao.detalhe_ordem", id=os_.id))
