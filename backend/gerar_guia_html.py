"""
gerar_guia_html.py — Converte docs/GUIA_DE_USO.md em uma página HTML única e
autocontida (CSS embutido + imagens em base64) com botão de exportar PDF.

Uso: python gerar_guia_html.py
Saída: docs/GUIA_DE_USO.html

Não depende de bibliotecas externas — conversor markdown mínimo cobrindo os
elementos usados no guia (títulos, listas, negrito, código, imagens, tabelas,
citações, regras horizontais).
"""

import base64
import html
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(BASE, "docs")
MD_PATH = os.path.join(DOCS, "GUIA_DE_USO.md")
OUT_PATH = os.path.join(DOCS, "GUIA_DE_USO.html")
# Cópia servida pela aplicação (dentro de backend/app/static)
STATIC_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "app", "static", "guia", "guia_de_uso.html")


def slug(texto: str) -> str:
    """
    Gera o id da âncora no mesmo estilo do GitHub (que o índice do markdown
    assume): minúsculas, acentos PRESERVADOS, pontuação removida (exceto hífen),
    espaços viram hífen. Usa \\w com re.UNICODE para manter letras acentuadas.
    """
    txt = texto.strip().lower()
    # remove pontuação (exceto espaço e hífen); NÃO colapsa espaços — o GitHub
    # troca cada espaço por um hífen, então "a / b" (2 espaços) vira "a--b".
    txt = re.sub(r"[^\w\s-]", "", txt, flags=re.UNICODE)
    return txt.replace(" ", "-")


def img_base64(caminho_rel: str) -> str:
    """Retorna data URI base64 da imagem, ou o caminho original se não achar."""
    caminho = os.path.join(DOCS, caminho_rel)
    if not os.path.exists(caminho):
        return caminho_rel
    with open(caminho, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def inline(texto: str) -> str:
    """Formatação inline: escapa HTML e aplica negrito, código e links."""
    texto = html.escape(texto)
    texto = re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)
    texto = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", texto)
    # links [texto](url) — depois de escapar, os parênteses estão intactos
    texto = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', texto)
    return texto


def converter(md: str) -> str:
    linhas = md.split("\n")
    out = []
    i = 0
    n = len(linhas)

    def fecha_lista(pilha):
        while pilha:
            out.append(f"</{pilha.pop()}>")

    pilha_lista = []

    while i < n:
        linha = linhas[i]
        stripped = linha.strip()

        # Regra horizontal
        if re.match(r"^---+$", stripped):
            fecha_lista(pilha_lista)
            out.append("<hr>")
            i += 1
            continue

        # Imagem isolada  ![alt](caminho)
        m_img = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if m_img:
            fecha_lista(pilha_lista)
            alt = html.escape(m_img.group(1))
            src = img_base64(m_img.group(2))
            out.append(f'<p class="img"><img src="{src}" alt="{alt}"></p>')
            i += 1
            continue

        # Títulos
        m_h = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m_h:
            fecha_lista(pilha_lista)
            nivel = len(m_h.group(1))
            texto = m_h.group(2)
            _id = slug(texto)
            out.append(f'<h{nivel} id="{_id}">{inline(texto)}</h{nivel}>')
            i += 1
            continue

        # Citação (blockquote)
        if stripped.startswith(">"):
            fecha_lista(pilha_lista)
            bloco = []
            while i < n and linhas[i].strip().startswith(">"):
                bloco.append(linhas[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(bloco))}</blockquote>")
            continue

        # Tabela (linha com | e a seguinte com ---)
        if "|" in stripped and i + 1 < n and re.match(r"^[\s|:-]+$", linhas[i + 1].strip()):
            fecha_lista(pilha_lista)
            header = [c.strip() for c in stripped.strip("|").split("|")]
            out.append('<table><thead><tr>')
            out.extend(f"<th>{inline(c)}</th>" for c in header)
            out.append("</tr></thead><tbody>")
            i += 2
            while i < n and "|" in linhas[i]:
                cols = [c.strip() for c in linhas[i].strip().strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cols) + "</tr>")
                i += 1
            out.append("</tbody></table>")
            continue

        # Lista ordenada
        m_ol = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m_ol:
            if not pilha_lista or pilha_lista[-1] != "ol":
                fecha_lista(pilha_lista)
                out.append("<ol>")
                pilha_lista.append("ol")
            out.append(f"<li>{inline(m_ol.group(2))}</li>")
            i += 1
            continue

        # Lista não ordenada
        m_ul = re.match(r"^[-*]\s+(.*)$", stripped)
        if m_ul:
            if not pilha_lista or pilha_lista[-1] != "ul":
                fecha_lista(pilha_lista)
                out.append("<ul>")
                pilha_lista.append("ul")
            out.append(f"<li>{inline(m_ul.group(1))}</li>")
            i += 1
            continue

        # Linha em branco
        if not stripped:
            fecha_lista(pilha_lista)
            i += 1
            continue

        # Parágrafo comum
        fecha_lista(pilha_lista)
        out.append(f"<p>{inline(stripped)}</p>")
        i += 1

    fecha_lista(pilha_lista)
    return "\n".join(out)


CSS = """
:root { --azul:#1a5276; --azul-claro:#2e86c1; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
       color:#222; line-height:1.6; margin:0; background:#f4f6f8; }
.container { max-width: 900px; margin: 0 auto; padding: 40px 32px 80px;
             background:#fff; box-shadow:0 0 20px rgba(0,0,0,.06); min-height:100vh; }
h1 { color:var(--azul); border-bottom:3px solid var(--azul); padding-bottom:8px; }
h2 { color:var(--azul); border-bottom:1px solid #ddd; padding-bottom:6px; margin-top:2em; }
h3 { color:var(--azul-claro); margin-top:1.5em; }
h4 { color:#555; }
code { background:#eef2f5; padding:2px 6px; border-radius:4px; font-size:.9em;
       font-family:"SF Mono", Consolas, monospace; color:#c0392b; }
blockquote { border-left:4px solid var(--azul-claro); background:#eef5fb;
             margin:1em 0; padding:10px 16px; border-radius:0 6px 6px 0; color:#34495e; }
table { border-collapse:collapse; width:100%; margin:1em 0; }
th, td { border:1px solid #ddd; padding:8px 12px; text-align:left; }
th { background:var(--azul); color:#fff; }
tr:nth-child(even) td { background:#f7f9fa; }
p.img { text-align:center; margin:1.5em 0; }
p.img img { max-width:100%; border:1px solid #ddd; border-radius:6px;
            box-shadow:0 2px 8px rgba(0,0,0,.1); }
a { color:var(--azul-claro); }
ul, ol { padding-left:1.6em; }
hr { border:none; border-top:1px solid #e0e0e0; margin:2em 0; }

/* Barra de ações (não aparece na impressão) */
.toolbar { position:sticky; top:0; z-index:10; background:var(--azul);
           padding:12px 32px; display:flex; justify-content:space-between;
           align-items:center; box-shadow:0 2px 6px rgba(0,0,0,.15); }
.toolbar span { color:#fff; font-weight:600; }
.btn-pdf { background:#fff; color:var(--azul); border:none; padding:8px 18px;
           border-radius:6px; font-weight:600; cursor:pointer; font-size:14px; }
.btn-pdf:hover { background:#eaf2f8; }

@media print {
  .toolbar { display:none; }
  body { background:#fff; }
  .container { box-shadow:none; max-width:100%; padding:0; }
  h2 { page-break-before: auto; }
  p.img { page-break-inside: avoid; }
  h1, h2, h3, h4 { page-break-after: avoid; }
}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SGHSC — Guia de Uso</title>
<style>{css}</style>
</head>
<body>
<div class="toolbar">
  <span>SGHSC — Guia de Uso</span>
  <button class="btn-pdf" onclick="window.print()">Exportar PDF / Imprimir</button>
</div>
<div class="container">
{conteudo}
</div>
</body>
</html>
"""


def main():
    with open(MD_PATH, encoding="utf-8") as f:
        md = f.read()
    conteudo = converter(md)
    html_final = TEMPLATE.format(css=CSS, conteudo=conteudo)
    # 1) cópia em docs/ (portável, para distribuição avulsa)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_final)
    # 2) cópia servida pela aplicação (rota /guia)
    os.makedirs(os.path.dirname(STATIC_OUT), exist_ok=True)
    with open(STATIC_OUT, "w", encoding="utf-8") as f:
        f.write(html_final)
    tamanho_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"Gerado: {OUT_PATH} ({tamanho_kb:.0f} KB)")
    print(f"Gerado: {STATIC_OUT} (servido pela aplicação em /guia)")


if __name__ == "__main__":
    main()
