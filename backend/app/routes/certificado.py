"""
routes/certificado.py — Certificação Digital (ICP-Brasil).

- Upload de certificado A1 (.p12/.pfx) do profissional
- Listagem de certificados e documentos assinados
- Validação pública de documento via código (QR Code) — SEM login
"""

import os
import secrets
from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db, limiter
from ..models.auditoria import AcaoAuditoria
from ..models.certificado import (
    CertificadoDigital,
    DocumentoAssinado,
    StatusDocumento,
    TipoCertificado,
)
from ..services import cert_service
from ..services.auditoria_service import registrar_acesso
from ..utils.authz import autorizar_recurso, requer_permissao

bp = Blueprint("certificado", __name__)


def _pasta_certs() -> str:
    pasta = current_app.config.get("CERT_STORAGE_PATH", "certs")
    os.makedirs(pasta, exist_ok=True)
    return pasta


# ---------------------------------------------------------------------------
# Painel / listagem
# ---------------------------------------------------------------------------

@bp.route("/")
@login_required
def painel():
    """Painel de certificação: certificado do usuário + documentos assinados."""
    certificados = CertificadoDigital.query.filter_by(
        usuario_id=current_user.id
    ).order_by(CertificadoDigital.criado_em.desc()).all()

    documentos = DocumentoAssinado.query.filter_by(
        assinante_id=current_user.id
    ).order_by(DocumentoAssinado.assinado_em.desc()).limit(50).all()

    return render_template(
        "certificado/painel.html",
        certificados=certificados,
        documentos=documentos,
    )


# ---------------------------------------------------------------------------
# Upload de certificado A1
# ---------------------------------------------------------------------------

@bp.route("/upload", methods=["GET", "POST"])
@login_required
@requer_permissao("certificado.usar")
def upload():
    """Upload de um certificado A1 (.p12/.pfx)."""
    if request.method == "POST":
        arquivo = request.files.get("certificado")
        senha = request.form.get("senha", "")

        if not arquivo or arquivo.filename == "":
            flash("Selecione um arquivo de certificado.", "warning")
            return redirect(url_for("certificado.upload"))

        ext = arquivo.filename.rsplit(".", 1)[-1].lower() if "." in arquivo.filename else ""
        if ext not in ("p12", "pfx"):
            flash("Formato inválido. Envie um arquivo .p12 ou .pfx.", "danger")
            return redirect(url_for("certificado.upload"))

        # Endurecimento de upload (S-09):
        # 1) salva em área TEMPORÁRIA (fora da pasta final de certificados);
        # 2) valida conteúdo/senha antes de persistir;
        # 3) só então move para o destino com nome TOTALMENTE GERADO (uuid),
        #    sem qualquer parte do nome original enviado pelo usuário.
        import tempfile
        import uuid

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=f".{ext}", prefix="cert_upload_")
        os.close(tmp_fd)
        arquivo.save(tmp_path)

        # Inspeciona metadados / valida a senha no arquivo temporário
        info = cert_service.inspecionar_certificado(tmp_path, senha)
        if not info["valido"]:
            os.remove(tmp_path)
            flash(f"Não foi possível validar o certificado: {info.get('erro')}", "danger")
            return redirect(url_for("certificado.upload"))

        # Nome final gerado (uuid) — não deriva do nome enviado pelo usuário
        import shutil
        nome_final = f"{uuid.uuid4().hex}.{ext}"
        caminho = os.path.join(_pasta_certs(), nome_final)
        shutil.move(tmp_path, caminho)  # move (lida com filesystems distintos)

        cert = CertificadoDigital(
            usuario_id=current_user.id,
            tipo=TipoCertificado.A1,
            titular=info.get("titular"),
            emissor=info.get("emissor"),
            numero_serie=info.get("numero_serie"),
            arquivo_path=caminho,
            valido_de=info.get("valido_de"),
            valido_ate=info.get("valido_ate"),
            ativo=True,
        )
        db.session.add(cert)

        # Atualiza os campos de conveniência no usuário
        current_user.cert_digital_path = caminho
        current_user.cert_validade = info.get("valido_ate")
        db.session.commit()

        flash("Certificado enviado e validado com sucesso.", "success")
        return redirect(url_for("certificado.painel"))

    return render_template("certificado/upload.html")


@bp.route("/gerar-teste", methods=["POST"])
@login_required
@requer_permissao("certificado.usar")
def gerar_teste():
    """Gera e vincula um certificado de TESTE ao usuário (desenvolvimento)."""
    if not current_app.debug:
        # Em produção, não permita certificado de teste
        abort(403)

    caminho = os.path.join(_pasta_certs(), f"teste_user{current_user.id}.p12")
    cert_service.gerar_certificado_teste(
        caminho, nome_comum=f"{current_user.nome} (TESTE)"
    )
    info = cert_service.inspecionar_certificado(caminho, "sghsc-teste")

    cert = CertificadoDigital(
        usuario_id=current_user.id,
        tipo=TipoCertificado.TESTE,
        titular=info.get("titular"),
        emissor=info.get("emissor"),
        numero_serie=info.get("numero_serie"),
        arquivo_path=caminho,
        valido_de=info.get("valido_de"),
        valido_ate=info.get("valido_ate"),
        ativo=True,
    )
    db.session.add(cert)
    current_user.cert_digital_path = caminho
    current_user.cert_validade = info.get("valido_ate")
    db.session.commit()

    flash("Certificado de TESTE gerado (senha: sghsc-teste). Sem valor jurídico.", "info")
    return redirect(url_for("certificado.painel"))


@bp.route("/<int:id>/desativar", methods=["POST"])
@login_required
def desativar(id: int):
    """Desativa um certificado."""
    cert = db.get_or_404(CertificadoDigital, id)
    # Só o dono do certificado (ou administrador) pode desativá-lo (S-02).
    autorizar_recurso(dono_id=cert.usuario_id)
    cert.ativo = False
    db.session.commit()
    flash("Certificado desativado.", "success")
    return redirect(url_for("certificado.painel"))


# ---------------------------------------------------------------------------
# Download de documento assinado
# ---------------------------------------------------------------------------

@bp.route("/documento/<int:id>/pdf")
@login_required
def baixar_documento(id: int):
    """Download do PDF de um documento assinado."""
    doc = db.get_or_404(DocumentoAssinado, id)
    # Autorização ao nível do objeto (S-02): o próprio assinante, ou quem tem
    # permissão de certificação. Verificada ANTES de checar a existência do
    # arquivo para não vazar a existência do documento a quem não pode vê-lo.
    autorizar_recurso(dono_id=doc.assinante_id, permissoes=("certificado.usar",))
    if not os.path.exists(doc.pdf_path):
        abort(404)

    # Trilha de auditoria LGPD: registra o download do documento assinado (S-07)
    registrar_acesso(
        AcaoAuditoria.BAIXAR_DOCUMENTO,
        paciente_id=doc.paciente_id,
        recurso="certificado.baixar_documento",
        recurso_id=doc.id,
        detalhe=f"{doc.tipo.value} — {doc.codigo_validacao}",
    )

    return send_file(
        doc.pdf_path, as_attachment=True,
        download_name=f"{doc.tipo.value}_{doc.codigo_validacao}.pdf"
    )


# ---------------------------------------------------------------------------
# Validação PÚBLICA (sem login) — destino do QR Code
# ---------------------------------------------------------------------------

@bp.route("/validar", methods=["GET"])
@bp.route("/validar/<codigo>", methods=["GET"])
@limiter.limit(lambda: current_app.config.get("RATELIMIT_VALIDACAO_PUBLICA", "30 per minute"))
def validar(codigo: str = None):
    """
    Página pública de validação de documento assinado.
    Acessível via QR Code impresso no documento.
    """
    documento = None
    verificacao = None

    if not codigo:
        codigo = request.args.get("codigo", "").strip()

    if codigo:
        documento = DocumentoAssinado.query.filter_by(codigo_validacao=codigo).first()
        if documento and os.path.exists(documento.pdf_path):
            verificacao = cert_service.verificar_assinatura(documento.pdf_path)

    return render_template(
        "certificado/validar.html",
        codigo=codigo,
        documento=documento,
        verificacao=verificacao,
    )


# ---------------------------------------------------------------------------
# Helper reutilizável: assina um PDF e registra o DocumentoAssinado
# ---------------------------------------------------------------------------

def assinar_documento(
    pdf_entrada: str,
    tipo,
    titulo: str,
    paciente_id: int = None,
    origem_tipo: str = None,
    origem_id: int = None,
    usuario=None,
) -> DocumentoAssinado:
    """
    Assina um PDF com o certificado do usuário e registra o DocumentoAssinado
    com QR Code de validação. Reutilizável por todos os módulos.

    Levanta ValueError se o usuário não tiver certificado vigente.
    """
    usuario = usuario or current_user

    cert = CertificadoDigital.query.filter_by(
        usuario_id=usuario.id, ativo=True
    ).order_by(CertificadoDigital.criado_em.desc()).first()
    if cert is None or not cert.vigente:
        raise ValueError("Usuário não possui certificado digital vigente.")

    # Senha: teste usa a padrão; produção deveria pedir a senha ao assinar
    senha = "sghsc-teste" if cert.tipo == TipoCertificado.TESTE else request.form.get("cert_senha", "")

    codigo = secrets.token_hex(8)  # 16 chars
    pasta_assinados = os.path.join(current_app.config.get("UPLOAD_FOLDER", "uploads"), "assinados")
    os.makedirs(pasta_assinados, exist_ok=True)
    pdf_saida = os.path.join(pasta_assinados, f"{codigo}.pdf")

    resultado = cert_service.assinar_pdf(
        pdf_entrada, pdf_saida, cert.arquivo_path, senha,
        motivo=f"Assinatura de {tipo.value}",
        timestamp_url=current_app.config.get("CERT_TIMESTAMP_URL"),
    )
    if resultado.get("aviso_timestamp"):
        current_app.logger.warning(resultado["aviso_timestamp"])

    # Gera QR apontando para a URL pública de validação
    url_validacao = url_for("certificado.validar", codigo=codigo, _external=True)
    qr_path = os.path.join(pasta_assinados, f"{codigo}_qr.png")
    try:
        cert_service.gerar_qrcode_validacao(url_validacao, qr_path)
    except Exception:
        qr_path = None

    doc = DocumentoAssinado(
        codigo_validacao=codigo,
        tipo=tipo,
        titulo=titulo,
        hash_documento=resultado["hash_documento"],
        pdf_path=pdf_saida,
        qrcode_path=qr_path,
        assinante_id=usuario.id,
        assinante_nome=resultado["assinante"],
        certificado_id=cert.id,
        paciente_id=paciente_id,
        origem_tipo=origem_tipo,
        origem_id=origem_id,
        status=StatusDocumento.ASSINADO,
        assinado_em=datetime.now(timezone.utc),
    )
    db.session.add(doc)
    db.session.commit()
    return doc
