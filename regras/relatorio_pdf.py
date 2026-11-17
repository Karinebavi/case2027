# -*- coding: utf-8 -*-
"""
Relatório das inscrições em PDF — com as IMAGENS dos gráficos da tela Relatórios:
indicadores, situação, regiões, estados, mapa do Brasil, nuvem de cidades, dias de
envio e o perfil das organizações (equipe, receita, infraestrutura, canais, Lei de
Incentivo, modalidades em barras e em nuvem). Pouca pontuação (pedido da Karine).

Usa o recorte filtrado e os números de regras/relatorio_dados.py (mesma fonte da
tela). Não traz nome de entidade, CNPJ nem contato — só números agregados.
"""
import io
import json
import math
import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from fpdf import FPDF  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from regras import pontuacao  # noqa: E402
from regras import relatorio_dados as rd  # noqa: E402

# Mesmas cores da tela (telas/dashboard.py)
ROXO, ROXO_ESCURO, LARANJA, LAVANDA = "#9333EA", "#3E087C", "#E07B12", "#F2F0FC"
TINTA, TINTA_SUAVE, GRADE = "#2B2540", "#6B6780", "#EEEAF6"
RAMPA = ["#D9C2FA", "#BB92F3", "#9F62EC", "#8434E0", "#6420B5", "#46138A"]
CATEGORICAS = ["#9333EA", "#E07B12", "#1F9E89", "#C2410C", "#5B6BD6"]
COR_SITUACAO = {"Classificada": "#2E7D32", "Fila de espera": "#C99A2E", "Eliminada": "#B84A4A"}
_FONTES = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
_MAPA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "base", "brasil_uf.geojson")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": TINTA,
                     "axes.labelcolor": TINTA_SUAVE, "xtick.color": TINTA_SUAVE, "ytick.color": TINTA_SUAVE})


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rampa(n):
    if n <= 1:
        return [ROXO]
    return [RAMPA[round(i * (len(RAMPA) - 1) / (n - 1))] for i in range(n)]


def _curto(texto, n=34):
    texto = str(texto)
    texto = texto if len(texto) <= n else texto[: n - 1].rstrip() + "…"
    return texto.replace("$", r"\$")  # "R$" não pode virar fórmula matemática no gráfico


def _contagem(serie, ordem=None):
    s = serie.astype(str).str.strip()
    c = s[s != ""].value_counts()
    if ordem:
        c = c.reindex([o for o in ordem if o in c.index] + [o for o in c.index if o not in ordem])
    return c


# ------------------------------------------------------------------ PDF base

class _PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("dj", "", 8)
        self.set_text_color(*_rgb(TINTA_SUAVE))
        self.cell(0, 6, "CASE 2027 · Relatório das inscrições", align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("dj", "", 8)
        self.set_text_color(*_rgb(TINTA_SUAVE))
        self.cell(0, 6, f"Página {self.page_no()}/{{nb}}", align="R")


def _novo():
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("dj", "", os.path.join(_FONTES, "DejaVuSans.ttf"))
    pdf.add_font("dj", "B", os.path.join(_FONTES, "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(True, margin=16)
    pdf.set_margins(14, 14, 14)
    pdf.alias_nb_pages()
    return pdf


def _largura(pdf):
    return pdf.w - pdf.l_margin - pdf.r_margin


def _secao(pdf, texto, espaco=70):
    if pdf.get_y() + espaco > pdf.h - 18:
        pdf.add_page()
    pdf.ln(2)
    pdf.set_font("dj", "B", 13)
    pdf.set_text_color(*_rgb(ROXO_ESCURO))
    pdf.cell(0, 8, texto, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*_rgb(ROXO))
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)


def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


def _imagens(pdf, figuras, altura):
    """Uma figura na largura toda, ou duas lado a lado (com o título em cima de cada)."""
    figuras = [f for f in figuras if f[1] is not None]
    if not figuras:
        return
    if pdf.get_y() + altura + 8 > pdf.h - 18:
        pdf.add_page()
    y0 = pdf.get_y()
    larg = (_largura(pdf) - 6 * (len(figuras) - 1)) / len(figuras)
    for i, (titulo, fig) in enumerate(figuras):
        x = pdf.l_margin + i * (larg + 6)
        pdf.set_xy(x, y0)
        pdf.set_font("dj", "B", 9.5)
        pdf.set_text_color(*_rgb(ROXO_ESCURO))
        pdf.cell(larg, 5, titulo)
        pdf.image(_png(fig), x=x, y=y0 + 6, w=larg, h=altura, keep_aspect_ratio=True)
    pdf.set_xy(pdf.l_margin, y0 + altura + 9)


def _indicadores(pdf, itens):
    """Quadradinhos com os números principais (como na tela)."""
    n = len(itens)
    larg = (_largura(pdf) - 4 * (n - 1)) / n
    y = pdf.get_y()
    for i, (rotulo, valor) in enumerate(itens):
        x = pdf.l_margin + i * (larg + 4)
        pdf.set_fill_color(*_rgb(LAVANDA))
        pdf.set_draw_color(*_rgb(GRADE))
        pdf.rect(x, y, larg, 20, style="DF", round_corners=True, corner_radius=2.5)
        pdf.set_xy(x + 3, y + 2.5)
        pdf.set_font("dj", "", 7.5)
        pdf.set_text_color(*_rgb(TINTA_SUAVE))
        pdf.cell(larg - 6, 4, rotulo)
        pdf.set_xy(x + 3, y + 8)
        pdf.set_font("dj", "B", 15)
        pdf.set_text_color(*_rgb(ROXO_ESCURO))
        pdf.cell(larg - 6, 9, str(valor))
    pdf.set_xy(pdf.l_margin, y + 25)


# ------------------------------------------------------------------ gráficos

def _eixo(ax, contagem="y"):
    for lado in ("top", "right", "left", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(length=0, labelsize=8)
    (ax.yaxis if contagem == "y" else ax.xaxis).set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis=contagem, color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def _barras(rotulos, valores, cores=None, horizontal=False, pct=False, tamanho=(5.2, 3.0)):
    rotulos, valores = [_curto(r) for r in rotulos], [int(v) for v in valores]
    if not valores or not sum(valores):
        return None
    total = sum(valores)
    textos = [("" if not v else f"{v} ({100 * v / total:.0f}%)" if pct else str(v)) for v in valores]
    cores = cores or ROXO
    fig, ax = plt.subplots(figsize=tamanho)
    if horizontal:
        pos = list(range(len(valores)))[::-1]
        barras = ax.barh(pos, valores, color=cores, height=0.62)
        ax.set_yticks(pos, rotulos)
        ax.set_xlim(0, max(valores) * 1.35 + 0.5)
        _eixo(ax, "x")
        for b, t in zip(barras, textos):
            ax.text(b.get_width() + max(valores) * 0.02, b.get_y() + b.get_height() / 2, t,
                    va="center", fontsize=8, color=TINTA)
    else:
        barras = ax.bar(rotulos, valores, color=cores, width=0.62)
        ax.set_ylim(0, max(valores) * 1.25 + 0.5)
        _eixo(ax, "y")
        if len(rotulos) > 6:
            plt.setp(ax.get_xticklabels(), rotation=40, ha="right")
        for b, t in zip(barras, textos):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), t, ha="center", va="bottom",
                    fontsize=8, color=TINTA)
    return fig


def _rosca(rotulos, valores, cores, centro=None, tamanho=(5.2, 3.0)):
    valores = [int(v) for v in valores]
    if not sum(valores):
        return None
    total = sum(valores)
    fig, ax = plt.subplots(figsize=tamanho)
    fatias, _ = ax.pie(valores, colors=cores, startangle=90, counterclock=False,
                       wedgeprops=dict(width=0.38, edgecolor="white", linewidth=2))
    for f, v in zip(fatias, valores):
        ang = math.radians((f.theta1 + f.theta2) / 2)
        ax.text(1.2 * math.cos(ang), 1.2 * math.sin(ang), f"{v} ({100 * v / total:.0f}%)",
                ha="center", va="center", fontsize=8, color=TINTA)
    if centro:
        ax.text(0, 0, centro, ha="center", va="center", fontsize=11, color=ROXO_ESCURO, fontweight="bold")
    ax.legend(fatias, [_curto(r, 40) for r in rotulos], loc="center left", bbox_to_anchor=(1.15, 0.5),
              frameon=False, fontsize=8)
    ax.set_aspect("equal")
    return fig


def _area(anel):
    anel = [tuple(pt[:2]) for pt in anel]
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(anel, anel[1:] + anel[:1])) / 2


def _centro(anel):
    """Centro de verdade do polígono (pela área), para o rótulo cair dentro do estado."""
    anel = [tuple(pt[:2]) for pt in anel]
    a = _area(anel) or 1e-9
    pares = list(zip(anel, anel[1:] + anel[:1]))
    cx = sum((x0 + x1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in pares) / (6 * a)
    cy = sum((y0 + y1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in pares) / (6 * a)
    return cx, cy


def _mapa(contagem_uf):
    """Mapa do Brasil por estado, desenhado com o mesmo GeoJSON da tela (sem internet)."""
    if not os.path.exists(_MAPA):
        return None
    with open(_MAPA, encoding="utf-8") as f:
        gj = json.load(f)
    maior = max(contagem_uf.values()) if contagem_uf else 0
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    for feat in gj["features"]:
        uf = feat["properties"].get("sigla")
        n = int(contagem_uf.get(uf, 0))
        cor = RAMPA[1 + round((n / maior) * (len(RAMPA) - 2))] if n and maior else "#F4EEFD"
        geom = feat["geometry"]
        polis = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for p in polis:
            ax.add_patch(Polygon(p[0], closed=True, facecolor=cor, edgecolor="white", linewidth=0.7))
        if n:
            cx, cy = _centro(max((p[0] for p in polis), key=lambda a: abs(_area(a))))
            escuro = n / maior > 0.45
            ax.text(cx, cy, f"{uf}\n{n}", ha="center", va="center", fontsize=7,
                    fontweight="bold", color="white" if escuro else ROXO_ESCURO, zorder=5)
    ax.set_xlim(-74.5, -34)
    ax.set_ylim(-34.5, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig


def _nuvem(freqs, tamanho=(9, 3.4)):
    freqs = {k: v for k, v in (freqs or {}).items() if str(k).strip()}
    if not freqs:
        return None
    from wordcloud import WordCloud
    tons = RAMPA[2:] + [LARANJA]

    def _cor(palavra, **_):
        return tons[sum(map(ord, palavra)) % len(tons)]
    larg, alt = int(tamanho[0] * 150), int(tamanho[1] * 150)
    wc = WordCloud(width=larg, height=alt, background_color="white", color_func=_cor, prefer_horizontal=0.9,
                   collocations=False, font_step=2, margin=6).generate_from_frequencies(freqs)
    fig, ax = plt.subplots(figsize=tamanho)
    ax.imshow(wc.to_array(), interpolation="bilinear")
    ax.axis("off")
    return fig


# ------------------------------------------------------------------ relatório

def gerar(w, filtros_txt, total_base):
    """Bytes do PDF do recorte `w` (já filtrado). `total_base`: inscrições sem filtro."""
    pdf = _novo()
    pdf.add_page()

    # capa
    pdf.set_fill_color(*_rgb(ROXO_ESCURO))
    pdf.rect(0, 0, pdf.w, 42, style="F")
    pdf.set_xy(14, 12)
    pdf.set_font("dj", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "CASE 2027", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.set_font("dj", "", 12)
    pdf.cell(0, 7, "Relatório das inscrições", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(48)
    pdf.set_font("dj", "", 8.5)
    pdf.set_text_color(*_rgb(TINTA_SUAVE))
    pdf.multi_cell(0, 4.5, f"Gerado em {datetime.now():%d/%m/%Y às %H:%M} · Instituto Imaginação\n"
                           f"{len(w)} de {total_base} inscrições · Filtros: {filtros_txt}",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    _indicadores(pdf, [("Inscrições", len(w)),
                       ("Estados", int(w["UF"].replace("", pd.NA).nunique())),
                       ("Cidades", int(w["Local"].replace("", pd.NA).nunique())),
                       ("Classificadas", int((w["Situação"] == "Classificada").sum())),
                       ("Eliminadas", int((w["Status"] == "Eliminada").sum()))])

    sit = _contagem(w["Situação"], list(COR_SITUACAO))
    reg = _contagem(w["Região"], rd.ORDEM_REGIAO)
    _imagens(pdf, [("Situação das inscrições",
                    _rosca(sit.index, sit.values, [COR_SITUACAO.get(s, "#888") for s in sit.index],
                           centro=f"{int(sit.sum())}\ninscrições")),
                   ("Inscrições por região", _barras(reg.index, reg.values, horizontal=True, pct=True))], 55)

    datas = pd.Series([d for d in w.get("_envio", []) if d is not None])
    if len(datas):
        pordia = datas.value_counts().sort_index()
        _imagens(pdf, [("Dias com mais inscrições", _barras([d.strftime("%d/%m") for d in pordia.index],
                                                            pordia.values, tamanho=(9, 2.6)))], 46)

    # onde estão
    _secao(pdf, "Onde estão", 140)  # o título vai junto com o mapa para a página seguinte
    uf = _contagem(w["UF"])
    _imagens(pdf, [("Mapa do Brasil — inscrições por estado", _mapa(uf.to_dict()))], 118)
    _imagens(pdf, [("Inscrições por estado", _barras(uf.index, uf.values, tamanho=(9, 2.6)))], 48)
    top = _contagem(w["Local"]).head(10)
    _imagens(pdf, [("Nuvem de cidades", _nuvem(_contagem(w["Cidade"]).to_dict(), (5.2, 3.0))),
                   ("Cidades mais frequentes", _barras(top.index, top.values, cores=LARANJA, horizontal=True))], 58)

    # perfil
    _secao(pdf, "Perfil das organizações", 70)
    vazio = pd.Series(dtype=str)
    eq = _contagem(w.get("p21", vazio), list(pontuacao.EQUIPE))
    rec = _contagem(w.get("p22", vazio), list(pontuacao.RECEITA))
    _imagens(pdf, [("Equipe (nº de pessoas)", _barras(eq.index, eq.values, cores=_rampa(len(eq)), pct=True)),
                   ("Receita bruta anual", _barras(rec.index, rec.values, cores=_rampa(len(rec)),
                                                   horizontal=True, pct=True))], 55)
    adm = _contagem(w.get("p23", vazio), list(pontuacao.INFRA_ADMIN))
    esp = _contagem(w.get("p24", vazio), list(pontuacao.INFRA_ESP))
    _imagens(pdf, [("Infraestrutura administrativa", _rosca(adm.index, adm.values, (CATEGORICAS * 2)[: len(adm)])),
                   ("Infraestrutura esportiva", _rosca(esp.index, esp.values, (CATEGORICAS * 2)[: len(esp)]))], 52)
    canais = rd.tabela_canais(w)
    lie = _contagem(w.get("p20_lie", vazio))
    _imagens(pdf, [("Canais digitais", _barras(canais["Canal"], canais["Inscrições"], horizontal=True, pct=True)
                    if len(canais) else None),
                   ("Situação na Lei de Incentivo (LIE)",
                    _rosca(lie.index, lie.values, (CATEGORICAS * 2)[: len(lie)]) if len(lie) else None)], 52)
    mod = rd.tabela_modalidades(w)
    if len(mod):
        top_mod = mod.head(12)
        _imagens(pdf, [("Modalidades esportivas", _barras(top_mod["Modalidade"], top_mod["Inscrições"],
                                                          horizontal=True, tamanho=(9, 0.32 * len(top_mod) + 0.9)))],
                 min(90, 7 * len(top_mod) + 14))
        _imagens(pdf, [("Nuvem de modalidades", _nuvem(dict(zip(mod["Modalidade"], mod["Inscrições"]))))], 58)

    pdf.ln(2)
    pdf.set_font("dj", "", 7.5)
    pdf.set_text_color(*_rgb(TINTA_SUAVE))
    pdf.multi_cell(0, 4, "Estados e cidades padronizados pela lista oficial do IBGE (ex.: “BH” e “Belo Horisonte” "
                         "contam como Belo Horizonte/MG). Percentuais sobre as inscrições do recorte. "
                         "Sem nomes de organizações nem contatos.", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
