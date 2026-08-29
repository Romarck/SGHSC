"""
routes/cirurgias.py — Módulo de Centro Cirúrgico.

Solicitação, escala/agenda, mapa cirúrgico (fluxo de sala) e descrição.
"""

from datetime import date, datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.cirurgia import (
    Cirurgia,
    PorteCirurgico,
    SalaCirurgica,
    StatusCirurgia,
    TipoAnestesia,
    TipoCirurgia,
)
from ..models.paciente import Paciente
from ..models.usuario import TipoPerfil, Usuario
from ..utils.authz import requer_permissao

bp = Blueprint("cirurgias", __name__)


def _gerar_numero() -> str:
    agora = datetime.now()
    ultimo = db.session.query(db.func.max(Cirurgia.id)).scalar() or 0
    return f"CIR{agora.strftime('%Y%m%d')}{(ultimo + 1):04d}"


def _medicos():
    return Usuario.query.filter(
        Usuario.perfil.has(tipo=TipoPerfil.MEDICO)
    ).order_by(Usuario.nome).all()


@bp.route("/")
@login_required
@requer_permissao("cirurgias.ver")
def escala():
    """Escala de cirurgias — lista por data (padrão: hoje em diante)."""
    cirurgias = Cirurgia.query.filter(
        Cirurgia.status.notin_([StatusCirurgia.CONCLUIDA, StatusCirurgia.CANCELADA])
    ).order_by(Cirurgia.data_agendada.is_(None), Cirurgia.data_agendada).all()
    return render_template("cirurgias/escala.html", cirurgias=cirurgias)


@bp.route("/mapa")
@login_required
@requer_permissao("cirurgias.ver")
def mapa():
    """Mapa cirúrgico do dia por sala (fluxo de pacientes)."""
    hoje = date.today()
    salas = SalaCirurgica.query.filter_by(ativa=True).order_by(SalaCirurgica.nome).all()
    # Cirurgias agendadas para hoje, agrupadas por sala
    por_sala: dict = {s.id: [] for s in salas}
    sem_sala = []
    cirurgias_hoje = Cirurgia.query.filter(
        db.func.date(Cirurgia.data_agendada) == hoje
    ).order_by(Cirurgia.data_agendada).all()
    for cir in cirurgias_hoje:
        if cir.sala_id and cir.sala_id in por_sala:
            por_sala[cir.sala_id].append(cir)
        else:
            sem_sala.append(cir)
    return render_template("cirurgias/mapa.html", salas=salas, por_sala=por_sala,
                           sem_sala=sem_sala, hoje=hoje)


@bp.route("/solicitar", methods=["GET", "POST"])
@login_required
@requer_permissao("cirurgias.gerir")
def solicitar():
    """Solicitação de cirurgia."""
    paciente_id = request.args.get("paciente_id")
    paciente = Paciente.query.get(int(paciente_id)) if paciente_id else None

    if request.method == "POST":
        cir = Cirurgia(
            numero=_gerar_numero(),
            paciente_id=int(request.form["paciente_id"]),
            cirurgiao_id=int(request.form["cirurgiao_id"]),
            solicitante_id=current_user.id,
            procedimento=request.form["procedimento"].strip(),
            codigo_procedimento=request.form.get("codigo_procedimento") or None,
            tipo=TipoCirurgia[request.form.get("tipo", "ELETIVA")],
            porte=PorteCirurgico[request.form["porte"]] if request.form.get("porte") else None,
            tipo_anestesia=TipoAnestesia[request.form["tipo_anestesia"]] if request.form.get("tipo_anestesia") else None,
            cid10=request.form.get("cid10") or None,
            indicacao=request.form.get("indicacao") or None,
            lateralidade=request.form.get("lateralidade") or None,
            status=StatusCirurgia.SOLICITADA,
        )
        if request.form.get("internacao_id"):
            cir.internacao_id = int(request.form["internacao_id"])
        db.session.add(cir)
        db.session.commit()
        flash(f"Cirurgia {cir.numero} solicitada.", "success")
        return redirect(url_for("cirurgias.detalhe", id=cir.id))

    return render_template(
        "cirurgias/solicitar.html",
        paciente=paciente, medicos=_medicos(),
        tipos=TipoCirurgia, portes=PorteCirurgico, anestesias=TipoAnestesia,
    )


@bp.route("/<int:id>")
@login_required
@requer_permissao("cirurgias.ver")
def detalhe(id: int):
    cir = db.get_or_404(Cirurgia, id)
    return render_template("cirurgias/detalhe.html", cir=cir,
                           StatusCirurgia=StatusCirurgia)


@bp.route("/<int:id>/agendar", methods=["GET", "POST"])
@login_required
@requer_permissao("cirurgias.gerir")
def agendar(id: int):
    """Agenda a cirurgia em uma sala/data."""
    cir = db.get_or_404(Cirurgia, id)
    if request.method == "POST":
        data_str = request.form.get("data_agendada")
        if data_str:
            cir.data_agendada = datetime.fromisoformat(data_str)
        cir.sala_id = int(request.form["sala_id"]) if request.form.get("sala_id") else None
        cir.duracao_estimada_min = int(request.form["duracao"]) if request.form.get("duracao") else None
        cir.anestesista_id = int(request.form["anestesista_id"]) if request.form.get("anestesista_id") else None
        cir.status = StatusCirurgia.AGENDADA
        db.session.commit()
        flash(f"Cirurgia {cir.numero} agendada.", "success")
        return redirect(url_for("cirurgias.detalhe", id=cir.id))

    salas = SalaCirurgica.query.filter_by(ativa=True).order_by(SalaCirurgica.nome).all()
    return render_template("cirurgias/agendar.html", cir=cir, salas=salas,
                           medicos=_medicos())


@bp.route("/<int:id>/status", methods=["POST"])
@login_required
@requer_permissao("cirurgias.gerir")
def mudar_status(id: int):
    """Avança o status da cirurgia (fluxo de sala) e carimba os tempos."""
    cir = db.get_or_404(Cirurgia, id)
    novo = StatusCirurgia[request.form["status"]]
    agora = datetime.now(timezone.utc)
    cir.status = novo
    if novo == StatusCirurgia.EM_PREPARO and not cir.entrada_sala_em:
        cir.entrada_sala_em = agora
    elif novo == StatusCirurgia.EM_ANDAMENTO and not cir.inicio_cirurgia_em:
        cir.inicio_cirurgia_em = agora
    elif novo == StatusCirurgia.RECUPERACAO and not cir.fim_cirurgia_em:
        cir.fim_cirurgia_em = agora
    elif novo == StatusCirurgia.CONCLUIDA and not cir.saida_sala_em:
        cir.saida_sala_em = agora
    db.session.commit()
    flash(f"Status atualizado para '{novo.value}'.", "success")
    return redirect(url_for("cirurgias.detalhe", id=cir.id))


@bp.route("/<int:id>/descricao", methods=["GET", "POST"])
@login_required
@requer_permissao("cirurgias.gerir")
def descricao(id: int):
    """Registro da descrição cirúrgica (nota de sala)."""
    cir = db.get_or_404(Cirurgia, id)
    if cir.descricao_assinada:
        flash("Descrição cirúrgica já assinada; não pode ser alterada.", "warning")
        return redirect(url_for("cirurgias.detalhe", id=cir.id))
    if request.method == "POST":
        cir.descricao_cirurgica = request.form.get("descricao_cirurgica") or None
        cir.achados = request.form.get("achados") or None
        cir.procedimento_realizado = request.form.get("procedimento_realizado") or None
        cir.intercorrencias = request.form.get("intercorrencias") or None
        cir.equipe = request.form.get("equipe") or None
        cir.material_utilizado = request.form.get("material_utilizado") or None
        db.session.commit()
        flash("Descrição cirúrgica salva.", "success")
        return redirect(url_for("cirurgias.detalhe", id=cir.id))
    return render_template("cirurgias/descricao.html", cir=cir)


@bp.route("/salas", methods=["GET", "POST"])
@login_required
@requer_permissao("cirurgias.gerir")
def salas():
    """Cadastro/listagem de salas cirúrgicas."""
    if request.method == "POST":
        sala = SalaCirurgica(
            nome=request.form["nome"].strip(),
            descricao=request.form.get("descricao") or None,
        )
        db.session.add(sala)
        db.session.commit()
        flash(f"Sala '{sala.nome}' cadastrada.", "success")
        return redirect(url_for("cirurgias.salas"))
    lista = SalaCirurgica.query.order_by(SalaCirurgica.nome).all()
    return render_template("cirurgias/salas.html", salas=lista)


@bp.route("/<int:id>/assinar-descricao", methods=["POST"])
@login_required
@requer_permissao("certificado.usar")
def assinar_descricao(id: int):
    """Gera o PDF da descrição cirúrgica, assina digitalmente e sela."""
    from ..models.certificado import TipoDocumentoAssinado
    from ..routes.certificado import assinar_documento
    from ..services.pdf_service import gerar_pdf_descricao_cirurgica

    cir = db.get_or_404(Cirurgia, id)

    if cir.descricao_assinada:
        flash("A descrição cirúrgica já está assinada.", "info")
        return redirect(url_for("cirurgias.detalhe", id=cir.id))

    if not cir.descricao_cirurgica and not cir.procedimento_realizado:
        flash("Preencha a descrição cirúrgica antes de assinar.", "warning")
        return redirect(url_for("cirurgias.descricao", id=cir.id))

    try:
        pdf_path = gerar_pdf_descricao_cirurgica(cir)
        doc = assinar_documento(
            pdf_path,
            TipoDocumentoAssinado.DESCRICAO_CIRURGICA,
            f"Descrição cirúrgica {cir.numero}",
            paciente_id=cir.paciente_id,
            origem_tipo="cirurgia",
            origem_id=cir.id,
        )
    except ValueError as e:
        flash(str(e) + " Cadastre um certificado em Certificação Digital.", "warning")
        return redirect(url_for("cirurgias.detalhe", id=cir.id))
    except Exception as e:
        flash(f"Erro ao assinar: {e}", "danger")
        return redirect(url_for("cirurgias.detalhe", id=cir.id))

    cir.descricao_assinada = True
    cir.documento_assinado_id = doc.id
    db.session.commit()

    flash(f"Descrição cirúrgica {cir.numero} assinada. Código: {doc.codigo_validacao}.", "success")
    return redirect(url_for("cirurgias.detalhe", id=cir.id))
