"""
routes/ccih.py — Comissão de Controle de Infecção Hospitalar.

Notificações de infecção, painel de isolamentos, relatório de vigilância.
"""

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.ccih import (
    IsolamentoPaciente,
    NotificacaoInfeccao,
    StatusIsolamento,
    StatusNotificacao,
    TipoInfeccao,
    TipoPrecaucao,
)
from ..models.internacao import Internacao
from ..models.paciente import Paciente
from ..utils.authz import requer_permissao

bp = Blueprint("ccih", __name__)


def _gerar_numero() -> str:
    agora = datetime.now()
    ultimo = db.session.query(db.func.max(NotificacaoInfeccao.id)).scalar() or 0
    return f"CCIH{agora.strftime('%Y%m%d')}{(ultimo + 1):04d}"


@bp.route("/")
def _root():
    return redirect(url_for("ccih.painel"))


@bp.route("/painel")
@login_required
@requer_permissao("ccih.ver")
def painel():
    """Painel CCIH: notificações abertas + isolamentos ativos."""
    notificacoes = NotificacaoInfeccao.query.filter(
        NotificacaoInfeccao.status.in_([
            StatusNotificacao.ABERTA, StatusNotificacao.EM_INVESTIGACAO,
            StatusNotificacao.CONFIRMADA,
        ])
    ).order_by(NotificacaoInfeccao.data_notificacao.desc()).all()

    isolamentos = IsolamentoPaciente.query.filter_by(
        status=StatusIsolamento.ATIVO
    ).order_by(IsolamentoPaciente.iniciado_em.desc()).all()

    return render_template(
        "ccih/painel.html",
        notificacoes=notificacoes, isolamentos=isolamentos,
    )


@bp.route("/notificar", methods=["GET", "POST"])
@login_required
@requer_permissao("ccih.gerir")
def notificar():
    """Registra uma notificação de infecção."""
    paciente_id = request.args.get("paciente_id")
    paciente = Paciente.query.get(int(paciente_id)) if paciente_id else None

    if request.method == "POST":
        notif = NotificacaoInfeccao(
            numero=_gerar_numero(),
            paciente_id=int(request.form["paciente_id"]),
            internacao_id=int(request.form["internacao_id"]) if request.form.get("internacao_id") else None,
            notificante_id=current_user.id,
            tipo=TipoInfeccao[request.form["tipo"]],
            topografia=request.form.get("topografia") or None,
            microrganismo=request.form.get("microrganismo") or None,
            antibiograma=request.form.get("antibiograma") or None,
            cid10=request.form.get("cid10") or None,
            descricao=request.form.get("descricao") or None,
            status=StatusNotificacao.ABERTA,
        )
        db.session.add(notif)
        db.session.commit()
        flash(f"Notificação {notif.numero} registrada.", "success")
        return redirect(url_for("ccih.painel"))

    return render_template("ccih/notificar.html", paciente=paciente, tipos=TipoInfeccao)


@bp.route("/notificacao/<int:id>", methods=["GET", "POST"])
@login_required
@requer_permissao("ccih.gerir")
def detalhe_notificacao(id: int):
    """Detalhe e atualização de status de uma notificação."""
    notif = db.get_or_404(NotificacaoInfeccao, id)
    if request.method == "POST":
        notif.status = StatusNotificacao[request.form["status"]]
        notif.conduta = request.form.get("conduta") or notif.conduta
        if notif.status in (StatusNotificacao.ENCERRADA, StatusNotificacao.DESCARTADA):
            notif.data_encerramento = datetime.now(timezone.utc)
        db.session.commit()
        flash("Notificação atualizada.", "success")
        return redirect(url_for("ccih.detalhe_notificacao", id=notif.id))
    return render_template("ccih/detalhe_notificacao.html", notif=notif,
                           status_opcoes=StatusNotificacao)


@bp.route("/isolar/<int:internacao_id>", methods=["GET", "POST"])
@login_required
@requer_permissao("ccih.gerir")
def isolar(internacao_id: int):
    """Inicia precaução/isolamento para uma internação e marca o leito."""
    internacao = db.get_or_404(Internacao, internacao_id)
    if request.method == "POST":
        iso = IsolamentoPaciente(
            internacao_id=internacao.id,
            tipo_precaucao=TipoPrecaucao[request.form["tipo_precaucao"]],
            motivo=request.form.get("motivo") or None,
            microrganismo=request.form.get("microrganismo") or None,
            prescrito_por_id=current_user.id,
            status=StatusIsolamento.ATIVO,
        )
        db.session.add(iso)
        # Marca o leito como isolamento (CCIH)
        if internacao.leito:
            internacao.leito.isolamento = True
        db.session.commit()
        flash("Isolamento iniciado.", "success")
        return redirect(url_for("ccih.painel"))
    return render_template("ccih/isolar.html", internacao=internacao,
                           precaucoes=TipoPrecaucao)


@bp.route("/isolamento/<int:id>/encerrar", methods=["POST"])
@login_required
@requer_permissao("ccih.gerir")
def encerrar_isolamento(id: int):
    """Encerra um isolamento e libera a marcação do leito."""
    iso = db.get_or_404(IsolamentoPaciente, id)
    iso.status = StatusIsolamento.ENCERRADO
    iso.encerrado_em = datetime.now(timezone.utc)
    # Se não houver outro isolamento ativo no mesmo leito, remove a marcação
    if iso.internacao and iso.internacao.leito:
        outros = IsolamentoPaciente.query.filter_by(
            internacao_id=iso.internacao_id, status=StatusIsolamento.ATIVO
        ).filter(IsolamentoPaciente.id != iso.id).count()
        if outros == 0:
            iso.internacao.leito.isolamento = False
    db.session.commit()
    flash("Isolamento encerrado.", "success")
    return redirect(url_for("ccih.painel"))


@bp.route("/relatorio")
@login_required
@requer_permissao("ccih.ver")
def relatorio():
    """Relatório simples de vigilância (base para SCIRAS)."""
    total_notif = NotificacaoInfeccao.query.count()
    confirmadas = NotificacaoInfeccao.query.filter_by(
        status=StatusNotificacao.CONFIRMADA
    ).count()
    iso_ativos = IsolamentoPaciente.query.filter_by(
        status=StatusIsolamento.ATIVO
    ).count()

    # Contagem por tipo de infecção
    por_tipo = {}
    for tipo in TipoInfeccao:
        c = NotificacaoInfeccao.query.filter_by(tipo=tipo).count()
        if c:
            por_tipo[tipo.value] = c

    return render_template(
        "ccih/relatorio.html",
        total_notif=total_notif, confirmadas=confirmadas,
        iso_ativos=iso_ativos, por_tipo=por_tipo,
    )
