"""
services/pdf_service.py — Geração de documentos PDF com ReportLab.

Documentos suportados:
  - Laudo de alta hospitalar (gerar_laudo_alta)
  - Prescrição médica (gerar_pdf_prescricao)
  - Evolução médica (gerar_pdf_evolucao_medica)
  - Laudo de exame (gerar_pdf_laudo_exame)

Os três últimos são destinados à assinatura digital (ver services/cert_service.py).

Padrão de nomenclatura dos arquivos gerados:
  uploads/laudos/laudo_alta_<numero_internacao>.pdf
  uploads/prescricoes/, uploads/evolucoes/, uploads/laudos_exame/
"""

import os
from datetime import datetime, timezone

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Helpers de estilo
# ---------------------------------------------------------------------------

def _build_styles():
    """Retorna dicionário com os estilos personalizados do SGHSC."""
    base = getSampleStyleSheet()

    estilos = {
        "titulo": ParagraphStyle(
            "titulo",
            parent=base["Heading1"],
            fontSize=14,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo",
            parent=base["Normal"],
            fontSize=10,
            fontName="Helvetica",
            alignment=TA_CENTER,
            spaceAfter=2,
            textColor=colors.HexColor("#555555"),
        ),
        "secao": ParagraphStyle(
            "secao",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1a1a1a"),
            spaceBefore=8,
            spaceAfter=3,
            borderPad=2,
        ),
        "campo_label": ParagraphStyle(
            "campo_label",
            parent=base["Normal"],
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#444444"),
            spaceAfter=1,
        ),
        "campo_valor": ParagraphStyle(
            "campo_valor",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            spaceAfter=4,
        ),
        "corpo": ParagraphStyle(
            "corpo",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            alignment=TA_JUSTIFY,
            leading=14,
            spaceAfter=6,
        ),
        "rodape": ParagraphStyle(
            "rodape",
            parent=base["Normal"],
            fontSize=7,
            fontName="Helvetica",
            textColor=colors.HexColor("#888888"),
            alignment=TA_CENTER,
        ),
        "assinatura": ParagraphStyle(
            "assinatura",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
    }
    return estilos


def _cabecalho_instituicao(estilos: dict) -> list:
    """Retorna os elementos do cabeçalho padrão da instituição."""
    nome = current_app.config.get("INSTITUICAO_NOME", "Santa Casa")
    cnes = current_app.config.get("INSTITUICAO_CNES", "")
    cnpj = current_app.config.get("INSTITUICAO_CNPJ", "")
    cidade = current_app.config.get("INSTITUICAO_CIDADE", "")
    uf = current_app.config.get("INSTITUICAO_UF", "")

    elementos = [
        Paragraph(nome.upper(), estilos["titulo"]),
    ]

    info_lines = []
    if cnes:
        info_lines.append(f"CNES: {cnes}")
    if cnpj:
        info_lines.append(f"CNPJ: {cnpj}")
    if cidade:
        info_lines.append(f"{cidade} — {uf}")

    if info_lines:
        elementos.append(
            Paragraph(" &nbsp;|&nbsp; ".join(info_lines), estilos["subtitulo"])
        )

    elementos.append(HRFlowable(width="100%", thickness=1.5,
                                color=colors.HexColor("#1a5276"), spaceAfter=6))
    return elementos


def _par_campo(label: str, valor: str, estilos: dict) -> list:
    """Retorna [label, valor] como parágrafos formatados."""
    return [
        Paragraph(label, estilos["campo_label"]),
        Paragraph(str(valor) if valor else "—", estilos["campo_valor"]),
    ]


def _tabela_dados(dados: list[tuple[str, str]], estilos: dict,
                  colunas: int = 2) -> Table:
    """
    Cria uma tabela de dados (label/valor) com N colunas por linha.
    dados: lista de (label, valor)
    colunas: quantos pares por linha
    """
    # Agrupa em linhas de N pares
    linhas = []
    for i in range(0, len(dados), colunas):
        grupo = dados[i:i + colunas]
        # Preenche se necessário
        while len(grupo) < colunas:
            grupo.append(("", ""))
        linha_labels = []
        linha_valores = []
        for label, valor in grupo:
            linha_labels.append(
                Paragraph(label, estilos["campo_label"]) if label else ""
            )
            linha_valores.append(
                Paragraph(str(valor) if valor else "—", estilos["campo_valor"])
                if label else ""
            )
        linhas.append(linha_labels)
        linhas.append(linha_valores)

    col_width = (A4[0] - 3 * cm) / colunas
    tabela = Table(linhas, colWidths=[col_width] * colunas)
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
    ]))
    return tabela


# ---------------------------------------------------------------------------
# Laudo de Alta Hospitalar
# ---------------------------------------------------------------------------

def gerar_laudo_alta(internacao) -> str:
    """
    Gera o laudo de alta hospitalar em PDF usando ReportLab.

    Args:
        internacao: instância do model Internacao (com relações carregadas).

    Returns:
        Caminho absoluto do PDF gerado.

    Raises:
        Exception: se houver erro na geração do PDF.
    """
    # Diretório de saída
    pasta = os.path.join(
        current_app.config.get("UPLOAD_FOLDER", "uploads"),
        "laudos"
    )
    os.makedirs(pasta, exist_ok=True)

    nome_arquivo = f"laudo_alta_{internacao.numero}.pdf"
    caminho = os.path.join(pasta, nome_arquivo)

    estilos = _build_styles()

    doc = SimpleDocTemplate(
        caminho,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        title=f"Laudo de Alta — {internacao.numero}",
        author=current_app.config.get("INSTITUICAO_NOME", "SGHSC"),
    )

    story = []

    # ---- Cabeçalho ----
    story.extend(_cabecalho_instituicao(estilos))
    story.append(
        Paragraph("LAUDO DE ALTA HOSPITALAR", ParagraphStyle(
            "doc_titulo",
            fontSize=12,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceAfter=4,
            textColor=colors.HexColor("#1a5276"),
        ))
    )
    story.append(
        Paragraph(f"Internação Nº: <b>{internacao.numero}</b>", ParagraphStyle(
            "doc_num",
            fontSize=10,
            fontName="Helvetica",
            alignment=TA_CENTER,
            spaceAfter=8,
            textColor=colors.HexColor("#555555"),
        ))
    )
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#aaaaaa"), spaceAfter=8))

    # ---- Identificação do paciente ----
    story.append(Paragraph("IDENTIFICAÇÃO DO PACIENTE", estilos["secao"]))

    paciente = internacao.paciente
    dados_paciente = [
        ("Nome completo", paciente.nome),
        ("Data de nascimento",
         paciente.data_nascimento.strftime("%d/%m/%Y") if paciente.data_nascimento else ""),
        ("Idade", f"{paciente.idade} anos"),
        ("Sexo", paciente.sexo.value if paciente.sexo else ""),
        ("CPF", paciente.cpf or ""),
        ("CNS", paciente.cns or ""),
        ("Prontuário",
         paciente.prontuario.numero if paciente.prontuario else ""),
        ("Convênio", internacao.convenio or "SUS"),
    ]
    story.append(_tabela_dados(dados_paciente, estilos, colunas=2))

    # ---- Dados da internação ----
    story.append(Paragraph("DADOS DA INTERNAÇÃO", estilos["secao"]))

    dados_internacao = [
        ("Tipo de internação", internacao.tipo.value),
        ("Médico responsável", internacao.medico_responsavel.nome),
        ("Leito", f"{internacao.leito.numero} — {internacao.leito.tipo.value}"),
        ("Ala / Setor", internacao.leito.ala or ""),
        ("Data/hora de admissão",
         internacao.admissao_em.strftime("%d/%m/%Y às %H:%M")),
        ("Data/hora de alta",
         internacao.alta_em.strftime("%d/%m/%Y às %H:%M") if internacao.alta_em else ""),
        ("Dias internado", f"{internacao.dias_internado} dias"),
        ("Nº da AIH", internacao.numero_aih or "Não informado"),
    ]
    story.append(_tabela_dados(dados_internacao, estilos, colunas=2))

    # ---- Diagnóstico ----
    story.append(Paragraph("DIAGNÓSTICO", estilos["secao"]))

    dados_diag = [
        ("Hipótese diagnóstica de entrada",
         internacao.hipotese_diagnostica or ""),
        ("CID-10 principal (entrada)",
         internacao.cid10_principal or ""),
        ("Diagnóstico principal na alta",
         internacao.diagnostico_principal_alta or ""),
    ]
    for label, valor in dados_diag:
        story.extend(_par_campo(label, valor, estilos))

    # ---- Resumo da internação ----
    story.append(Paragraph("RESUMO DA INTERNAÇÃO", estilos["secao"]))
    texto_resumo = (internacao.resumo_alta or "").replace("\n", "<br/>")
    story.append(Paragraph(texto_resumo or "—", estilos["corpo"]))

    # ---- Condições de alta ----
    story.append(Paragraph("CONDIÇÕES DE ALTA", estilos["secao"]))

    dados_alta = [
        ("Tipo de alta", internacao.tipo_alta.value if internacao.tipo_alta else ""),
        ("Condição clínica na alta",
         internacao.condicao_alta.value if internacao.condicao_alta else ""),
        ("Retorno em",
         f"{internacao.retorno_dias} dias" if internacao.retorno_dias else "Sem retorno agendado"),
        ("Alta concedida por", internacao.dado_alta_por.nome
         if internacao.dado_alta_por else internacao.medico_responsavel.nome),
    ]
    story.append(_tabela_dados(dados_alta, estilos, colunas=2))

    # ---- Orientações ao paciente ----
    if internacao.orientacoes_alta:
        story.append(Paragraph("ORIENTAÇÕES AO PACIENTE / FAMILIAR", estilos["secao"]))
        texto_ori = internacao.orientacoes_alta.replace("\n", "<br/>")
        story.append(Paragraph(texto_ori, estilos["corpo"]))

    # ---- Prescrições na alta (medicamentos em uso) ----
    prescricao = internacao.prescricoes_medicas.filter_by(ativa=True).first()
    if prescricao and prescricao.itens:
        story.append(Paragraph("MEDICAMENTOS EM USO NA ALTA", estilos["secao"]))

        cabecalho_rx = [
            [
                Paragraph("<b>Medicamento / Item</b>", estilos["campo_label"]),
                Paragraph("<b>Dose</b>", estilos["campo_label"]),
                Paragraph("<b>Via</b>", estilos["campo_label"]),
                Paragraph("<b>Frequência</b>", estilos["campo_label"]),
                Paragraph("<b>Duração</b>", estilos["campo_label"]),
            ]
        ]
        linhas_rx = []
        for item in prescricao.itens:
            if item.status.value == "ativo":
                linhas_rx.append([
                    Paragraph(item.descricao, estilos["campo_valor"]),
                    Paragraph(item.dose or "—", estilos["campo_valor"]),
                    Paragraph(item.via.value if item.via else "—", estilos["campo_valor"]),
                    Paragraph(
                        item.frequencia.value if item.frequencia
                        else item.frequencia_custom or "—",
                        estilos["campo_valor"]
                    ),
                    Paragraph(item.duracao or "—", estilos["campo_valor"]),
                ])

        if linhas_rx:
            larguras = [6 * cm, 2.5 * cm, 2 * cm, 3.5 * cm, 3 * cm]
            tabela_rx = Table(
                cabecalho_rx + linhas_rx,
                colWidths=larguras,
            )
            tabela_rx.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d6eaf8")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aaaaaa")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(tabela_rx)

    # ---- Espaço para assinatura ----
    story.append(Spacer(1, 1.5 * cm))
    story.append(HRFlowable(width="50%", thickness=0.5,
                            color=colors.black, hAlign="CENTER", spaceAfter=4))

    medico = internacao.dado_alta_por or internacao.medico_responsavel
    story.append(Paragraph(medico.nome, estilos["assinatura"]))
    story.append(
        Paragraph("Médico responsável", ParagraphStyle(
            "ass_cargo",
            fontSize=8,
            fontName="Helvetica",
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
        ))
    )

    # ---- Rodapé ----
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#aaaaaa"), spaceBefore=4, spaceAfter=4))
    agora = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M")
    story.append(
        Paragraph(
            f"Documento gerado em {agora} &nbsp;|&nbsp; "
            f"SGHSC — Sistema de Gestão Hospitalar para Santas Casas &nbsp;|&nbsp; "
            f"{current_app.config.get('INSTITUICAO_NOME', '')}",
            estilos["rodape"],
        )
    )

    doc.build(story)
    current_app.logger.info(f"Laudo de alta gerado: {caminho}")
    return caminho


# ---------------------------------------------------------------------------
# Documentos clínicos para assinatura digital
# ---------------------------------------------------------------------------

def _doc_clinico_base(caminho: str, titulo_doc: str, numero: str):
    """Cria o SimpleDocTemplate + story inicial (cabeçalho) para um doc clínico."""
    estilos = _build_styles()
    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=2 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        title=f"{titulo_doc} — {numero}",
        author=current_app.config.get("INSTITUICAO_NOME", "SGHSC"),
    )
    story = []
    story.extend(_cabecalho_instituicao(estilos))
    story.append(Paragraph(titulo_doc.upper(), ParagraphStyle(
        "doc_titulo", fontSize=12, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4,
        textColor=colors.HexColor("#1a5276"),
    )))
    story.append(Paragraph(f"Documento Nº: <b>{numero}</b>", ParagraphStyle(
        "doc_num", fontSize=9, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=8,
        textColor=colors.HexColor("#555555"),
    )))
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#aaaaaa"), spaceAfter=8))
    return doc, story, estilos


def _bloco_paciente(story, estilos, paciente, extra: list = None):
    """Adiciona o bloco de identificação do paciente ao story."""
    story.append(Paragraph("PACIENTE", estilos["secao"]))
    dados = [
        ("Nome", paciente.nome),
        ("Data de nascimento",
         paciente.data_nascimento.strftime("%d/%m/%Y") if paciente.data_nascimento else ""),
        ("Idade", f"{paciente.idade} anos"),
        ("CNS", paciente.cns or ""),
    ]
    if extra:
        dados.extend(extra)
    story.append(_tabela_dados(dados, estilos, colunas=2))


def _rodape_assinatura(story, estilos, profissional):
    """Adiciona o bloco de identificação do profissional (assinatura eletrônica)."""
    story.append(Spacer(1, 0.8 * cm))
    conselho = ""
    if getattr(profissional, "conselho_tipo", None) and getattr(profissional, "conselho_numero", None):
        conselho = f" — {profissional.conselho_tipo} {profissional.conselho_numero}"
        if getattr(profissional, "conselho_uf", None):
            conselho += f"/{profissional.conselho_uf}"
    story.append(Paragraph(
        f"<b>{profissional.nome}</b>{conselho}", estilos["assinatura"]
    ))
    story.append(Paragraph(
        "Documento assinado digitalmente (ICP-Brasil). "
        "A validade e integridade podem ser conferidas pelo QR Code / código de validação.",
        ParagraphStyle("ass_nota", fontSize=7, fontName="Helvetica",
                       alignment=TA_CENTER, textColor=colors.HexColor("#777777")),
    ))


def _rodape_doc(story, estilos):
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#aaaaaa"), spaceBefore=4, spaceAfter=4))
    agora = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M")
    story.append(Paragraph(
        f"Documento gerado em {agora} (UTC) &nbsp;|&nbsp; SGHSC &nbsp;|&nbsp; "
        f"{current_app.config.get('INSTITUICAO_NOME', '')}",
        estilos["rodape"],
    ))


def _saida(subpasta: str, nome: str) -> str:
    pasta = os.path.join(current_app.config.get("UPLOAD_FOLDER", "uploads"), subpasta)
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, nome)


def gerar_pdf_prescricao(prescricao) -> str:
    """Gera o PDF de uma prescrição médica de internação."""
    internacao = prescricao.internacao
    caminho = _saida("prescricoes", f"prescricao_{prescricao.numero}.pdf")
    doc, story, estilos = _doc_clinico_base(caminho, "Prescrição Médica", prescricao.numero)

    _bloco_paciente(story, estilos, internacao.paciente, extra=[
        ("Internação", internacao.numero),
        ("Leito", internacao.leito.numero if internacao.leito else ""),
        ("Data da prescrição", prescricao.data_prescricao.strftime("%d/%m/%Y")),
    ])

    story.append(Paragraph("ITENS PRESCRITOS", estilos["secao"]))
    cabecalho = [[
        Paragraph("<b>Item</b>", estilos["campo_label"]),
        Paragraph("<b>Dose</b>", estilos["campo_label"]),
        Paragraph("<b>Via</b>", estilos["campo_label"]),
        Paragraph("<b>Frequência</b>", estilos["campo_label"]),
        Paragraph("<b>Horários</b>", estilos["campo_label"]),
    ]]
    linhas = []
    for item in prescricao.itens:
        if item.status.value != "ativo":
            continue
        linhas.append([
            Paragraph(item.descricao + (f"<br/><font size=7 color='#666'>{item.diluicao}</font>" if item.diluicao else ""), estilos["campo_valor"]),
            Paragraph(item.dose or "—", estilos["campo_valor"]),
            Paragraph(item.via.value if item.via else "—", estilos["campo_valor"]),
            Paragraph(item.frequencia.value if item.frequencia else (item.frequencia_custom or "—"), estilos["campo_valor"]),
            Paragraph(item.horarios or "—", estilos["campo_valor"]),
        ])
    if linhas:
        tabela = Table(cabecalho + linhas, colWidths=[6.5 * cm, 2.5 * cm, 1.8 * cm, 3.2 * cm, 3 * cm])
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d6eaf8")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aaaaaa")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tabela)
    else:
        story.append(Paragraph("Sem itens ativos.", estilos["corpo"]))

    if prescricao.observacoes:
        story.append(Paragraph("OBSERVAÇÕES", estilos["secao"]))
        story.append(Paragraph(prescricao.observacoes.replace("\n", "<br/>"), estilos["corpo"]))

    _rodape_assinatura(story, estilos, prescricao.medico)
    _rodape_doc(story, estilos)
    doc.build(story)
    current_app.logger.info(f"PDF de prescrição gerado: {caminho}")
    return caminho


def gerar_pdf_evolucao_medica(evolucao) -> str:
    """Gera o PDF de uma evolução médica."""
    internacao = evolucao.internacao
    numero = f"EVOL-{evolucao.id}"
    caminho = _saida("evolucoes", f"evolucao_medica_{evolucao.id}.pdf")
    doc, story, estilos = _doc_clinico_base(caminho, "Evolução Médica", numero)

    _bloco_paciente(story, estilos, internacao.paciente, extra=[
        ("Internação", internacao.numero),
        ("Leito", internacao.leito.numero if internacao.leito else ""),
        ("Data/hora", evolucao.registrado_em.strftime("%d/%m/%Y %H:%M")),
    ])

    story.append(Paragraph("EVOLUÇÃO (SOAP)", estilos["secao"]))
    campos = [
        ("S — Subjetivo", evolucao.subjetivo),
        ("O — Objetivo", evolucao.objetivo),
        ("A — Avaliação", evolucao.avaliacao),
        ("P — Plano", evolucao.plano),
    ]
    algum = False
    for label, valor in campos:
        if valor:
            algum = True
            story.extend(_par_campo(label, valor.replace("\n", "<br/>"), estilos))
    if evolucao.evolucao_livre:
        algum = True
        story.extend(_par_campo("Evolução", evolucao.evolucao_livre.replace("\n", "<br/>"), estilos))
    if not algum:
        story.append(Paragraph("Sem conteúdo.", estilos["corpo"]))
    if evolucao.cid10_atual:
        story.extend(_par_campo("CID-10 atual", evolucao.cid10_atual, estilos))

    _rodape_assinatura(story, estilos, evolucao.medico)
    _rodape_doc(story, estilos)
    doc.build(story)
    current_app.logger.info(f"PDF de evolução médica gerado: {caminho}")
    return caminho


def gerar_pdf_laudo_exame(solicitacao) -> str:
    """Gera o PDF do laudo/resultado de uma solicitação de exame."""
    caminho = _saida("laudos_exame", f"laudo_exame_{solicitacao.numero}.pdf")
    doc, story, estilos = _doc_clinico_base(caminho, "Laudo de Exame", solicitacao.numero)

    _bloco_paciente(story, estilos, solicitacao.paciente, extra=[
        ("Solicitante", solicitacao.solicitante.nome if solicitacao.solicitante else ""),
        ("Prioridade", solicitacao.prioridade.value),
        ("Data", solicitacao.solicitado_em.strftime("%d/%m/%Y %H:%M")),
    ])

    story.append(Paragraph("RESULTADOS", estilos["secao"]))
    cabecalho = [[
        Paragraph("<b>Exame</b>", estilos["campo_label"]),
        Paragraph("<b>Resultado</b>", estilos["campo_label"]),
        Paragraph("<b>Unidade</b>", estilos["campo_label"]),
        Paragraph("<b>Referência</b>", estilos["campo_label"]),
    ]]
    linhas = []
    responsavel = None
    for item in solicitacao.itens:
        res = item.resultado
        valor = "—"
        unidade = "—"
        ref = "—"
        if res:
            valor = res.valor or (res.laudo[:60] + "..." if res.laudo and len(res.laudo) > 60 else res.laudo) or "—"
            unidade = res.unidade or "—"
            ref = res.valor_referencia or "—"
            if res.responsavel:
                responsavel = res.responsavel
        linhas.append([
            Paragraph(item.nome_exame, estilos["campo_valor"]),
            Paragraph(str(valor), estilos["campo_valor"]),
            Paragraph(unidade, estilos["campo_valor"]),
            Paragraph(ref, estilos["campo_valor"]),
        ])
    tabela = Table(cabecalho + linhas, colWidths=[6 * cm, 5 * cm, 2.5 * cm, 3.5 * cm])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d6eaf8")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aaaaaa")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tabela)

    # Laudos descritivos longos (imagem/anatomopatológico)
    for item in solicitacao.itens:
        if item.resultado and item.resultado.laudo and len(item.resultado.laudo) > 60:
            story.append(Paragraph(f"LAUDO — {item.nome_exame}", estilos["secao"]))
            story.append(Paragraph(item.resultado.laudo.replace("\n", "<br/>"), estilos["corpo"]))

    if responsavel:
        _rodape_assinatura(story, estilos, responsavel)
    _rodape_doc(story, estilos)
    doc.build(story)
    current_app.logger.info(f"PDF de laudo de exame gerado: {caminho}")
    return caminho


def gerar_pdf_evolucao_enfermagem(evolucao) -> str:
    """Gera o PDF de uma evolução de enfermagem."""
    internacao = evolucao.internacao
    numero = f"EVENF-{evolucao.id}"
    caminho = _saida("evolucoes_enf", f"evolucao_enfermagem_{evolucao.id}.pdf")
    doc, story, estilos = _doc_clinico_base(caminho, "Evolução de Enfermagem", numero)

    turno_label = {"manha": "Manhã", "tarde": "Tarde", "noite": "Noite"}.get(evolucao.turno, evolucao.turno or "—")
    _bloco_paciente(story, estilos, internacao.paciente, extra=[
        ("Internação", internacao.numero),
        ("Leito", internacao.leito.numero if internacao.leito else ""),
        ("Turno", turno_label),
        ("Data/hora", evolucao.registrado_em.strftime("%d/%m/%Y %H:%M")),
    ])

    story.append(Paragraph("EVOLUÇÃO", estilos["secao"]))
    story.append(Paragraph((evolucao.conteudo or "").replace("\n", "<br/>"), estilos["corpo"]))
    if evolucao.observacoes:
        story.append(Paragraph("OBSERVAÇÕES", estilos["secao"]))
        story.append(Paragraph(evolucao.observacoes.replace("\n", "<br/>"), estilos["corpo"]))

    _rodape_assinatura(story, estilos, evolucao.profissional)
    _rodape_doc(story, estilos)
    doc.build(story)
    current_app.logger.info(f"PDF de evolução de enfermagem gerado: {caminho}")
    return caminho


def gerar_pdf_prescricao_enfermagem(prescricao) -> str:
    """Gera o PDF de uma prescrição de enfermagem."""
    internacao = prescricao.internacao
    numero = f"RXENF-{prescricao.id}"
    caminho = _saida("prescricoes_enf", f"prescricao_enfermagem_{prescricao.id}.pdf")
    doc, story, estilos = _doc_clinico_base(caminho, "Prescrição de Enfermagem", numero)

    _bloco_paciente(story, estilos, internacao.paciente, extra=[
        ("Internação", internacao.numero),
        ("Leito", internacao.leito.numero if internacao.leito else ""),
        ("Data da prescrição", prescricao.data_prescricao.strftime("%d/%m/%Y")),
    ])

    story.append(Paragraph("CUIDADOS DE ENFERMAGEM", estilos["secao"]))
    story.append(Paragraph((prescricao.conteudo or "").replace("\n", "<br/>"), estilos["corpo"]))
    if prescricao.observacoes:
        story.append(Paragraph("OBSERVAÇÕES", estilos["secao"]))
        story.append(Paragraph(prescricao.observacoes.replace("\n", "<br/>"), estilos["corpo"]))

    _rodape_assinatura(story, estilos, prescricao.enfermeiro)
    _rodape_doc(story, estilos)
    doc.build(story)
    current_app.logger.info(f"PDF de prescrição de enfermagem gerado: {caminho}")
    return caminho


def gerar_pdf_descricao_cirurgica(cirurgia) -> str:
    """Gera o PDF da descrição cirúrgica (nota de sala)."""
    caminho = _saida("descricoes_cirurgicas", f"descricao_cirurgica_{cirurgia.numero}.pdf")
    doc, story, estilos = _doc_clinico_base(caminho, "Descrição Cirúrgica", cirurgia.numero)

    _bloco_paciente(story, estilos, cirurgia.paciente, extra=[
        ("Procedimento", cirurgia.procedimento),
        ("Cirurgião", cirurgia.cirurgiao.nome if cirurgia.cirurgiao else ""),
        ("Data", cirurgia.data_agendada.strftime("%d/%m/%Y %H:%M") if cirurgia.data_agendada else ""),
    ])

    campos = [
        ("Descrição cirúrgica", cirurgia.descricao_cirurgica),
        ("Achados", cirurgia.achados),
        ("Procedimento realizado", cirurgia.procedimento_realizado),
        ("Intercorrências", cirurgia.intercorrencias),
        ("Equipe", cirurgia.equipe),
        ("Material utilizado", cirurgia.material_utilizado),
    ]
    story.append(Paragraph("DESCRIÇÃO", estilos["secao"]))
    algum = False
    for label, valor in campos:
        if valor:
            algum = True
            story.extend(_par_campo(label, valor.replace("\n", "<br/>"), estilos))
    if not algum:
        story.append(Paragraph("Sem conteúdo registrado.", estilos["corpo"]))

    _rodape_assinatura(story, estilos, cirurgia.cirurgiao)
    _rodape_doc(story, estilos)
    doc.build(story)
    current_app.logger.info(f"PDF de descrição cirúrgica gerado: {caminho}")
    return caminho
