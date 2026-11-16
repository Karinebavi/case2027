# -*- coding: utf-8 -*-
"""
Tela 7 — Relatórios
===================
Relatório técnico das inscrições: filtros em cascata (situação, região, estado,
cidade, nota, tempo de existência, data de envio, equipe e receita), estatística
descritiva, desempenho por bloco da régua, território (com estado e cidade
padronizados pela lista do IBGE), perfil das OSCs, qualidade dos dados e
exportação em PDF. Os números vêm de regras/relatorio_dados.py — a mesma fonte do
PDF, então tela e PDF nunca divergem.
"""
import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import tema
from regras import feedback, geo, pontuacao
from regras import relatorio_dados as rd
from telas import _calculo, _ui

ROXO = tema.PRIMARIA_GRAF
LARANJA = tema.SECUNDARIA_GRAF
SEQ = tema.SEQ_CASE
COR_SITUACAO = tema.SEMAFORO_FORTE
_K = "rel_"  # prefixo das chaves dos filtros
_CONTADOR = [0]


def _fig(fig, altura=320):
    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=36, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(size=12), legend=dict(orientation="h", y=-0.2))
    _CONTADOR[0] += 1
    st.plotly_chart(fig, width="stretch", key=f"rel_g{_CONTADOR[0]}", config={"displayModeBar": False})


def _tabela(df, altura=None, **cfg):
    if df is None or not len(df):
        st.caption("Sem dados neste recorte.")
        return
    conf = {c: st.column_config.NumberColumn(c, format="%.1f") for c in df.columns
            if c.startswith("%") or c in ("Média", "Mediana", "Desvio-padrão", "Nota média")}
    conf.update(cfg)
    st.dataframe(df, hide_index=True, width="stretch", column_config=conf,
                 height=altura or "auto")


# ------------------------------------------------------------------ filtros

def _limpar():
    for k in list(st.session_state):
        if k.startswith(_K):
            del st.session_state[k]


def _so_validos(chave, opcoes):
    """Filtro em cascata: tira da seleção o que deixou de existir (ex.: trocou a região)."""
    if chave in st.session_state:
        st.session_state[chave] = [v for v in st.session_state[chave] if v in opcoes]


def _filtros(w):
    nota_max = 70
    anos_max = int(math.ceil(w["Anos"].max())) if w["Anos"].notna().any() else 50
    datas = [d for d in w["_envio"] if d is not None] if "_envio" in w.columns else []
    envio_lim = (min(datas), max(datas)) if datas else None

    with st.container(border=True):
        c = st.columns(4)
        sit_ops = [s for s in ["Classificada", "Fila de espera", "Eliminada"] if s in set(w["Situação"])]
        _so_validos(_K + "situacao", sit_ops)
        situacao = c[0].multiselect("Situação", sit_ops, key=_K + "situacao", placeholder="Todas")

        reg_ops = [r for r in rd.ORDEM_REGIAO if r in set(w["Região"])]
        _so_validos(_K + "regiao", reg_ops)
        regiao = c[1].multiselect("Região", reg_ops, key=_K + "regiao", placeholder="Todas")

        sub = w[w["Região"].isin(regiao)] if regiao else w
        uf_ops = sorted(u for u in set(sub["UF"]) if u)
        _so_validos(_K + "uf", uf_ops)
        uf = c[2].multiselect("Estado (UF)", uf_ops, key=_K + "uf", placeholder="Todos",
                              help="Já padronizado: “Minas”, “mg” e “Minas Gerias” contam como MG.")

        sub = sub[sub["UF"].isin(uf)] if uf else sub
        cid_ops = sorted(c_ for c_ in set(sub["Local"]) if c_)
        _so_validos(_K + "cidade", cid_ops)
        cidade = c[3].multiselect("Cidade", cid_ops, key=_K + "cidade", placeholder="Todas",
                                  help="Padronizada pela lista do IBGE: “BH” e “Belo Horisonte” "
                                       "contam como Belo Horizonte/MG.")

        c = st.columns(4)
        nota = c[0].slider("Nota", 0, nota_max, (0, nota_max), key=_K + "nota")
        anos = c[1].slider("Tempo de existência (anos)", 0, anos_max, (0, anos_max), key=_K + "anos")
        envio = None
        if envio_lim:
            valor = c[2].date_input("Data de envio", value=envio_lim, min_value=envio_lim[0],
                                    max_value=envio_lim[1], format="DD/MM/YYYY", key=_K + "envio")
            envio = tuple(valor) if isinstance(valor, (list, tuple)) and len(valor) == 2 else None
        eq_ops = [o for o in pontuacao.EQUIPE if o in set(w.get("p21", pd.Series(dtype=str)))]
        _so_validos(_K + "equipe", eq_ops)
        equipe = c[3].multiselect("Equipe (pergunta 24)", eq_ops, key=_K + "equipe", placeholder="Todas")

        c = st.columns([3, 1], vertical_alignment="bottom")
        rec_ops = [o for o in pontuacao.RECEITA if o in set(w.get("p22", pd.Series(dtype=str)))]
        _so_validos(_K + "receita", rec_ops)
        receita = c[0].multiselect("Receita bruta anual (pergunta 25)", rec_ops, key=_K + "receita",
                                   placeholder="Todas")
        c[1].button("Limpar filtros", icon=":material/filter_alt_off:", on_click=_limpar, width="stretch")

    f = {"situacao": situacao, "regiao": regiao, "uf": uf, "cidade": cidade, "equipe": equipe,
         "receita": receita, "nota": nota, "anos": anos, "envio": envio}
    return f, rd.descrever_filtros(f, nota_max, anos_max, envio_lim)


# ------------------------------------------------------------------ PDF

def _exportar(w, filtros, texto, total):
    assinatura = (texto, len(w), float(w["Nota"].sum()) if len(w) else 0.0)
    pronto = st.session_state.get("_rel_pdf")
    if pronto and pronto[0] == assinatura:
        st.download_button("Baixar PDF", pronto[1], file_name="CASE2027_relatorio_inscricoes.pdf",
                           mime="application/pdf", icon=":material/download:", type="primary",
                           width="stretch")
    elif st.button("Gerar PDF", icon=":material/picture_as_pdf:", type="primary", width="stretch",
                   help="Relatório técnico do recorte filtrado, sem nomes nem contatos."):
        from regras import relatorio_pdf
        with st.spinner("Montando o PDF…"):
            st.session_state["_rel_pdf"] = (assinatura, relatorio_pdf.gerar(w, texto, total))
        st.rerun()


# ------------------------------------------------------------------ tela

def mostrar():
    _ui.cabecalho(7, "Relatório técnico das inscrições: filtre, confira os números e exporte em PDF.")
    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok") or not len(dados):
        st.info("Ainda não há inscrições. Elas chegam sozinhas do Wix na etapa Inscrições.")
        return

    _CONTADOR[0] = 0
    vagas = int(st.session_state.get("vagas", 10))
    scored = _calculo.processar(dados, st.session_state["mapa"], vagas)
    w_total = rd.montar_base(dados, scored)

    filtros, texto = _filtros(w_total)
    w = rd.aplicar_filtros(w_total, filtros)

    c = st.columns([3, 1], vertical_alignment="center")
    c[0].markdown(f"**{len(w)} de {len(w_total)} inscrições** · Filtros: {texto}")
    if len(w):
        with c[1]:
            _exportar(w, filtros, texto, len(w_total))
    if not len(w):
        st.warning("Nenhuma inscrição com esses filtros.")
        return

    abas = st.tabs(["Resumo", "Notas", "Território", "Perfil das OSCs", "Qualidade dos dados"])
    with abas[0]:
        _resumo(w)
    with abas[1]:
        _notas(w)
    with abas[2]:
        _territorio(w)
    with abas[3]:
        _perfil(w)
    with abas[4]:
        _qualidade(w)
    st.caption(rd.METODOLOGIA)
    _feedback_equipe()


def _resumo(w):
    r = rd.resumo(w)
    c = st.columns(4)
    c[0].metric("Inscrições", r["Inscrições"])
    c[1].metric("Estados · municípios", f"{r['Estados (UF)']} · {r['Municípios']}")
    br = lambda v: str(v).replace(".", ",")  # noqa: E731
    c[2].metric("Eliminadas", r["Eliminadas"], f"{br(r['Taxa de eliminação (%)'])}% do recorte",
                delta_color="off", delta_arrow="off")
    c[3].metric("Nota média (em classificação)", br(r["Nota média (em classificação)"]),
                f"mediana {br(r['Nota mediana (em classificação)'])} · desvio {br(r['Desvio-padrão da nota'])}",
                delta_color="off", delta_arrow="off")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Situação")
        cont = w["Situação"].value_counts()
        fig = go.Figure(go.Pie(labels=cont.index, values=cont.values, hole=0.55, textinfo="label+value+percent",
                               marker=dict(colors=[COR_SITUACAO.get(s, "#888") for s in cont.index])))
        fig.update_layout(showlegend=False)
        _fig(fig)
    with col2:
        st.subheader("Motivos de eliminação")
        _tabela(rd.tabela_eliminacoes(w))
    tenv = rd.tabela_envios(w)
    if len(tenv):
        st.subheader("Inscrições por dia de envio")
        fig = go.Figure()
        fig.add_bar(x=tenv["Data"], y=tenv["Inscrições"], name="Por dia", marker_color=ROXO)
        fig.add_scatter(x=tenv["Data"], y=tenv["Acumulado"], name="Acumulado", yaxis="y2",
                        line=dict(color=LARANJA, width=2))
        fig.update_layout(yaxis=dict(title="Por dia"), yaxis2=dict(title="Acumulado", overlaying="y", side="right"))
        _fig(fig, 300)


def _notas(w):
    col1, col2 = st.columns([2, 3])
    with col1:
        st.subheader("Estatística descritiva")
        _tabela(rd.tabela_notas(w))
    with col2:
        st.subheader("Distribuição (em classificação)")
        em = w[w["Situação"].isin(rd.EM_CLASSIFICACAO)]["Nota"].dropna()
        if len(em):
            fig = px.histogram(x=em, nbins=14, range_x=[0, 70], color_discrete_sequence=[ROXO])
            fig.add_vline(x=em.mean(), line_color=LARANJA, annotation_text=f"média {em.mean():.1f}")
            fig.add_vline(x=em.median(), line_dash="dash", line_color=tema.ROXO_ESCURO,
                          annotation_text=f"mediana {em.median():.1f}", annotation_position="bottom right")
            fig.update_layout(xaxis_title="Nota", yaxis_title="Inscrições", bargap=0.05)
            _fig(fig)
        else:
            st.caption("Nenhuma inscrição em classificação neste recorte.")
    st.subheader("Desempenho por bloco da régua (0 a 10 cada)")
    tb = rd.tabela_blocos(w)
    col1, col2 = st.columns([3, 2])
    with col1:
        _tabela(tb)
    with col2:
        if len(tb):
            fig = px.bar(tb, x="Média", y="Bloco", orientation="h", range_x=[0, 10], text="Média",
                         color_discrete_sequence=[ROXO])
            fig.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis_title="Média")
            _fig(fig, 300)
    if w["Região"].nunique() > 1:
        st.subheader("Nota por região")
        em = w[w["Situação"].isin(rd.EM_CLASSIFICACAO)]
        fig = px.box(em, x="Região", y="Nota", points="all", color_discrete_sequence=[ROXO],
                     category_orders={"Região": rd.ORDEM_REGIAO})
        fig.update_layout(yaxis_range=[0, 70])
        _fig(fig, 320)


def _territorio(w):
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Mapa por estado")
        gj = geo.carregar_geojson()
        cont = w["UF"].value_counts()
        dfu = pd.DataFrame({"UF": list(geo.UF_NOME)})
        dfu["Estado"] = dfu["UF"].map(geo.UF_NOME)
        dfu["Inscrições"] = dfu["UF"].map(cont).fillna(0).astype(int)
        if gj is not None:
            fig = px.choropleth(dfu, geojson=gj, locations="UF", featureidkey="properties.sigla",
                                color="Inscrições", color_continuous_scale=tema.ESCALA_ROXO,
                                hover_name="Estado", hover_data={"UF": False, "Inscrições": True})
            fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
            fig.update_traces(marker_line_color="#FFFFFF", marker_line_width=0.6)
            fig.update_layout(height=460, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                              dragmode=False)
            st.plotly_chart(fig, width="stretch", key="rel_mapa",
                            config={"displayModeBar": False, "scrollZoom": False})
    with col2:
        st.subheader("Por região")
        _tabela(rd.tabela_territorio(w, "Região"))
    st.subheader("Por estado (UF)")
    _tabela(rd.tabela_territorio(w, "UF"))
    st.subheader("Municípios com mais inscrições")
    st.caption("Cidades padronizadas pela lista oficial do IBGE: grafias diferentes da mesma cidade contam juntas.")
    _tabela(rd.tabela_cidades(w, top=30))


def _perfil(w):
    col1, col2 = st.columns(2)
    for col, (chave, titulo) in zip((col1, col2), [("p18", "Elaboração com incentivo (pergunta 21)"),
                                                   ("p19", "Execução com incentivo (pergunta 22)")]):
        with col:
            st.subheader(titulo)
            _tabela(rd.tabela_mecanismos(w, chave))
    for chave, titulo, ordem in rd.PERFIL:
        t = rd.tabela_perfil(w, chave, ordem)
        if len(t):
            st.subheader(titulo)
            _tabela(t, **{"%": st.column_config.ProgressColumn("%", min_value=0, max_value=100, format="%.1f%%")})
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Canais digitais (pergunta 28)")
        _tabela(rd.tabela_canais(w))
    with col2:
        st.subheader("Modalidades esportivas (pergunta 31)")
        _tabela(rd.tabela_modalidades(w), altura=320)


def _qualidade(w):
    st.subheader("Estado e cidade")
    st.caption("O sistema padroniza o que foi digitado pela lista oficial de municípios do IBGE. "
               "“Corrigida”: erro de digitação, abreviação ou apelido resolvido com segurança. "
               "“A conferir”: o sistema não decide sozinho — veja a observação. O texto original "
               "continua guardado na base.")
    _tabela(rd.tabela_qualidade(w))
    tcor = rd.tabela_correcoes(w)
    if len(tcor):
        st.subheader("Correções e pontos a conferir")
        _tabela(tcor)
    else:
        st.success("Todos os estados e cidades deste recorte conferem com a lista do IBGE.")
    _alertas(w)


def _alertas(w):
    st.subheader("Respostas que a régua não reconhece")
    st.caption("Viram nota zero no bloco. Se aparecerem muitas, confira o texto das opções no formulário.")
    linhas = []
    for chave, nome, tabela in [("p21", "24. Equipe", pontuacao.EQUIPE), ("p22", "25. Receita", pontuacao.RECEITA),
                                ("p23", "26. Infra administrativa", pontuacao.INFRA_ADMIN),
                                ("p24", "27. Infra esportiva", pontuacao.INFRA_ESP)]:
        if chave not in w.columns:
            continue
        s = w[chave].astype(str).str.strip()
        nao = s[(s != "") & ~s.isin(tabela.keys())]
        if len(nao):
            linhas.append({"Pergunta": nome, "Não reconhecidas": len(nao),
                           "Exemplos": ", ".join(sorted(nao.unique())[:3])})
    if linhas:
        _tabela(pd.DataFrame(linhas))
    else:
        st.success("Todas as respostas das perguntas de nota foram reconhecidas.")


def _feedback_equipe():
    itens = feedback.listar(50)
    with st.expander(f"Feedback da equipe ({len(itens)})"):
        if not itens:
            st.caption("Ainda não há feedback. Os mentores enviam pela caixa na barra lateral.")
            return
        for it in itens:
            cab = " · ".join([x for x in [it.get("data", ""), it.get("autor", ""), it.get("tela", "")] if x])
            st.markdown(f"**{cab}**" if cab else "**Feedback**")
            st.write(it.get("texto", ""))
