"""
routes/farmacia.py — Módulo de Farmácia Hospitalar.

Dispensação por prescrição, controle de estoque, entradas e ajustes.
"""

from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.farmacia import (
    Dispensacao,
    FormaFarmaceutica,
    ItemDispensacao,
    LoteEstoque,
    MedicamentoFarmacia,
    MovimentoEstoque,
    StatusDispensacao,
    TipoMovimentoEstoque,
)
from ..models.internacao import Internacao, StatusInternacao
from ..utils.authz import requer_permissao

bp = Blueprint("farmacia", __name__)


def _gerar_numero_dispensacao() -> str:
    agora = datetime.now()
    ultimo = db.session.query(db.func.max(Dispensacao.id)).scalar() or 0
    return f"DISP{agora.strftime('%Y%m%d')}{(ultimo + 1):04d}"


def _registrar_movimento(medicamento, tipo, quantidade, motivo=None,
                         lote=None, dispensacao_id=None):
    """Registra um movimento de estoque e ajusta o saldo do lote."""
    if lote is not None:
        lote.quantidade = max(0, lote.quantidade + quantidade)
    mov = MovimentoEstoque(
        medicamento_id=medicamento.id,
        lote_id=lote.id if lote else None,
        tipo=tipo,
        quantidade=quantidade,
        saldo_apos=medicamento.estoque_total,
        motivo=motivo,
        dispensacao_id=dispensacao_id,
        responsavel_id=current_user.id,
    )
    db.session.add(mov)
    return mov


# ---------------------------------------------------------------------------
# Estoque
# ---------------------------------------------------------------------------

@bp.route("/")
@bp.route("/estoque")
@login_required
@requer_permissao("farmacia.ver")
def estoque():
    """Lista de medicamentos com saldo de estoque; destaca abaixo do mínimo."""
    busca = request.args.get("q", "").strip()
    query = MedicamentoFarmacia.query.filter_by(ativo=True)
    if busca:
        like = f"%{busca}%"
        query = query.filter(db.or_(
            MedicamentoFarmacia.nome.ilike(like),
            MedicamentoFarmacia.principio_ativo.ilike(like),
            MedicamentoFarmacia.codigo.ilike(like),
        ))
    medicamentos = query.order_by(MedicamentoFarmacia.nome).all()
    abaixo_minimo = [m for m in medicamentos if m.abaixo_minimo]
    return render_template(
        "farmacia/estoque.html",
        medicamentos=medicamentos, busca=busca, abaixo_minimo=abaixo_minimo,
    )


@bp.route("/medicamento/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("farmacia.gerir")
def novo_medicamento():
    """Cadastro de medicamento."""
    if request.method == "POST":
        med = MedicamentoFarmacia(
            codigo=request.form.get("codigo", "").strip(),
            nome=request.form.get("nome", "").strip(),
            principio_ativo=request.form.get("principio_ativo") or None,
            concentracao=request.form.get("concentracao") or None,
            forma=FormaFarmaceutica[request.form["forma"]] if request.form.get("forma") else None,
            unidade_dispensacao=request.form.get("unidade_dispensacao") or None,
            controlado=bool(request.form.get("controlado")),
            estoque_minimo=int(request.form.get("estoque_minimo") or 0),
        )
        db.session.add(med)
        db.session.commit()
        flash(f"Medicamento '{med.nome}' cadastrado.", "success")
        return redirect(url_for("farmacia.estoque"))
    return render_template("farmacia/form_medicamento.html", formas=FormaFarmaceutica)


@bp.route("/medicamento/<int:id>/entrada", methods=["GET", "POST"])
@login_required
@requer_permissao("farmacia.gerir")
def entrada_estoque(id: int):
    """Entrada de estoque (novo lote)."""
    med = db.get_or_404(MedicamentoFarmacia, id)
    if request.method == "POST":
        qtd = int(request.form.get("quantidade") or 0)
        if qtd <= 0:
            flash("Quantidade deve ser maior que zero.", "warning")
            return redirect(url_for("farmacia.entrada_estoque", id=med.id))
        validade = request.form.get("validade")
        lote = LoteEstoque(
            medicamento_id=med.id,
            numero_lote=request.form.get("numero_lote") or None,
            validade=date.fromisoformat(validade) if validade else None,
            quantidade=0,
            fabricante=request.form.get("fabricante") or None,
        )
        db.session.add(lote)
        db.session.flush()
        _registrar_movimento(med, TipoMovimentoEstoque.ENTRADA, qtd,
                             motivo="Entrada de estoque", lote=lote)
        db.session.commit()
        flash(f"Entrada de {qtd} unidades registrada para '{med.nome}'.", "success")
        return redirect(url_for("farmacia.estoque"))
    return render_template("farmacia/entrada.html", med=med)


@bp.route("/medicamento/<int:id>/movimentos")
@login_required
@requer_permissao("farmacia.ver")
def movimentos(id: int):
    """Histórico de movimentos de um medicamento."""
    med = db.get_or_404(MedicamentoFarmacia, id)
    movs = MovimentoEstoque.query.filter_by(medicamento_id=med.id).order_by(
        MovimentoEstoque.registrado_em.desc()
    ).limit(200).all()
    return render_template("farmacia/movimentos.html", med=med, movimentos=movs)


# ---------------------------------------------------------------------------
# Dispensação
# ---------------------------------------------------------------------------

@bp.route("/dispensar", methods=["GET"])
@login_required
@requer_permissao("farmacia.dispensar")
def dispensar_lista():
    """Lista de internações ativas para dispensação por prescrição."""
    internacoes = Internacao.query.filter_by(
        status=StatusInternacao.ATIVA
    ).order_by(Internacao.admissao_em).all()
    return render_template("farmacia/dispensar_lista.html", internacoes=internacoes)


@bp.route("/dispensar/<int:internacao_id>", methods=["GET", "POST"])
@login_required
@requer_permissao("farmacia.dispensar")
def dispensar(internacao_id: int):
    """Dispensa medicamentos com base na prescrição médica ativa."""
    internacao = db.get_or_404(Internacao, internacao_id)
    prescricao = internacao.prescricoes_medicas.filter_by(ativa=True).first()

    if request.method == "POST":
        disp = Dispensacao(
            numero=_gerar_numero_dispensacao(),
            paciente_id=internacao.paciente_id,
            prescricao_id=prescricao.id if prescricao else None,
            internacao_id=internacao.id,
            farmaceutico_id=current_user.id,
            status=StatusDispensacao.DISPENSADO,
            observacoes=request.form.get("observacoes") or None,
        )
        db.session.add(disp)
        db.session.flush()

        med_ids = request.form.getlist("med_id")
        quantidades = request.form.getlist("quantidade")
        item_presc_ids = request.form.getlist("item_prescricao_id")
        dispensou = 0
        for i, med_id in enumerate(med_ids):
            if not med_id:
                continue
            qtd = int(quantidades[i]) if i < len(quantidades) and quantidades[i] else 0
            if qtd <= 0:
                continue
            med = db.session.get(MedicamentoFarmacia, int(med_id))
            if not med:
                continue
            # Baixa do primeiro lote disponível (FEFO — first expired, first out)
            lote = next((l for l in med.lotes if l.quantidade > 0 and not l.vencido), None)
            item = ItemDispensacao(
                dispensacao_id=disp.id,
                medicamento_id=med.id,
                lote_id=lote.id if lote else None,
                quantidade=qtd,
                item_prescricao_id=int(item_presc_ids[i]) if i < len(item_presc_ids) and item_presc_ids[i] else None,
            )
            db.session.add(item)
            _registrar_movimento(med, TipoMovimentoEstoque.DISPENSACAO, -qtd,
                                 motivo=f"Dispensação {disp.numero}", lote=lote,
                                 dispensacao_id=disp.id)
            dispensou += 1

        db.session.commit()
        flash(f"Dispensação {disp.numero} registrada ({dispensou} itens).", "success")
        return redirect(url_for("farmacia.dispensar_lista"))

    medicamentos = MedicamentoFarmacia.query.filter_by(ativo=True).order_by(
        MedicamentoFarmacia.nome
    ).all()
    return render_template(
        "farmacia/dispensar.html",
        internacao=internacao, prescricao=prescricao, medicamentos=medicamentos,
    )
