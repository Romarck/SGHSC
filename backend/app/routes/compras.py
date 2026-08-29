"""routes/compras.py — Módulo de Compras."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.compras import (
    Fornecedor,
    ItemPedidoCompra,
    ItemSolicitacaoCompra,
    PedidoCompra,
    Recebimento,
    SolicitacaoCompra,
    StatusPedido,
    StatusSolicitacaoCompra,
)
from ..models.estoque import (
    LocalEstoque,
    MovimentoEstoqueAlmox,
    ProdutoEstoque,
    SaldoEstoque,
    TipoMovimento,
)
from ..utils.authz import requer_permissao

bp = Blueprint("compras", __name__)


def _num(prefixo, model):
    ultimo = db.session.query(db.func.max(model.id)).scalar() or 0
    return f"{prefixo}{datetime.now().strftime('%Y%m%d')}{(ultimo + 1):04d}"


@bp.route("/")
@bp.route("/solicitacoes")
@login_required
@requer_permissao("compras.ver")
def solicitacoes():
    lista = SolicitacaoCompra.query.order_by(SolicitacaoCompra.criado_em.desc()).limit(100).all()
    return render_template("compras/solicitacoes.html", solicitacoes=lista)


@bp.route("/solicitacoes/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("compras.gerir")
def nova_solicitacao():
    produtos = ProdutoEstoque.query.filter_by(ativo=True).order_by(ProdutoEstoque.nome).all()
    if request.method == "POST":
        s = SolicitacaoCompra(
            numero=_num("SC", SolicitacaoCompra),
            solicitante_id=current_user.id,
            justificativa=request.form.get("justificativa") or None,
            status=StatusSolicitacaoCompra.ABERTA,
        )
        db.session.add(s)
        db.session.flush()
        descs = request.form.getlist("descricao")
        qtds = request.form.getlist("quantidade")
        pids = request.form.getlist("produto_id")
        for i, desc in enumerate(descs):
            if desc.strip():
                db.session.add(ItemSolicitacaoCompra(
                    solicitacao_id=s.id,
                    produto_id=int(pids[i]) if i < len(pids) and pids[i] else None,
                    descricao=desc.strip(),
                    quantidade=int(qtds[i]) if i < len(qtds) and qtds[i] else 1,
                ))
        db.session.commit()
        flash(f"Solicitação {s.numero} criada.", "success")
        return redirect(url_for("compras.solicitacoes"))
    return render_template("compras/nova_solicitacao.html", produtos=produtos)


@bp.route("/fornecedores", methods=["GET", "POST"])
@login_required
@requer_permissao("compras.gerir")
def fornecedores():
    if request.method == "POST":
        db.session.add(Fornecedor(
            razao_social=request.form["razao_social"].strip(),
            nome_fantasia=request.form.get("nome_fantasia") or None,
            cnpj=request.form.get("cnpj") or None,
            telefone=request.form.get("telefone") or None,
            email=request.form.get("email") or None,
        ))
        db.session.commit()
        flash("Fornecedor cadastrado.", "success")
        return redirect(url_for("compras.fornecedores"))
    lista = Fornecedor.query.order_by(Fornecedor.razao_social).all()
    return render_template("compras/fornecedores.html", fornecedores=lista)


@bp.route("/pedidos")
@login_required
@requer_permissao("compras.ver")
def pedidos():
    lista = PedidoCompra.query.order_by(PedidoCompra.criado_em.desc()).limit(100).all()
    return render_template("compras/pedidos.html", pedidos=lista)


@bp.route("/pedidos/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("compras.gerir")
def novo_pedido():
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.razao_social).all()
    produtos = ProdutoEstoque.query.filter_by(ativo=True).order_by(ProdutoEstoque.nome).all()
    if request.method == "POST":
        p = PedidoCompra(
            numero=_num("PC", PedidoCompra),
            fornecedor_id=int(request.form["fornecedor_id"]),
            emitido_por_id=current_user.id,
            status=StatusPedido.EMITIDO,
        )
        db.session.add(p)
        db.session.flush()
        total = 0
        descs = request.form.getlist("descricao")
        qtds = request.form.getlist("quantidade")
        vals = request.form.getlist("valor_unitario")
        pids = request.form.getlist("produto_id")
        for i, desc in enumerate(descs):
            if desc.strip():
                qtd = int(qtds[i]) if i < len(qtds) and qtds[i] else 1
                val = float(vals[i]) if i < len(vals) and vals[i] else 0
                total += qtd * val
                db.session.add(ItemPedidoCompra(
                    pedido_id=p.id,
                    produto_id=int(pids[i]) if i < len(pids) and pids[i] else None,
                    descricao=desc.strip(), quantidade=qtd, valor_unitario=val,
                ))
        p.valor_total = total
        db.session.commit()
        flash(f"Pedido {p.numero} emitido.", "success")
        return redirect(url_for("compras.pedidos"))
    return render_template("compras/novo_pedido.html", fornecedores=fornecedores, produtos=produtos)


@bp.route("/pedidos/<int:id>/receber", methods=["GET", "POST"])
@login_required
@requer_permissao("compras.gerir")
def receber(id):
    pedido = db.get_or_404(PedidoCompra, id)
    locais = LocalEstoque.query.filter_by(ativo=True).order_by(LocalEstoque.nome).all()
    if request.method == "POST":
        local_id = int(request.form["local_id"]) if request.form.get("local_id") else None
        rec = Recebimento(
            pedido_id=pedido.id, nota_fiscal=request.form.get("nota_fiscal") or None,
            local_id=local_id, recebido_por_id=current_user.id,
        )
        db.session.add(rec)
        # Dá entrada no estoque para cada item com produto vinculado
        if local_id:
            for item in pedido.itens:
                if item.produto_id:
                    saldo = SaldoEstoque.query.filter_by(produto_id=item.produto_id, local_id=local_id).first()
                    if not saldo:
                        saldo = SaldoEstoque(produto_id=item.produto_id, local_id=local_id, quantidade=0)
                        db.session.add(saldo); db.session.flush()
                    saldo.quantidade += item.quantidade
                    item.quantidade_recebida = item.quantidade
                    db.session.add(MovimentoEstoqueAlmox(
                        produto_id=item.produto_id, local_id=local_id,
                        tipo=TipoMovimento.ENTRADA, quantidade=item.quantidade,
                        motivo=f"Recebimento pedido {pedido.numero}",
                        responsavel_id=current_user.id,
                    ))
        pedido.status = StatusPedido.RECEBIDO
        db.session.commit()
        flash(f"Recebimento do pedido {pedido.numero} registrado; estoque atualizado.", "success")
        return redirect(url_for("compras.pedidos"))
    return render_template("compras/receber.html", pedido=pedido, locais=locais)
