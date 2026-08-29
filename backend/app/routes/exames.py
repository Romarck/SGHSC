"""
routes/exames.py — Módulo de Exames.

Fluxo: solicitar → fila de coleta → lançar resultado → visualizar.
"""

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.exame import (
    CategoriaExame,
    ExameCatalogo,
    ItemExame,
    OrigemExame,
    PrioridadeExame,
    ResultadoExame,
    SolicitacaoExame,
    StatusSolicitacaoExame,
)
from ..models.paciente import Paciente
from ..utils.authz import requer_permissao

bp = Blueprint("exames", __name__)


def _gerar_numero() -> str:
    agora = datetime.now()
    ultimo = db.session.query(db.func.max(SolicitacaoExame.id)).scalar() or 0
    return f"EX{agora.strftime('%Y%m%d')}{(ultimo + 1):04d}"


@bp.route("/")
@login_required
@requer_permissao("exames.ver")
def listar():
    """Lista de solicitações de exame, com filtro por status."""
    status = request.args.get("status")
    query = SolicitacaoExame.query
    if status:
        try:
            query = query.filter_by(status=StatusSolicitacaoExame[status])
        except KeyError:
            pass
    solicitacoes = query.order_by(SolicitacaoExame.solicitado_em.desc()).limit(100).all()
    return render_template(
        "exames/lista.html",
        solicitacoes=solicitacoes,
        status_atual=status,
        StatusSolicitacaoExame=StatusSolicitacaoExame,
    )


@bp.route("/fila-coleta")
@login_required
@requer_permissao("exames.ver")
def fila_coleta():
    """Fila de exames aguardando coleta/execução pelo laboratório."""
    pendentes = SolicitacaoExame.query.filter(
        SolicitacaoExame.status.in_([
            StatusSolicitacaoExame.SOLICITADO,
            StatusSolicitacaoExame.COLETADO,
            StatusSolicitacaoExame.EM_ANALISE,
        ])
    ).order_by(
        SolicitacaoExame.prioridade.desc(),
        SolicitacaoExame.solicitado_em
    ).all()
    return render_template("exames/fila.html", pendentes=pendentes)


@bp.route("/solicitar", methods=["GET", "POST"])
@login_required
@requer_permissao("exames.solicitar")
def solicitar():
    """Solicitação de exames por um médico."""
    paciente_id = request.args.get("paciente_id")
    paciente = Paciente.query.get(int(paciente_id)) if paciente_id else None

    if request.method == "POST":
        pac_id = request.form.get("paciente_id")
        if not pac_id:
            flash("Selecione um paciente.", "warning")
            return redirect(url_for("exames.solicitar"))

        solic = SolicitacaoExame(
            numero=_gerar_numero(),
            paciente_id=int(pac_id),
            solicitante_id=current_user.id,
            prioridade=PrioridadeExame[request.form.get("prioridade", "ROTINA")],
            indicacao_clinica=request.form.get("indicacao_clinica") or None,
            cid10=request.form.get("cid10") or None,
            observacoes=request.form.get("observacoes") or None,
            status=StatusSolicitacaoExame.SOLICITADO,
        )
        if request.form.get("internacao_id"):
            solic.internacao_id = int(request.form["internacao_id"])
            solic.origem = OrigemExame.INTERNACAO
        db.session.add(solic)
        db.session.flush()

        # Itens: nomes de exame digitados livremente ou do catálogo
        nomes = request.form.getlist("item_nome")
        cat_ids = request.form.getlist("item_catalogo_id")
        for i, nome in enumerate(nomes):
            if not nome.strip():
                continue
            cat_id = cat_ids[i] if i < len(cat_ids) and cat_ids[i] else None
            db.session.add(ItemExame(
                solicitacao_id=solic.id,
                exame_catalogo_id=int(cat_id) if cat_id else None,
                nome_exame=nome.strip(),
            ))
        db.session.commit()
        flash(f"Solicitação {solic.numero} registrada.", "success")
        return redirect(url_for("exames.detalhe", id=solic.id))

    catalogo = ExameCatalogo.query.filter_by(ativo=True).order_by(ExameCatalogo.nome).all()
    return render_template(
        "exames/solicitar.html",
        paciente=paciente, catalogo=catalogo,
        prioridades=PrioridadeExame,
    )


@bp.route("/<int:id>")
@login_required
@requer_permissao("exames.ver")
def detalhe(id: int):
    """Detalhe de uma solicitação com seus itens e resultados."""
    solic = db.get_or_404(SolicitacaoExame, id)
    return render_template("exames/detalhe.html", solic=solic,
                           StatusSolicitacaoExame=StatusSolicitacaoExame)


@bp.route("/<int:id>/coletar", methods=["POST"])
@login_required
@requer_permissao("exames.coletar")
def coletar(id: int):
    """Marca a solicitação como coletada."""
    solic = db.get_or_404(SolicitacaoExame, id)
    solic.status = StatusSolicitacaoExame.COLETADO
    solic.coletado_em = datetime.now(timezone.utc)
    solic.coletado_por_id = current_user.id
    db.session.commit()
    flash(f"Solicitação {solic.numero} marcada como coletada.", "success")
    return redirect(url_for("exames.fila_coleta"))


@bp.route("/<int:id>/resultado", methods=["GET", "POST"])
@login_required
@requer_permissao("exames.resultado")
def lancar_resultado(id: int):
    """Lança resultados para os itens de uma solicitação."""
    solic = db.get_or_404(SolicitacaoExame, id)

    # Travamento: não permite alterar resultado já assinado digitalmente
    if any(item.resultado and item.resultado.assinado for item in solic.itens):
        flash("Laudo já assinado digitalmente; não pode ser alterado.", "warning")
        return redirect(url_for("exames.detalhe", id=solic.id))

    if request.method == "POST":
        for item in solic.itens:
            valor = request.form.get(f"valor_{item.id}")
            laudo = request.form.get(f"laudo_{item.id}")
            if not valor and not laudo:
                continue
            if item.resultado:
                res = item.resultado
            else:
                res = ResultadoExame(item_id=item.id)
                db.session.add(res)
            res.valor = valor or None
            res.unidade = request.form.get(f"unidade_{item.id}") or None
            res.valor_referencia = request.form.get(f"ref_{item.id}") or None
            res.laudo = laudo or None
            res.alterado = bool(request.form.get(f"alterado_{item.id}"))
            res.responsavel_id = current_user.id
            res.liberado_em = datetime.now(timezone.utc)

        solic.status = StatusSolicitacaoExame.RESULTADO_DISPONIVEL
        db.session.commit()
        flash("Resultados lançados.", "success")
        return redirect(url_for("exames.detalhe", id=solic.id))

    return render_template("exames/resultado.html", solic=solic)


# ---------------------------------------------------------------------------
# Catálogo de exames
# ---------------------------------------------------------------------------

@bp.route("/catalogo", methods=["GET", "POST"])
@login_required
@requer_permissao("exames.ver")
def catalogo():
    """Cadastro/listagem do catálogo de exames."""
    if request.method == "POST":
        exame = ExameCatalogo(
            codigo=request.form.get("codigo", "").strip(),
            nome=request.form.get("nome", "").strip(),
            categoria=CategoriaExame[request.form.get("categoria", "LABORATORIAL")],
            material=request.form.get("material") or None,
            unidade_medida=request.form.get("unidade_medida") or None,
            valor_referencia=request.form.get("valor_referencia") or None,
        )
        db.session.add(exame)
        db.session.commit()
        flash(f"Exame '{exame.nome}' adicionado ao catálogo.", "success")
        return redirect(url_for("exames.catalogo"))

    itens = ExameCatalogo.query.order_by(ExameCatalogo.nome).all()
    return render_template("exames/catalogo.html", itens=itens, categorias=CategoriaExame)


# ---------------------------------------------------------------------------
# Assinatura digital do laudo
# ---------------------------------------------------------------------------

@bp.route("/<int:id>/assinar", methods=["POST"])
@login_required
@requer_permissao("certificado.usar")
def assinar_laudo(id: int):
    """Gera o PDF do laudo consolidado, assina digitalmente e sela os resultados."""
    from ..models.certificado import TipoDocumentoAssinado
    from ..routes.certificado import assinar_documento
    from ..services.pdf_service import gerar_pdf_laudo_exame

    solic = db.get_or_404(SolicitacaoExame, id)

    if not any(item.resultado for item in solic.itens):
        flash("Não há resultados lançados para assinar.", "warning")
        return redirect(url_for("exames.detalhe", id=solic.id))

    if any(item.resultado and item.resultado.assinado for item in solic.itens):
        flash("Este laudo já está assinado.", "info")
        return redirect(url_for("exames.detalhe", id=solic.id))

    try:
        pdf_path = gerar_pdf_laudo_exame(solic)
        doc = assinar_documento(
            pdf_path,
            TipoDocumentoAssinado.LAUDO_EXAME,
            f"Laudo de exame {solic.numero}",
            paciente_id=solic.paciente_id,
            origem_tipo="solicitacao_exame",
            origem_id=solic.id,
        )
    except ValueError as e:
        flash(str(e) + " Cadastre um certificado em Certificação Digital.", "warning")
        return redirect(url_for("exames.detalhe", id=solic.id))
    except Exception as e:
        flash(f"Erro ao assinar: {e}", "danger")
        return redirect(url_for("exames.detalhe", id=solic.id))

    # Sela todos os resultados da solicitação
    for item in solic.itens:
        if item.resultado:
            item.resultado.assinado = True
            item.resultado.documento_assinado_id = doc.id
    db.session.commit()

    flash(f"Laudo {solic.numero} assinado digitalmente. "
          f"Código de validação: {doc.codigo_validacao}.", "success")
    return redirect(url_for("exames.detalhe", id=solic.id))
