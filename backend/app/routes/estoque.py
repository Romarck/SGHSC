"""routes/estoque.py — Almoxarifado / Estoque."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.estoque import (
    CategoriaProduto,
    Inventario,
    ItemRequisicao,
    LocalEstoque,
    MovimentoEstoqueAlmox,
    ProdutoEstoque,
    RequisicaoMaterial,
    SaldoEstoque,
    StatusRequisicao,
    TipoMovimento,
    UnidadeMedida,
)
from ..utils.authz import requer_permissao

bp = Blueprint("estoque", __name__)


def _num(prefixo, model):
    ultimo = db.session.query(db.func.max(model.id)).scalar() or 0
    return f"{prefixo}{datetime.now().strftime('%Y%m%d')}{(ultimo + 1):04d}"


def _saldo(produto_id, local_id):
    saldo = SaldoEstoque.query.filter_by(produto_id=produto_id, local_id=local_id).first()
    if not saldo:
        saldo = SaldoEstoque(produto_id=produto_id, local_id=local_id, quantidade=0)
        db.session.add(saldo)
        db.session.flush()
    return saldo


@bp.route("/")
@bp.route("/produtos")
@login_required
@requer_permissao("estoque.ver")
def produtos():
    busca = request.args.get("q", "").strip()
    query = ProdutoEstoque.query.filter_by(ativo=True)
    if busca:
        like = f"%{busca}%"
        query = query.filter(db.or_(ProdutoEstoque.nome.ilike(like), ProdutoEstoque.codigo.ilike(like)))
    produtos = query.order_by(ProdutoEstoque.nome).all()
    abaixo = [p for p in produtos if p.abaixo_minimo]
    return render_template("estoque/produtos.html", produtos=produtos, busca=busca, abaixo=abaixo)


@bp.route("/produtos/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("estoque.gerir")
def novo_produto():
    if request.method == "POST":
        p = ProdutoEstoque(
            codigo=request.form["codigo"].strip(),
            nome=request.form["nome"].strip(),
            categoria=CategoriaProduto[request.form["categoria"]],
            unidade=UnidadeMedida[request.form.get("unidade", "UNIDADE")],
            estoque_minimo=int(request.form.get("estoque_minimo") or 0),
        )
        db.session.add(p)
        db.session.commit()
        flash(f"Produto '{p.nome}' cadastrado.", "success")
        return redirect(url_for("estoque.produtos"))
    return render_template("estoque/form_produto.html",
                           categorias=CategoriaProduto, unidades=UnidadeMedida)


@bp.route("/produtos/<int:id>/movimentar", methods=["GET", "POST"])
@login_required
@requer_permissao("estoque.gerir")
def movimentar(id):
    produto = db.get_or_404(ProdutoEstoque, id)
    locais = LocalEstoque.query.filter_by(ativo=True).order_by(LocalEstoque.nome).all()
    if request.method == "POST":
        local_id = int(request.form["local_id"])
        tipo = TipoMovimento[request.form["tipo"]]
        qtd = int(request.form["quantidade"])
        saldo = _saldo(produto.id, local_id)
        delta = qtd if tipo in (TipoMovimento.ENTRADA, TipoMovimento.AJUSTE) else -qtd
        saldo.quantidade = max(0, saldo.quantidade + delta)
        db.session.add(MovimentoEstoqueAlmox(
            produto_id=produto.id, local_id=local_id, tipo=tipo, quantidade=delta,
            motivo=request.form.get("motivo") or None, responsavel_id=current_user.id,
        ))
        db.session.commit()
        flash("Movimentação registrada.", "success")
        return redirect(url_for("estoque.produtos"))
    return render_template("estoque/movimentar.html", produto=produto, locais=locais, tipos=TipoMovimento)


@bp.route("/locais", methods=["GET", "POST"])
@login_required
@requer_permissao("estoque.gerir")
def locais():
    if request.method == "POST":
        db.session.add(LocalEstoque(
            nome=request.form["nome"].strip(),
            descricao=request.form.get("descricao") or None,
            principal=bool(request.form.get("principal")),
        ))
        db.session.commit()
        flash("Local cadastrado.", "success")
        return redirect(url_for("estoque.locais"))
    lista = LocalEstoque.query.order_by(LocalEstoque.nome).all()
    return render_template("estoque/locais.html", locais=lista)


@bp.route("/requisicoes")
@login_required
@requer_permissao("estoque.ver")
def requisicoes():
    lista = RequisicaoMaterial.query.order_by(RequisicaoMaterial.criado_em.desc()).limit(100).all()
    return render_template("estoque/requisicoes.html", requisicoes=lista)


@bp.route("/requisicoes/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("estoque.gerir")
def nova_requisicao():
    produtos = ProdutoEstoque.query.filter_by(ativo=True).order_by(ProdutoEstoque.nome).all()
    if request.method == "POST":
        req = RequisicaoMaterial(
            numero=_num("REQ", RequisicaoMaterial),
            setor_solicitante=request.form.get("setor") or None,
            solicitante_id=current_user.id,
            observacoes=request.form.get("observacoes") or None,
            status=StatusRequisicao.PENDENTE,
        )
        db.session.add(req)
        db.session.flush()
        pids = request.form.getlist("produto_id")
        qtds = request.form.getlist("quantidade")
        for i, pid in enumerate(pids):
            if pid and i < len(qtds) and qtds[i]:
                db.session.add(ItemRequisicao(
                    requisicao_id=req.id, produto_id=int(pid),
                    quantidade_solicitada=int(qtds[i]),
                ))
        db.session.commit()
        flash(f"Requisição {req.numero} criada.", "success")
        return redirect(url_for("estoque.requisicoes"))
    return render_template("estoque/nova_requisicao.html", produtos=produtos)


@bp.route("/inventarios")
@login_required
@requer_permissao("estoque.ver")
def inventarios():
    lista = Inventario.query.order_by(Inventario.criado_em.desc()).all()
    return render_template("estoque/inventarios.html", inventarios=lista)
