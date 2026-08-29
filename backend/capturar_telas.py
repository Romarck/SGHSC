"""
capturar_telas.py — Gera as capturas de tela do guia de uso via Playwright.

Requer: seed_demo.py já executado e o app rodando.
Uso: docker compose exec app python capturar_telas.py
Saída: PNGs em /tmp/shots/ (copiar com docker compose cp).
"""

import os
from playwright.sync_api import sync_playwright

from app import create_app
from app.models.internacao import Internacao
from app.models.exame import SolicitacaoExame
from app.models.cirurgia import Cirurgia
from app.models.maternidade import Parto, PreNatal

BASE = "http://localhost:5000"
OUT = "/tmp/shots"
os.makedirs(OUT, exist_ok=True)

# Descobre IDs reais dos registros de demonstração
app = create_app("development")
with app.app_context():
    intern = Internacao.query.filter(Internacao.numero.like("INTDEMO%")).first()
    solic = SolicitacaoExame.query.filter(SolicitacaoExame.numero.like("EXDEMO%")).first()
    cir = Cirurgia.query.filter(Cirurgia.numero.like("CIRDEMO%")).first()
    parto = Parto.query.filter(Parto.numero.like("PARTDEMO%")).first()
    pn = PreNatal.query.first()
    INTERN_ID = intern.id if intern else 1
    SOLIC_ID = solic.id if solic else 1
    CIR_ID = cir.id if cir else 1
    PARTO_ID = parto.id if parto else 1
    PN_ID = pn.id if pn else 1

# Lista de (nome_arquivo, caminho_url) a capturar
TELAS = [
    ("01_dashboard", "/dashboard"),
    ("03_pacientes_lista", "/pacientes/"),
    ("04_emergencia_fila", "/emergencia/"),
    ("05_ambulatorio_agenda", "/ambulatorio/"),
    ("06_internacao_mapa", "/internacao/leitos"),
    ("06_internacao_lista", "/internacao/"),
    ("06_internacao_prontuario", f"/internacao/{INTERN_ID}"),
    ("07_certificado_painel", "/certificado/"),
    ("08_exames_lista", "/exames/"),
    ("08_exames_detalhe", f"/exames/{SOLIC_ID}"),
    ("09_farmacia_estoque", "/farmacia/estoque"),
    ("10_nutricao_mapa", "/nutricao/mapa"),
    ("11_ccih_painel", "/ccih/painel"),
    ("12_cirurgias_escala", "/cirurgias/"),
    ("12_cirurgias_detalhe", f"/cirurgias/{CIR_ID}"),
    ("13_maternidade_painel", "/maternidade/"),
    ("13_maternidade_parto", f"/maternidade/parto/{PARTO_ID}"),
    ("14_estoque_produtos", "/estoque/produtos"),
    ("14_compras_pedidos", "/compras/pedidos"),
    ("14_financeiro_contas", "/financeiro/contas"),
    ("14_faturamento_guias", "/faturamento/guias"),
    ("14_convenios_guias", "/convenios/guias"),
    ("14_patrimonio_bens", "/patrimonio/bens"),
    ("14_rh_funcionarios", "/rh/funcionarios"),
    ("14_manutencao_ordens", "/manutencao/ordens"),
    ("15_relatorios_dashboard", "/relatorios/"),
    ("15_residuos_painel", "/residuos/painel"),
    ("15_rnds_fila", "/rnds/fila"),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900})
        page = ctx.new_page()

        # Login
        page.goto(f"{BASE}/auth/login", wait_until="networkidle")
        page.fill("input[name='username']", "dr.demo")
        page.fill("input[name='senha']", "Demo@123")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        if "login" in page.url:
            print("FALHA no login. URL atual:", page.url)
            browser.close()
            return

        # Captura a tela de login separadamente (deslogado)
        ctx2 = browser.new_context(viewport={"width": 1366, "height": 900})
        pg2 = ctx2.new_page()
        pg2.goto(f"{BASE}/auth/login", wait_until="networkidle")
        pg2.screenshot(path=f"{OUT}/00_login.png", full_page=True)
        ctx2.close()

        ok, erros = 0, []
        for nome, url in TELAS:
            try:
                page.goto(f"{BASE}{url}", wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(600)  # deixa HTMX/contadores carregarem
                page.screenshot(path=f"{OUT}/{nome}.png", full_page=True)
                ok += 1
                print(f"  [ok] {nome} <- {url}")
            except Exception as e:
                erros.append((nome, url, str(e)))
                print(f"  [ERRO] {nome} <- {url}: {e}")

        browser.close()
        print(f"\nCapturas: {ok}/{len(TELAS)} | login: 00_login.png")
        if erros:
            print("Erros:")
            for n, u, e in erros:
                print(f"  {n} ({u}): {e[:80]}")


if __name__ == "__main__":
    main()
