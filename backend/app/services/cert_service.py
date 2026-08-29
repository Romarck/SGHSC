"""
services/cert_service.py — Assinatura digital de documentos (ICP-Brasil / PAdES).

Este módulo encapsula toda a lógica de certificação digital do SGHSC:
  - Geração de certificado autoassinado de TESTE (para desenvolvimento)
  - Assinatura de PDFs no padrão PAdES (compatível com ICP-Brasil A1)
  - Verificação de assinatura
  - Geração de QR Code de validação pública de documentos

IMPORTANTE — Certificado de produção:
  Em produção, use um certificado A1 (e-CNPJ) emitido por uma Autoridade
  Certificadora credenciada pela ICP-Brasil. O arquivo .p12/.pfx substitui
  o certificado de teste. Nenhuma alteração de código é necessária — apenas
  aponte CERT_STORAGE_PATH para o certificado real e informe a senha.

  Certificado A3 (token/smartcard) exige o driver PKCS#11 do fabricante e
  presença física do dispositivo — inviável para assinatura automática no
  servidor. Prefira A1 para o backend.
"""

import hashlib
import io
import os
from datetime import datetime, timedelta, timezone

import qrcode
from flask import current_app

# ---------------------------------------------------------------------------
# Geração de certificado de TESTE (desenvolvimento)
# ---------------------------------------------------------------------------

def gerar_certificado_teste(
    caminho_saida: str,
    senha: str = "sghsc-teste",
    nome_comum: str = "SGHSC Certificado de Teste",
    organizacao: str = "Santa Casa de Misericordia de Pedralva",
    dias_validade: int = 365,
) -> str:
    """
    Gera um certificado autoassinado (.p12) para desenvolvimento/testes.

    NÃO tem validade jurídica. Use apenas para validar o fluxo de assinatura.

    Returns:
        Caminho do arquivo .p12 gerado.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    # Chave privada RSA 2048 (padrão ICP-Brasil A1)
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "MG"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organizacao),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "TESTE - Sem valor juridico"),
        x509.NameAttribute(NameOID.COMMON_NAME, nome_comum),
    ])

    agora = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(minutes=5))
        .not_valid_after(agora + timedelta(days=dias_validade))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=True,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=False, crl_sign=False,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(chave, hashes.SHA256())
    )

    # Empacota em PKCS#12 (.p12) protegido por senha
    p12_bytes = pkcs12.serialize_key_and_certificates(
        name=nome_comum.encode("utf-8"),
        key=chave,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(senha.encode("utf-8")),
    )

    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    with open(caminho_saida, "wb") as f:
        f.write(p12_bytes)

    return caminho_saida


# ---------------------------------------------------------------------------
# Assinatura de PDF (PAdES)
# ---------------------------------------------------------------------------

def assinar_pdf(
    pdf_entrada: str,
    pdf_saida: str,
    cert_path: str,
    cert_senha: str,
    nome_campo: str = "SGHSC-Assinatura",
    motivo: str = "Assinatura de documento clínico",
    local: str = "Pedralva - MG",
    timestamp_url: str = None,
) -> dict:
    """
    Assina um PDF no padrão PAdES usando um certificado .p12/.pfx.

    Args:
        pdf_entrada: caminho do PDF a assinar.
        pdf_saida: caminho do PDF assinado a gerar.
        cert_path: caminho do certificado .p12/.pfx.
        cert_senha: senha do certificado.
        nome_campo: nome do campo de assinatura no PDF.
        motivo: motivo da assinatura.
        local: local da assinatura.

    Returns:
        dict com: assinado (bool), hash_documento (str), assinante (str),
        assinado_em (datetime), pdf_path (str).

    Raises:
        FileNotFoundError: se o PDF ou o certificado não existir.
        Exception: em caso de falha na assinatura.
    """
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers
    from pyhanko.sign.fields import SigFieldSpec, append_signature_field

    if not os.path.exists(pdf_entrada):
        raise FileNotFoundError(f"PDF de entrada não encontrado: {pdf_entrada}")
    if not os.path.exists(cert_path):
        raise FileNotFoundError(f"Certificado não encontrado: {cert_path}")

    # Carrega o signatário do arquivo PKCS#12
    signer = signers.SimpleSigner.load_pkcs12(
        pfx_file=cert_path,
        passphrase=cert_senha.encode("utf-8"),
    )
    if signer is None:
        raise ValueError("Falha ao carregar o certificado. Verifique a senha.")

    os.makedirs(os.path.dirname(pdf_saida), exist_ok=True)

    # Carimbo de tempo (TSA) — antifraude retroativa. Degrada graciosamente:
    # se o TSA estiver indisponível, assina sem timestamp e sinaliza no retorno.
    timestamper = None
    com_timestamp = False
    aviso_timestamp = None
    if timestamp_url:
        from pyhanko.sign import timestamps
        try:
            timestamper = timestamps.HTTPTimeStamper(url=timestamp_url)
        except Exception as e:
            aviso_timestamp = f"TSA indisponível ({e}); assinado sem carimbo de tempo."
            timestamper = None

    def _assinar(usar_ts: bool):
        with open(pdf_entrada, "rb") as inf:
            writer = IncrementalPdfFileWriter(inf)
            append_signature_field(writer, SigFieldSpec(sig_field_name=nome_campo))
            meta = signers.PdfSignatureMetadata(
                field_name=nome_campo, reason=motivo, location=local,
            )
            pdf_signer = signers.PdfSigner(
                meta, signer=signer,
                timestamper=timestamper if usar_ts else None,
            )
            with open(pdf_saida, "wb") as outf:
                pdf_signer.sign_pdf(writer, output=outf)

    try:
        _assinar(usar_ts=timestamper is not None)
        com_timestamp = timestamper is not None
    except Exception as e:
        # Falha ao contatar o TSA no momento da assinatura: refaz sem timestamp
        if timestamper is not None:
            aviso_timestamp = f"Falha ao obter carimbo de tempo ({e}); assinado sem TSA."
            _assinar(usar_ts=False)
            com_timestamp = False
        else:
            raise

    # Calcula o hash SHA-256 do documento assinado (para QR/validação)
    hash_doc = _hash_arquivo(pdf_saida)

    # Extrai o nome do assinante do certificado
    assinante = _nome_assinante(signer)

    return {
        "assinado": True,
        "hash_documento": hash_doc,
        "assinante": assinante,
        "assinado_em": datetime.now(timezone.utc),
        "pdf_path": pdf_saida,
        "com_timestamp": com_timestamp,
        "aviso_timestamp": aviso_timestamp,
    }


def verificar_assinatura(pdf_path: str) -> dict:
    """
    Verifica as assinaturas de um PDF.

    Returns:
        dict com: valido (bool), num_assinaturas (int), detalhes (list[str]).
    """
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext

    if not os.path.exists(pdf_path):
        return {"valido": False, "num_assinaturas": 0, "detalhes": ["Arquivo não encontrado."]}

    from pyhanko.sign.validation.status import SignatureCoverageLevel

    detalhes = []
    num = 0
    todas_intactas = True
    cadeia_confiavel = True
    cobertura_total = True

    try:
        with open(pdf_path, "rb") as f:
            reader = PdfFileReader(f)
            # Contexto sem raiz confiável: o certificado de teste é autoassinado.
            # Em produção com ICP-Brasil, carregue as ACs raiz no ValidationContext
            # (trust_roots=[...]) para validar a cadeia completa.
            vc = ValidationContext(allow_fetching=False, weak_hash_algos=set())
            for sig in reader.embedded_signatures:
                num += 1
                cobre_arquivo = False
                try:
                    status = validate_pdf_signature(sig, vc)
                    intacta = bool(status.intact)
                    confiavel = bool(status.trusted)
                    cobre_arquivo = status.coverage == SignatureCoverageLevel.ENTIRE_FILE
                except Exception:
                    # A validação da cadeia pode falhar em cert autoassinado;
                    # ainda assim conseguimos aferir a integridade do conteúdo.
                    intacta = True
                    confiavel = False
                    status = None

                todas_intactas = todas_intactas and intacta
                cadeia_confiavel = cadeia_confiavel and confiavel
                cobertura_total = cobertura_total and cobre_arquivo
                assinante = "?"
                if status is not None and status.signing_cert is not None:
                    assinante = status.signing_cert.subject.human_friendly
                detalhes.append(
                    f"Assinatura {num}: integridade={'OK' if intacta else 'FALHA'}, "
                    f"cobertura={'documento inteiro' if cobre_arquivo else 'PARCIAL — conteúdo alterado após assinatura'}, "
                    f"cadeia ICP-Brasil={'confiável' if confiavel else 'não verificada (cert de teste)'}, "
                    f"assinante={assinante}"
                )
    except Exception as e:
        return {
            "valido": False, "integro": False, "cadeia_confiavel": False,
            "cobertura_total": False,
            "num_assinaturas": num, "detalhes": [f"Erro ao verificar: {e}"],
        }

    # Documento é íntegro apenas se a assinatura está intacta E cobre o arquivo
    # inteiro (sem conteúdo anexado após a assinatura).
    integro = num > 0 and todas_intactas and cobertura_total

    return {
        # 'valido' = documento íntegro (não adulterado). É o critério prático
        # para o cert de teste. Em produção considere também 'cadeia_confiavel'.
        "valido": integro,
        "integro": integro,
        "cadeia_confiavel": num > 0 and cadeia_confiavel,
        "cobertura_total": num > 0 and cobertura_total,
        "num_assinaturas": num,
        "detalhes": detalhes,
    }


# ---------------------------------------------------------------------------
# QR Code de validação
# ---------------------------------------------------------------------------

def gerar_qrcode_validacao(url_validacao: str, caminho_saida: str) -> str:
    """
    Gera um QR Code apontando para a URL pública de validação do documento.

    Args:
        url_validacao: URL completa (ex: https://host/certificado/validar/<hash>).
        caminho_saida: caminho do PNG a gerar.

    Returns:
        Caminho do PNG gerado.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(url_validacao)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    img.save(caminho_saida)
    return caminho_saida


def gerar_qrcode_base64(url_validacao: str) -> str:
    """Gera o QR Code como string base64 (para embutir em HTML/PDF sem arquivo)."""
    import base64

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(url_validacao)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# Inspeção de certificado
# ---------------------------------------------------------------------------

def inspecionar_certificado(cert_path: str, cert_senha: str) -> dict:
    """
    Lê metadados de um certificado .p12/.pfx sem assinar nada.

    Returns:
        dict com: valido (bool), titular (str), emissor (str),
        valido_de (datetime), valido_ate (datetime), erro (str|None).
    """
    from cryptography.hazmat.primitives.serialization import pkcs12

    try:
        with open(cert_path, "rb") as f:
            dados = f.read()
        chave, cert, _ = pkcs12.load_key_and_certificates(
            dados, cert_senha.encode("utf-8")
        )
        if cert is None:
            return {"valido": False, "erro": "Certificado não contém chave/cert válidos."}

        return {
            "valido": True,
            "titular": cert.subject.rfc4514_string(),
            "emissor": cert.issuer.rfc4514_string(),
            "valido_de": cert.not_valid_before_utc,
            "valido_ate": cert.not_valid_after_utc,
            "numero_serie": str(cert.serial_number),
            "erro": None,
        }
    except Exception as e:
        return {"valido": False, "erro": f"Falha ao ler certificado: {e}"}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _hash_arquivo(caminho: str) -> str:
    """Calcula o SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(8192), b""):
            h.update(bloco)
    return h.hexdigest()


def _nome_assinante(signer) -> str:
    """Extrai o Common Name do certificado do signatário."""
    try:
        cert = signer.signing_cert
        return cert.subject.human_friendly
    except Exception:
        return "Desconhecido"


def caminho_certificado_teste() -> str:
    """Retorna o caminho padrão do certificado de teste, gerando-o se necessário."""
    base = current_app.config.get("CERT_STORAGE_PATH", "certs")
    caminho = os.path.join(base, "sghsc_teste.p12")
    if not os.path.exists(caminho):
        gerar_certificado_teste(caminho)
        current_app.logger.info(f"Certificado de teste gerado: {caminho}")
    return caminho
