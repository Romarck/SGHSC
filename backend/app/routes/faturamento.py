"""routes/faturamento.py — Faturamento SUS (AIH/APAC/BPA)."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.faturamento import (
    GuiaFaturamento,
    ItemGuiaFaturamento,
    ProcedimentoSIGTAP,
    StatusFaturamento,
    TipoProducao,
)
from ..models.paciente import Paciente
from ..utils.authz import requer_permissao

bp = Blueprint("faturamento", __name__)


def _num():
    ultimo = db.session.query(db.func.max(GuiaFaturamento.id)).scalar() or 0
    return f"FAT{datetime.now().strftime('%Y%m%d')}{(ultimo + 1):04d}"


@bp.route("/")
@bp.route("/guias")
@login_required
@requer_permissao("faturamento.ver")
def guias():
    tipo = request.args.get("tipo")
    query = GuiaFaturamento.query
    if tipo:
        try:
            query = query.filter_by(tipo=TipoProducao[tipo])
        except KeyError:
            pass
    lista = query.order_by(GuiaFaturamento.criado_em.desc()).limit(100).all()
    return render_template("faturamento/guias.html", guias=lista, tipo_atual=tipo, TipoProducao=TipoProducao)


@bp.route("/guias/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("faturamento.gerir")
def nova_guia():
    paciente_id = request.args.get("paciente_id")
    paciente = Paciente.query.get(int(paciente_id)) if paciente_id else None
    if request.method == "POST":
        g = GuiaFaturamento(
            numero=_num(),
            tipo=TipoProducao[request.form["tipo"]],
            paciente_id=int(request.form["paciente_id"]) if request.form.get("paciente_id") else None,
            competencia=request.form["competencia"].strip(),
            cid_principal=request.form.get("cid_principal") or None,
            procedimento_principal=request.form.get("procedimento_principal") or None,
            criado_por_id=current_user.id,
            status=StatusFaturamento.ABERTA,
        )
        db.session.add(g)
        db.session.flush()
        total = 0
        cods = request.form.getlist("cod_proc")
        qtds = request.form.getlist("qtd_proc")
        vals = request.form.getlist("val_proc")
        for i, cod in enumerate(cods):
            if cod.strip():
                qtd = int(qtds[i]) if i < len(qtds) and qtds[i] else 1
                val = float(vals[i]) if i < len(vals) and vals[i] else 0
                total += qtd * val
                db.session.add(ItemGuiaFaturamento(
                    guia_id=g.id, codigo_procedimento=cod.strip(),
                    quantidade=qtd, valor_unitario=val,
                ))
        g.valor_total = total
        db.session.commit()
        flash(f"Guia {g.numero} criada.", "success")
        return redirect(url_for("faturamento.guias"))
    return render_template("faturamento/nova_guia.html", paciente=paciente, tipos=TipoProducao)


@bp.route("/guias/<int:id>/exportar")
@login_required
@requer_permissao("faturamento.gerir")
def exportar(id):
    """
    Exportação DATASUS (stub). A geração dos arquivos magnéticos no layout
    oficial (SISAIH01, BPA-MAG) depende das tabelas SIGTAP e do layout binário
    específico do DATASUS, a ser implementado com as tabelas oficiais.
    """
    g = db.get_or_404(GuiaFaturamento, id)
    g.status = StatusFaturamento.EXPORTADA
    db.session.commit()
    flash("Guia marcada como exportada. Geração do arquivo magnético DATASUS "
          "será implementada com as tabelas SIGTAP oficiais.", "info")
    return redirect(url_for("faturamento.guias"))


@bp.route("/procedimentos", methods=["GET", "POST"])
@login_required
@requer_permissao("faturamento.gerir")
def procedimentos():
    if request.method == "POST":
        db.session.add(ProcedimentoSIGTAP(
            codigo=request.form["codigo"].strip(),
            nome=request.form["nome"].strip(),
            complexidade=request.form.get("complexidade") or None,
            valor_sus=float(request.form["valor_sus"]) if request.form.get("valor_sus") else 0,
        ))
        db.session.commit()
        flash("Procedimento SIGTAP cadastrado.", "success")
        return redirect(url_for("faturamento.procedimentos"))
    lista = ProcedimentoSIGTAP.query.order_by(ProcedimentoSIGTAP.codigo).limit(200).all()
    return render_template("faturamento/procedimentos.html", procedimentos=lista)
