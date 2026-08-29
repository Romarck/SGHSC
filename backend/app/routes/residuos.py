"""routes/residuos.py — PGRSS (gestão de resíduos)."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.residuos import (
    ColetaResiduo,
    GrupoResiduo,
    RegistroResiduo,
    StatusColeta,
)
from ..utils.authz import requer_permissao

bp = Blueprint("residuos", __name__)


def _num():
    ultimo = db.session.query(db.func.max(ColetaResiduo.id)).scalar() or 0
    return f"COL{datetime.now().strftime('%Y%m%d')}{(ultimo + 1):04d}"


@bp.route("/")
@bp.route("/painel")
@login_required
@requer_permissao("residuos.ver")
def painel():
    registros = RegistroResiduo.query.order_by(RegistroResiduo.gerado_em.desc()).limit(100).all()
    # Totais por grupo (armazenados, ainda não coletados)
    por_grupo = {}
    for g in GrupoResiduo:
        peso = db.session.query(db.func.coalesce(db.func.sum(RegistroResiduo.peso_kg), 0)).filter(
            RegistroResiduo.grupo == g, RegistroResiduo.status == StatusColeta.ARMAZENADO
        ).scalar()
        por_grupo[g] = float(peso)
    return render_template("residuos/painel.html", registros=registros,
                           por_grupo=por_grupo, grupos=GrupoResiduo)


@bp.route("/registrar", methods=["GET", "POST"])
@login_required
@requer_permissao("residuos.gerir")
def registrar():
    if request.method == "POST":
        db.session.add(RegistroResiduo(
            grupo=GrupoResiduo[request.form["grupo"]],
            origem_setor=request.form.get("origem_setor") or None,
            peso_kg=float(request.form["peso_kg"]),
            descricao=request.form.get("descricao") or None,
            acondicionamento=request.form.get("acondicionamento") or None,
            registrado_por_id=current_user.id,
            status=StatusColeta.ARMAZENADO,
        ))
        db.session.commit()
        flash("Resíduo registrado.", "success")
        return redirect(url_for("residuos.painel"))
    return render_template("residuos/registrar.html", grupos=GrupoResiduo)


@bp.route("/coletas")
@login_required
@requer_permissao("residuos.ver")
def coletas():
    lista = ColetaResiduo.query.order_by(ColetaResiduo.coletado_em.desc()).limit(100).all()
    return render_template("residuos/coletas.html", coletas=lista)


@bp.route("/coletas/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("residuos.gerir")
def nova_coleta():
    # Registros armazenados disponíveis para coleta
    disponiveis = RegistroResiduo.query.filter_by(status=StatusColeta.ARMAZENADO).order_by(
        RegistroResiduo.gerado_em
    ).all()
    if request.method == "POST":
        coleta = ColetaResiduo(
            numero=_num(),
            empresa_coletora=request.form["empresa_coletora"].strip(),
            numero_manifesto=request.form.get("numero_manifesto") or None,
            destinacao_final=request.form.get("destinacao_final") or None,
            observacoes=request.form.get("observacoes") or None,
            responsavel_id=current_user.id,
        )
        db.session.add(coleta)
        db.session.flush()
        # Vincula os registros selecionados e soma o peso
        ids = request.form.getlist("registro_id")
        total = 0
        for rid in ids:
            reg = db.session.get(RegistroResiduo, int(rid))
            if reg and reg.status == StatusColeta.ARMAZENADO:
                reg.status = StatusColeta.COLETADO
                reg.coleta_id = coleta.id
                total += float(reg.peso_kg)
        coleta.peso_total_kg = total
        db.session.commit()
        flash(f"Coleta {coleta.numero} registrada ({total:.3f} kg).", "success")
        return redirect(url_for("residuos.coletas"))
    return render_template("residuos/nova_coleta.html", disponiveis=disponiveis)
