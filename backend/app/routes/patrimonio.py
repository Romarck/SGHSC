"""routes/patrimonio.py — Gestão de Patrimônio."""

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.patrimonio import (
    BemPatrimonial,
    EstadoConservacao,
    MovimentacaoBem,
    SituacaoBem,
)
from ..utils.authz import requer_permissao

bp = Blueprint("patrimonio", __name__)


@bp.route("/")
@bp.route("/bens")
@login_required
@requer_permissao("patrimonio.ver")
def bens():
    busca = request.args.get("q", "").strip()
    query = BemPatrimonial.query.filter_by(ativo=True)
    if busca:
        like = f"%{busca}%"
        query = query.filter(db.or_(
            BemPatrimonial.descricao.ilike(like),
            BemPatrimonial.numero_patrimonio.ilike(like),
        ))
    lista = query.order_by(BemPatrimonial.numero_patrimonio).all()
    return render_template("patrimonio/bens.html", bens=lista, busca=busca)


@bp.route("/bens/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("patrimonio.gerir")
def novo_bem():
    if request.method == "POST":
        b = BemPatrimonial(
            numero_patrimonio=request.form["numero_patrimonio"].strip(),
            descricao=request.form["descricao"].strip(),
            categoria=request.form.get("categoria") or None,
            marca=request.form.get("marca") or None,
            modelo=request.form.get("modelo") or None,
            numero_serie=request.form.get("numero_serie") or None,
            localizacao=request.form.get("localizacao") or None,
            situacao=SituacaoBem[request.form.get("situacao", "ATIVO")],
            estado=EstadoConservacao[request.form["estado"]] if request.form.get("estado") else None,
            valor_aquisicao=float(request.form["valor_aquisicao"]) if request.form.get("valor_aquisicao") else None,
            data_aquisicao=date.fromisoformat(request.form["data_aquisicao"]) if request.form.get("data_aquisicao") else None,
            vida_util_anos=int(request.form["vida_util_anos"]) if request.form.get("vida_util_anos") else None,
        )
        db.session.add(b)
        db.session.commit()
        flash(f"Bem {b.numero_patrimonio} cadastrado.", "success")
        return redirect(url_for("patrimonio.bens"))
    return render_template("patrimonio/form_bem.html",
                           situacoes=SituacaoBem, estados=EstadoConservacao)


@bp.route("/bens/<int:id>")
@login_required
@requer_permissao("patrimonio.ver")
def detalhe_bem(id):
    bem = db.get_or_404(BemPatrimonial, id)
    return render_template("patrimonio/detalhe_bem.html", bem=bem)


@bp.route("/bens/<int:id>/mover", methods=["POST"])
@login_required
@requer_permissao("patrimonio.gerir")
def mover_bem(id):
    bem = db.get_or_404(BemPatrimonial, id)
    destino = request.form["localizacao_destino"].strip()
    db.session.add(MovimentacaoBem(
        bem_id=bem.id, localizacao_origem=bem.localizacao,
        localizacao_destino=destino, motivo=request.form.get("motivo") or None,
        responsavel_id=current_user.id,
    ))
    bem.localizacao = destino
    db.session.commit()
    flash("Bem movimentado.", "success")
    return redirect(url_for("patrimonio.detalhe_bem", id=bem.id))
