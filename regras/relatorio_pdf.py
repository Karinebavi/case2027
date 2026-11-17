# -*- coding: utf-8 -*-
"""
Relatório técnico das inscrições em PDF (fpdf2 + gráficos do matplotlib).

Usa as MESMAS tabelas da tela (regras/relatorio_dados.py) e o recorte filtrado.
Não traz nome de entidade, CNPJ nem contato — só números agregados — para poder
circular com patrocinador e equipe sem expor dado pessoal.
"""
import io
import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from fpdf import FPDF  # noqa: E402
from fpdf.fonts import FontFace  # noqa: E402

from regras import relatorio_dados as rd  # noqa: E402

ROXO, ROXO_ESCURO, LARANJA, LAVANDA, CINZA = "#9333EA", "#3E087C", "#FF9A2D", "#F2F0FC", "#625E75"
_FONTES = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class _PDF(FPDF):
    titulo = "CASE 2027 · Relatório das inscrições"

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("dj", "", 8)
        self.set_text_color(*_rgb(CINZA))
        self.cell(0, 6, self.titulo, align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("dj", "", 8)
        self.set_text_color(*_rgb(CINZA))
        self.cell(0, 6, f"Página {self.page_no()}/{{nb}}", align="R")


def _novo():
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("dj", "", os.path.join(_FONTES, "DejaVuSans.ttf"))
    pdf.add_font("dj", "B", os.path.join(_FONTES, "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(True, margin=16)
    pdf.set_margins(14, 14, 14)
    pdf.alias_nb_pages()
    return pdf


def _secao(pdf, texto):
    if pdf.get_y() > 240:
        pdf.add_page()
    pdf.ln(3)
    pdf.set_font("dj", "B", 13)
    pdf.set_text_color(*_rgb(ROXO_ESCURO))
    pdf.cell(0, 8, texto, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*_rgb(ROXO))
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _sub(pdf, texto):
    if pdf.get_y() > 250:
        pdf.add_page()
    pdf.ln(1)
    pdf.set_font("dj", "B", 10)
    pdf.set_text_color(*_rgb(ROXO_ESCURO))
    pdf.cell(0, 6, texto, new_x="LMARGIN", new_y="NEXT")


def _texto(pdf, texto, tam=9, cor=CINZA):
    pdf.set_font("dj", "", tam)
    pdf.set_text_color(*_rgb(cor))
    pdf.multi_cell(0, 4.6, texto, new_x="LMARGIN", new_y="NEXT")


def _fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.1f}".replace(".", ",")
    if isinstance(v, int):
        return f"{v:,}".replace(",", ".")
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y")
    return str(v)


def _tabela(pdf, df, larguras=None, tam=8):
    if df is None or not len(df):
        _texto(pdf, "Sem dados neste recorte.")
        return
    pdf.set_font("dj", "", tam)
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(220, 216, 235)
    pdf.set_line_width(0.2)
    pdf.set_fill_color(250, 249, 254)  # zebra lavanda bem clara (a capa deixa o roxo no "pincel")
    cab = FontFace(emphasis="BOLD", color=_rgb(ROXO_ESCURO), fill_color=_rgb(LAVANDA))

    def _num(v):
        return v is None or isinstance(v, (int, float)) and not isinstance(v, bool)
    numericas = [c for c in df.columns if all(_num(v) for v in df[c].tolist())]
    alinh = tuple("RIGHT" if c in numericas else "LEFT" for c in df.columns)
    with pdf.table(col_widths=larguras, text_align=alinh, headings_style=cab, line_height=4.8,
                   cell_fill_mode="ROWS", first_row_as_headings=True) as t:
        t.row([str(c) for c in df.columns])
        for _, linha in df.iterrows():
            t.row([_fmt(v) for v in linha.values])
    pdf.ln(2)


def _grafico(pdf, fig, altura_mm=62):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    if pdf.get_y() + altura_mm > pdf.h - 18:
        pdf.add_page()
    pdf.image(buf, x=pdf.l_margin, w=pdf.w - pdf.l_margin - pdf.r_margin, h=altura_mm, keep_aspect_ratio=True)
    pdf.ln(2)


def _eixo(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(colors="#444444", labelsize=8)
    from matplotlib.ticker import MaxNLocator
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))  # contagens: só números inteiros


def _barras(rotulos, valores, titulo, cor=ROXO, horizontal=False, xlabel="", ylabel="Inscrições"):
    fig, ax = plt.subplots(figsize=(8, 2.9))
    if horizontal:
        ax.barh(rotulos[::-1], valores[::-1], color=cor)
        for i, v in enumerate(valores[::-1]):
            ax.text(v, i, f" {v:g}", va="center", fontsize=7, color="#333333")
        ax.set_xlabel(ylabel, fontsize=8)
    else:
        ax.bar(rotulos, valores, color=cor)
        for i, v in enumerate(valores):
            ax.text(i, v, f"{v:g}", ha="center", va="bottom", fontsize=7, color="#333333")
        ax.set_ylabel(ylabel, fontsize=8)
        ax.set_xlabel(xlabel, fontsize=8)
        plt.setp(ax.get_xticklabels(), rotation=0 if len(rotulos) < 10 else 45, ha="center" if len(rotulos) < 10 else "right")
    ax.set_title(titulo, fontsize=9, color=ROXO_ESCURO, loc="left")
    _eixo(ax)
    return fig


def gerar(w, filtros_txt, total_base):
    """Bytes do PDF do recorte `w` (já filtrado). `total_base`: inscrições sem filtro."""
    pdf = _novo()
    pdf.add_page()

    # ---------------- capa
    pdf.set_fill_color(*_rgb(ROXO_ESCURO))
    pdf.rect(0, 0, pdf.w, 46, style="F")
    pdf.set_xy(14, 13)
    pdf.set_font("dj", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "CASE 2027", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.set_font("dj", "", 12)
    pdf.cell(0, 7, "Relatório das inscrições · Etapa 1", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(54)
    _texto(pdf, f"Gerado em {datetime.now():%d/%m/%Y às %H:%M} · Instituto Imaginação", 9, CINZA)
    _texto(pdf, f"Recorte: {len(w)} de {total_base} inscrições · Filtros: {filtros_txt}", 9, CINZA)

    # ---------------- 1. resumo
    _secao(pdf, "Resumo")
    em = w[w["Situação"].isin(rd.EM_CLASSIFICACAO)]["Nota"].dropna()
    resumo = {"Inscrições": len(w),
              "Estados": int(w["UF"].replace("", pd.NA).nunique()),
              "Cidades": int(w["Local"].replace("", pd.NA).nunique()),
              "Classificadas": int((w["Situação"] == "Classificada").sum()),
              "Eliminadas": int((w["Status"] == "Eliminada").sum()),
              "Nota média (em classificação)": f"{em.mean():.0f}" if len(em) else "—"}
    _tabela(pdf, pd.DataFrame({"": list(resumo), "Total": [str(v) for v in resumo.values()]}), larguras=(120, 62))

    # ---------------- 2. situação e notas
    _secao(pdf, "Situação e notas")
    sit = w["Situação"].value_counts()
    _tabela(pdf, pd.DataFrame({"Situação": sit.index, "Inscrições": [int(v) for v in sit.values],
                               "%": [rd._pct(v, len(w)) for v in sit.values]}), larguras=(100, 41, 41))
    if len(em):
        fig, ax = plt.subplots(figsize=(8, 2.6))
        ax.hist(em, bins=range(0, 75, 5), color=ROXO, edgecolor="white")
        ax.set_xlabel("Nota", fontsize=8)
        ax.set_ylabel("Inscrições", fontsize=8)
        ax.set_title("Distribuição das notas (em classificação)", fontsize=9, color=ROXO_ESCURO, loc="left")
        _eixo(ax)
        _grafico(pdf, fig, 55)
    elim = rd.tabela_eliminacoes(w)
    if len(elim):
        _sub(pdf, "Motivos de eliminação")
        _tabela(pdf, elim[["Motivo", "Inscrições"]], larguras=(146, 36))

    # ---------------- 3. onde estão
    _secao(pdf, "Onde estão")
    reg = w["Região"].value_counts().reindex([r for r in rd.ORDEM_REGIAO if r in set(w["Região"])])
    _tabela(pdf, pd.DataFrame({"Região": reg.index, "Inscrições": [int(v) for v in reg.values],
                               "%": [rd._pct(v, len(w)) for v in reg.values]}), larguras=(100, 41, 41))
    uf = w["UF"].replace("", pd.NA).dropna().value_counts()
    if len(uf):
        _grafico(pdf, _barras(list(uf.index), [int(v) for v in uf.values], "Inscrições por estado"), 52)
    _sub(pdf, "Cidades com mais inscrições")
    _tabela(pdf, rd.tabela_cidades(w, top=10), larguras=(110, 36, 36))
    tenv = rd.tabela_envios(w)
    if len(tenv):
        _grafico(pdf, _barras([d.strftime("%d/%m") for d in tenv["Data"]], list(tenv["Inscrições"]),
                              "Inscrições por dia de envio"), 50)

    # ---------------- 4. perfil
    _secao(pdf, "Perfil das organizações")
    for chave, titulo in [("p18", "Elaboração — nº de mecanismos que já escreveu"),
                          ("p19", "Execução — nº de mecanismos que já executou")]:
        t = rd.tabela_mecanismos(w, chave)
        if len(t):
            _sub(pdf, titulo)
            _tabela(pdf, t[["Mecanismos", "Inscrições", "%"]], larguras=(100, 41, 41))
    for chave, titulo, ordem in rd.PERFIL:
        t = rd.tabela_perfil(w, chave, ordem)
        if len(t):
            _sub(pdf, titulo.split(" — ")[0])
            _tabela(pdf, t[["Resposta", "Inscrições", "%"]], larguras=(120, 31, 31))
    for tab, titulo in [(rd.tabela_canais(w), "Canais digitais"), (rd.tabela_modalidades(w).head(10),
                                                                    "Modalidades esportivas (10 mais citadas)")]:
        if len(tab):
            _sub(pdf, titulo)
            _tabela(pdf, tab, larguras=(110, 36, 36))

    pdf.ln(3)
    _texto(pdf, "Estados e cidades padronizados pela lista oficial do IBGE (ex.: “BH” e “Belo Horisonte” "
                "contam como Belo Horizonte/MG). Percentuais sobre as inscrições do recorte.", 8)

    return bytes(pdf.output())
