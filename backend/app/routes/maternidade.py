"""
routes/maternidade.py — Módulo de Maternidade.

Pré-natal, registro de parto e recém-nascido.
"""

from datetime import date, datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.maternidade import (
    ClassificacaoRisco,
    CondicaoNascimento,
    ConsultaPreNatal,
    Parto,
    PreNatal,
    RecemNascido,
    SexoRN,
    TipoParto,
)
from ..models.paciente import Paciente
from ..utils.authz import requer_permissao

bp = Blueprint("maternidade", __name__)


def _gerar_numero_parto() -> str:
    agora = datetime.now()
    ultimo = db.session.query(db.func.max(Parto.id)).scalar() or 0
    return f"PART{agora.strftime('%Y%m%d')}{(ultimo + 1):04d}"


@bp.route("/")
@login_required
@requer_permissao("maternidade.ver")
def painel():
    """Painel: pré-natais ativos + partos recentes."""
    prenatais = PreNatal.query.filter_by(ativo=True).order_by(
        PreNatal.criado_em.desc()
    ).limit(50).all()
    partos = Parto.query.order_by(Parto.data_parto.desc()).limit(20).all()
    return render_template("maternidade/painel.html", prenatais=prenatais, partos=partos)


# ---------------------------------------------------------------------------
# Pré-natal
# ---------------------------------------------------------------------------

@bp.route("/prenatal/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("maternidade.gerir")
def novo_prenatal():
    paciente_id = request.args.get("paciente_id")
    paciente = Paciente.query.get(int(paciente_id)) if paciente_id else None

    if request.method == "POST":
        dum = request.form.get("dum")
        dpp = request.form.get("dpp")
        pn = PreNatal(
            gestante_id=int(request.form["gestante_id"]),
            dum=date.fromisoformat(dum) if dum else None,
            dpp=date.fromisoformat(dpp) if dpp else None,
            gestacoes=int(request.form.get("gestacoes") or 0),
            partos=int(request.form.get("partos") or 0),
            abortos=int(request.form.get("abortos") or 0),
            cesareas=int(request.form.get("cesareas") or 0),
            classificacao_risco=ClassificacaoRisco[request.form.get("classificacao_risco", "HABITUAL")],
            tipo_sanguineo=request.form.get("tipo_sanguineo") or None,
            observacoes=request.form.get("observacoes") or None,
            medico_id=current_user.id,
        )
        db.session.add(pn)
        db.session.commit()
        flash("Pré-natal cadastrado.", "success")
        return redirect(url_for("maternidade.detalhe_prenatal", id=pn.id))

    return render_template("maternidade/form_prenatal.html", paciente=paciente,
                           riscos=ClassificacaoRisco)


@bp.route("/prenatal/<int:id>", methods=["GET", "POST"])
@login_required
@requer_permissao("maternidade.gerir")
def detalhe_prenatal(id: int):
    """Detalhe do pré-natal + registro de consultas."""
    pn = db.get_or_404(PreNatal, id)
    if request.method == "POST":
        c = ConsultaPreNatal(
            prenatal_id=pn.id,
            data_consulta=date.fromisoformat(request.form["data_consulta"]),
            idade_gestacional_semanas=int(request.form["ig"]) if request.form.get("ig") else None,
            peso=request.form.get("peso") or None,
            pressao_arterial=request.form.get("pressao_arterial") or None,
            altura_uterina=int(request.form["altura_uterina"]) if request.form.get("altura_uterina") else None,
            bcf=int(request.form["bcf"]) if request.form.get("bcf") else None,
            movimentacao_fetal=bool(request.form.get("movimentacao_fetal")),
            edema=request.form.get("edema") or None,
            observacoes=request.form.get("observacoes") or None,
        )
        db.session.add(c)
        db.session.commit()
        flash("Consulta de pré-natal registrada.", "success")
        return redirect(url_for("maternidade.detalhe_prenatal", id=pn.id))
    return render_template("maternidade/detalhe_prenatal.html", pn=pn)


# ---------------------------------------------------------------------------
# Parto e recém-nascido
# ---------------------------------------------------------------------------

@bp.route("/parto/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("maternidade.gerir")
def novo_parto():
    paciente_id = request.args.get("paciente_id")
    paciente = Paciente.query.get(int(paciente_id)) if paciente_id else None

    if request.method == "POST":
        parto = Parto(
            numero=_gerar_numero_parto(),
            gestante_id=int(request.form["gestante_id"]),
            internacao_id=int(request.form["internacao_id"]) if request.form.get("internacao_id") else None,
            tipo=TipoParto[request.form["tipo"]],
            data_parto=datetime.fromisoformat(request.form["data_parto"]) if request.form.get("data_parto") else datetime.now(timezone.utc),
            idade_gestacional_semanas=int(request.form["ig"]) if request.form.get("ig") else None,
            medico_id=current_user.id,
            tipo_anestesia=request.form.get("tipo_anestesia") or None,
            intercorrencias=request.form.get("intercorrencias") or None,
            descricao=request.form.get("descricao") or None,
        )
        db.session.add(parto)
        db.session.flush()

        # Recém-nascidos (pode haver múltiplos)
        sexos = request.form.getlist("rn_sexo")
        pesos = request.form.getlist("rn_peso")
        apgar1 = request.form.getlist("rn_apgar1")
        apgar5 = request.form.getlist("rn_apgar5")
        condicoes = request.form.getlist("rn_condicao")
        for i, sexo in enumerate(sexos):
            if not sexo:
                continue
            db.session.add(RecemNascido(
                parto_id=parto.id,
                sexo=SexoRN[sexo],
                condicao=CondicaoNascimento[condicoes[i]] if i < len(condicoes) and condicoes[i] else CondicaoNascimento.VIVO,
                peso_gramas=int(pesos[i]) if i < len(pesos) and pesos[i] else None,
                apgar_1min=int(apgar1[i]) if i < len(apgar1) and apgar1[i] else None,
                apgar_5min=int(apgar5[i]) if i < len(apgar5) and apgar5[i] else None,
                hora_nascimento=parto.data_parto,
            ))
        db.session.commit()
        flash(f"Parto {parto.numero} registrado.", "success")
        return redirect(url_for("maternidade.detalhe_parto", id=parto.id))

    return render_template("maternidade/form_parto.html", paciente=paciente,
                           tipos=TipoParto, sexos=SexoRN, condicoes=CondicaoNascimento)


@bp.route("/parto/<int:id>")
@login_required
@requer_permissao("maternidade.ver")
def detalhe_parto(id: int):
    parto = db.get_or_404(Parto, id)
    return render_template("maternidade/detalhe_parto.html", parto=parto)
