"""
routes/nutricao.py — Módulo de Nutrição.

Prescrição dietética e mapa de dietas por ala.
"""

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.internacao import Internacao, StatusInternacao
from ..models.nutricao import (
    ConsistenciaDieta,
    PrescricaoDietetica,
    StatusPrescricaoDieta,
    TipoDieta,
    ViaAlimentacao,
)
from ..utils.authz import requer_permissao

bp = Blueprint("nutricao", __name__)


@bp.route("/")
@bp.route("/mapa")
@login_required
@requer_permissao("nutricao.ver")
def mapa_dietas():
    """Mapa de dietas: internações ativas agrupadas por ala com dieta vigente."""
    internacoes = Internacao.query.filter_by(
        status=StatusInternacao.ATIVA
    ).order_by(Internacao.leito_id).all()

    # Agrupa por ala, anexando a dieta ativa de cada paciente
    alas: dict = {}
    for intern in internacoes:
        dieta = PrescricaoDietetica.query.filter_by(
            internacao_id=intern.id, status=StatusPrescricaoDieta.ATIVA
        ).order_by(PrescricaoDietetica.criado_em.desc()).first()
        chave = intern.leito.ala or "Geral"
        alas.setdefault(chave, []).append((intern, dieta))

    return render_template("nutricao/mapa.html", alas=alas)


@bp.route("/prescrever/<int:internacao_id>", methods=["GET", "POST"])
@login_required
@requer_permissao("nutricao.prescrever")
def prescrever(internacao_id: int):
    """Prescrição dietética para uma internação."""
    internacao = db.get_or_404(Internacao, internacao_id)

    if request.method == "POST":
        # Encerra a dieta ativa anterior
        PrescricaoDietetica.query.filter_by(
            internacao_id=internacao.id, status=StatusPrescricaoDieta.ATIVA
        ).update({"status": StatusPrescricaoDieta.ENCERRADA})

        dieta = PrescricaoDietetica(
            internacao_id=internacao.id,
            nutricionista_id=current_user.id,
            data_prescricao=date.today(),
            tipo_dieta=TipoDieta[request.form["tipo_dieta"]],
            consistencia=ConsistenciaDieta[request.form["consistencia"]] if request.form.get("consistencia") else None,
            via=ViaAlimentacao[request.form.get("via", "ORAL")],
            valor_calorico=int(request.form["valor_calorico"]) if request.form.get("valor_calorico") else None,
            fracionamento=request.form.get("fracionamento") or None,
            restricoes=request.form.get("restricoes") or None,
            suplementos=request.form.get("suplementos") or None,
            observacoes=request.form.get("observacoes") or None,
            status=StatusPrescricaoDieta.ATIVA,
        )
        db.session.add(dieta)
        db.session.commit()
        flash("Prescrição dietética registrada.", "success")
        return redirect(url_for("nutricao.mapa_dietas"))

    return render_template(
        "nutricao/prescrever.html",
        internacao=internacao,
        tipos=TipoDieta, consistencias=ConsistenciaDieta, vias=ViaAlimentacao,
    )
