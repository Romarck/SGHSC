"""routes/financeiro.py — Módulo Financeiro."""

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.financeiro import (
    CategoriaFinanceira,
    Conta,
    LancamentoCaixa,
    StatusConta,
    TipoConta,
    TipoLancamento,
)
from ..utils.authz import requer_permissao

bp = Blueprint("financeiro", __name__)


@bp.route("/")
def _root():
    return redirect(url_for("financeiro.contas"))


@bp.route("/contas")
@login_required
@requer_permissao("financeiro.ver")
def contas():
    tipo = request.args.get("tipo")
    query = Conta.query
    if tipo in ("PAGAR", "RECEBER"):
        query = query.filter_by(tipo=TipoConta[tipo])
    lista = query.order_by(Conta.vencimento).limit(200).all()
    total_pagar = sum(float(c.valor) for c in lista if c.tipo == TipoConta.PAGAR and c.status == StatusConta.ABERTA)
    total_receber = sum(float(c.valor) for c in lista if c.tipo == TipoConta.RECEBER and c.status == StatusConta.ABERTA)
    return render_template("financeiro/contas.html", contas=lista, tipo_atual=tipo,
                           total_pagar=total_pagar, total_receber=total_receber)


@bp.route("/contas/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("financeiro.gerir")
def nova_conta():
    categorias = CategoriaFinanceira.query.filter_by(ativo=True).order_by(CategoriaFinanceira.nome).all()
    if request.method == "POST":
        c = Conta(
            descricao=request.form["descricao"].strip(),
            tipo=TipoConta[request.form["tipo"]],
            valor=float(request.form["valor"]),
            vencimento=date.fromisoformat(request.form["vencimento"]),
            categoria_id=int(request.form["categoria_id"]) if request.form.get("categoria_id") else None,
            convenio=request.form.get("convenio") or None,
            criado_por_id=current_user.id,
            status=StatusConta.ABERTA,
        )
        db.session.add(c)
        db.session.commit()
        flash("Conta registrada.", "success")
        return redirect(url_for("financeiro.contas"))
    return render_template("financeiro/nova_conta.html", categorias=categorias, tipos=TipoConta)


@bp.route("/contas/<int:id>/baixar", methods=["POST"])
@login_required
@requer_permissao("financeiro.gerir")
def baixar_conta(id):
    c = db.get_or_404(Conta, id)
    c.status = StatusConta.PAGA if c.tipo == TipoConta.PAGAR else StatusConta.RECEBIDA
    c.data_pagamento = date.today()
    c.valor_pago = c.valor
    # Lança no caixa
    db.session.add(LancamentoCaixa(
        descricao=f"Baixa: {c.descricao}",
        tipo=TipoLancamento.SAIDA if c.tipo == TipoConta.PAGAR else TipoLancamento.ENTRADA,
        valor=c.valor, data=date.today(),
        categoria_id=c.categoria_id, conta_id=c.id,
        registrado_por_id=current_user.id,
    ))
    db.session.commit()
    flash("Conta baixada e lançada no caixa.", "success")
    return redirect(url_for("financeiro.contas"))


@bp.route("/caixa")
@login_required
@requer_permissao("financeiro.ver")
def caixa():
    lancamentos = LancamentoCaixa.query.order_by(LancamentoCaixa.data.desc()).limit(200).all()
    entradas = sum(float(l.valor) for l in lancamentos if l.tipo == TipoLancamento.ENTRADA)
    saidas = sum(float(l.valor) for l in lancamentos if l.tipo == TipoLancamento.SAIDA)
    return render_template("financeiro/caixa.html", lancamentos=lancamentos,
                           entradas=entradas, saidas=saidas, saldo=entradas - saidas)


@bp.route("/categorias", methods=["GET", "POST"])
@login_required
@requer_permissao("financeiro.gerir")
def categorias():
    if request.method == "POST":
        db.session.add(CategoriaFinanceira(
            nome=request.form["nome"].strip(),
            tipo=TipoLancamento[request.form["tipo"]] if request.form.get("tipo") else None,
        ))
        db.session.commit()
        flash("Categoria criada.", "success")
        return redirect(url_for("financeiro.categorias"))
    lista = CategoriaFinanceira.query.order_by(CategoriaFinanceira.nome).all()
    return render_template("financeiro/categorias.html", categorias=lista, tipos=TipoLancamento)
