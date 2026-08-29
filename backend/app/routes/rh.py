"""routes/rh.py — Recursos Humanos."""

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.rh import (
    EscalaPlantao,
    Funcionario,
    Setor,
    StatusFuncionario,
    TipoVinculo,
    TurnoPlantao,
)
from ..utils.authz import requer_permissao

bp = Blueprint("rh", __name__)


@bp.route("/")
@bp.route("/funcionarios")
@login_required
@requer_permissao("rh.ver")
def funcionarios():
    busca = request.args.get("q", "").strip()
    query = Funcionario.query
    if busca:
        like = f"%{busca}%"
        query = query.filter(db.or_(
            Funcionario.nome.ilike(like), Funcionario.matricula.ilike(like)))
    lista = query.order_by(Funcionario.nome).all()
    return render_template("rh/funcionarios.html", funcionarios=lista, busca=busca)


@bp.route("/funcionarios/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("rh.gerir")
def novo_funcionario():
    setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()
    if request.method == "POST":
        f = Funcionario(
            matricula=request.form["matricula"].strip(),
            nome=request.form["nome"].strip(),
            cpf=request.form.get("cpf") or None,
            cargo=request.form.get("cargo") or None,
            setor_id=int(request.form["setor_id"]) if request.form.get("setor_id") else None,
            vinculo=TipoVinculo[request.form["vinculo"]] if request.form.get("vinculo") else None,
            status=StatusFuncionario[request.form.get("status", "ATIVO")],
            conselho_tipo=request.form.get("conselho_tipo") or None,
            conselho_numero=request.form.get("conselho_numero") or None,
            telefone=request.form.get("telefone") or None,
            email=request.form.get("email") or None,
            data_admissao=date.fromisoformat(request.form["data_admissao"]) if request.form.get("data_admissao") else None,
        )
        db.session.add(f)
        db.session.commit()
        flash(f"Funcionário {f.nome} cadastrado.", "success")
        return redirect(url_for("rh.funcionarios"))
    return render_template("rh/form_funcionario.html", setores=setores,
                           vinculos=TipoVinculo, status_opcoes=StatusFuncionario)


@bp.route("/setores", methods=["GET", "POST"])
@login_required
@requer_permissao("rh.gerir")
def setores():
    if request.method == "POST":
        db.session.add(Setor(nome=request.form["nome"].strip()))
        db.session.commit()
        flash("Setor cadastrado.", "success")
        return redirect(url_for("rh.setores"))
    lista = Setor.query.order_by(Setor.nome).all()
    return render_template("rh/setores.html", setores=lista)


@bp.route("/escalas", methods=["GET", "POST"])
@login_required
@requer_permissao("rh.gerir")
def escalas():
    funcionarios = Funcionario.query.filter_by(status=StatusFuncionario.ATIVO).order_by(Funcionario.nome).all()
    setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()
    if request.method == "POST":
        db.session.add(EscalaPlantao(
            funcionario_id=int(request.form["funcionario_id"]),
            setor_id=int(request.form["setor_id"]) if request.form.get("setor_id") else None,
            data=date.fromisoformat(request.form["data"]),
            turno=TurnoPlantao[request.form["turno"]],
            observacoes=request.form.get("observacoes") or None,
            criado_por_id=current_user.id,
        ))
        db.session.commit()
        flash("Escala registrada.", "success")
        return redirect(url_for("rh.escalas"))
    escalas = EscalaPlantao.query.order_by(EscalaPlantao.data.desc()).limit(100).all()
    return render_template("rh/escalas.html", escalas=escalas, funcionarios=funcionarios,
                           setores=setores, turnos=TurnoPlantao)
