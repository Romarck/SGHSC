"""routes/convenios.py — Faturamento de convênios (TISS)."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.convenios import (
    Convenio,
    GuiaConvenio,
    ItemGuiaConvenio,
    ProcedimentoCBHPM,
    StatusGuia,
    TipoGuia,
)
from ..models.paciente import Paciente
from ..utils.authz import requer_permissao

bp = Blueprint("convenios", __name__)


def _num():
    ultimo = db.session.query(db.func.max(GuiaConvenio.id)).scalar() or 0
    return f"GC{datetime.now().strftime('%Y%m%d')}{(ultimo + 1):04d}"


@bp.route("/")
def _root():
    return redirect(url_for("convenios.guias"))


@bp.route("/guias")
@login_required
@requer_permissao("convenios.ver")
def guias():
    lista = GuiaConvenio.query.order_by(GuiaConvenio.criado_em.desc()).limit(100).all()
    return render_template("convenios/guias.html", guias=lista)


@bp.route("/guias/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("convenios.gerir")
def nova_guia():
    paciente_id = request.args.get("paciente_id")
    paciente = Paciente.query.get(int(paciente_id)) if paciente_id else None
    convenios = Convenio.query.filter_by(ativo=True).order_by(Convenio.nome).all()
    if request.method == "POST":
        g = GuiaConvenio(
            numero=_num(),
            tipo=TipoGuia[request.form["tipo"]],
            convenio_id=int(request.form["convenio_id"]),
            paciente_id=int(request.form["paciente_id"]),
            numero_carteirinha=request.form.get("numero_carteirinha") or None,
            senha_autorizacao=request.form.get("senha_autorizacao") or None,
            criado_por_id=current_user.id,
            status=StatusGuia.ABERTA,
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
                db.session.add(ItemGuiaConvenio(
                    guia_id=g.id, codigo_procedimento=cod.strip(),
                    quantidade=qtd, valor_unitario=val,
                ))
        g.valor_total = total
        db.session.commit()
        flash(f"Guia {g.numero} criada.", "success")
        return redirect(url_for("convenios.guias"))
    return render_template("convenios/nova_guia.html", paciente=paciente,
                           convenios=convenios, tipos=TipoGuia)


@bp.route("/operadoras", methods=["GET", "POST"])
@login_required
@requer_permissao("convenios.gerir")
def operadoras():
    if request.method == "POST":
        db.session.add(Convenio(
            nome=request.form["nome"].strip(),
            registro_ans=request.form.get("registro_ans") or None,
            cnpj=request.form.get("cnpj") or None,
            tabela_preco=request.form.get("tabela_preco") or None,
        ))
        db.session.commit()
        flash("Convênio cadastrado.", "success")
        return redirect(url_for("convenios.operadoras"))
    lista = Convenio.query.order_by(Convenio.nome).all()
    return render_template("convenios/operadoras.html", convenios=lista)


@bp.route("/procedimentos", methods=["GET", "POST"])
@login_required
@requer_permissao("convenios.gerir")
def procedimentos():
    if request.method == "POST":
        db.session.add(ProcedimentoCBHPM(
            codigo=request.form["codigo"].strip(),
            nome=request.form["nome"].strip(),
            porte=request.form.get("porte") or None,
            valor_referencia=float(request.form["valor_referencia"]) if request.form.get("valor_referencia") else 0,
        ))
        db.session.commit()
        flash("Procedimento CBHPM/TUSS cadastrado.", "success")
        return redirect(url_for("convenios.procedimentos"))
    lista = ProcedimentoCBHPM.query.order_by(ProcedimentoCBHPM.codigo).limit(200).all()
    return render_template("convenios/procedimentos.html", procedimentos=lista)
