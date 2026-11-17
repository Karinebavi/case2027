# -*- coding: utf-8 -*-
"""
Tela 7 — Relatórios
===================
Visão geral das inscrições numa página só, em gráficos: situação, notas, regiões,
mapa do Brasil, dias com mais inscrições, cidades e o perfil das OSCs.
Filtros no topo (os principais à vista, o resto em "Mais filtros") e exportação em
PDF do que estiver filtrado. Estado e cidade já vêm padronizados pela lista do IBGE
(regras/localidade.py): "BH" e "Belo Horisonte" contam como Belo Horizonte/MG.
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

AZUL = tema.PRIMARIA_GRAF
DOURADO = tema.SECUNDARIA_GRAF
SEQ = tema.SEQ_CASE
COR_SITUACAO = tema.SEMAFORO_FORTE
_K = "rel_"  # prefixo das chaves dos filtros
_CONTADOR = [0]


def _fig(fig, altura=340):
    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=40, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(size=13), legend=dict(orientation="h", y=-0.15))
    _CONTADOR[0] += 1
    st.plotly_chart(fig, width="stretch", key=f"rel_g{_CONTADOR[0]}", config={"displayModeBar": False})


def _contagem(serie, ordem=None):
    s = serie.astype(str).str.strip()
    c = s[s != ""].value_counts()
    if ordem:
        c = c.reindex([o for o in ordem if o in c.index]).dropna()
    return c


# ------------------------------------------------------------------ filtros

def _limpar():
    for k in list(st.session_state):
        if k.startswith(_K):
            del st.session_state[k]


def _so_validos(chave, opcoes):
    """Filtro em cascata: tira da seleção o que deixou de existir (ex.: trocou a região)."""
    if chave in st.session_state:
        st.session_state[chave] = [v for v in st.session_state[chave] if v in opcoes]


def _multi(onde, rotulo, opcoes, chave, vazio="Todas", ajuda=None):
    _so_validos(_K + chave, opcoes)
    return onde.multiselect(rotulo, opcoes, key=_K + chave, placeholder=vazio, help=ajuda)


def _filtros(w):
    anos_max = int(math.ceil(w["Anos"].max())) if w["Anos"].notna().any() else 50
    datas = [d for d in w["_envio"] if d is not None] if "_envio" in w.columns else []
    envio_lim = (min(datas), max(datas)) if datas else None

    c = st.columns([1, 1, 1, 1, 0.9], vertical_alignment="bottom")
    situacao = _multi(c[0], "Situação", [s for s in ["Classificada", "Fila de espera", "Eliminada"]
                                         if s in set(w["Situação"])], "situacao")
    regiao = _multi(c[1], "Região", [r for r in rd.ORDEM_REGIAO if r in set(w["Região"])], "regiao")
    sub = w[w["Região"].isin(regiao)] if regiao else w
    uf = _multi(c[2], "Estado", sorted(u for u in set(sub["UF"]) if u), "uf", "Todos")
    sub = sub[sub["UF"].isin(uf)] if uf else sub
    cidade = _multi(c[3], "Cidade", sorted(x for x in set(sub["Local"]) if x), "cidade",
                    ajuda="Cidades corrigidas pela lista do IBGE: “BH” e “Belo Horisonte” "
                          "contam como Belo Horizonte/MG.")
    with c[4].popover("Mais filtros", icon=":material/tune:", width="stretch"):
        nota = st.slider("Nota", 0, 70, (0, 70), key=_K + "nota")
        anos = st.slider("Tempo de existência (anos)", 0, anos_max, (0, anos_max), key=_K + "anos")
        envio = None
        if envio_lim:
            v = st.date_input("Data de envio", value=envio_lim, min_value=envio_lim[0],
                              max_value=envio_lim[1], format="DD/MM/YYYY", key=_K + "envio")
            envio = tuple(v) if isinstance(v, (list, tuple)) and len(v) == 2 else None
        equipe = _multi(st, "Equipe", [o for o in pontuacao.EQUIPE if o in set(w.get("p21", []))], "equipe")
        receita = _multi(st, "Receita bruta anual", [o for o in pontuacao.RECEITA if o in set(w.get("p22", []))],
                         "receita")
        st.button("Limpar filtros", icon=":material/filter_alt_off:", on_click=_limpar, width="stretch")

    f = {"situacao": situacao, "regiao": regiao, "uf": uf, "cidade": cidade, "equipe": equipe,
         "receita": receita, "nota": nota, "anos": anos, "envio": envio}
    return f, rd.descrever_filtros(f, 70, anos_max, envio_lim)


def _exportar(w, texto, total):
    assinatura = (texto, len(w), float(w["Nota"].sum()) if len(w) else 0.0)
    pronto = st.session_state.get("_rel_pdf")
    if pronto and pronto[0] == assinatura:
        st.download_button("Baixar PDF", pronto[1], file_name="CASE2027_relatorio_inscricoes.pdf",
                           mime="application/pdf", icon=":material/download:", type="primary", width="stretch")
    elif st.button("Gerar PDF", icon=":material/picture_as_pdf:", type="primary", width="stretch",
                   help="O relatório do que está filtrado, sem nomes nem contatos."):
        from regras import relatorio_pdf
        with st.spinner("Montando o PDF…"):
            st.session_state["_rel_pdf"] = (assinatura, relatorio_pdf.gerar(w, texto, total))
        st.rerun()


# ------------------------------------------------------------------ tela

def mostrar():
    _ui.cabecalho(7, "A visão geral das inscrições em gráficos. Filtre e baixe em PDF.")
    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok") or not len(dados):
        st.info("Ainda não há inscrições. Elas chegam sozinhas do Wix na etapa Inscrições.")
        return

    _CONTADOR[0] = 0
    vagas = int(st.session_state.get("vagas", 10))
    w_total = rd.montar_base(dados, _calculo.processar(dados, st.session_state["mapa"], vagas))
    filtros, texto = _filtros(w_total)
    work = rd.aplicar_filtros(w_total, filtros)

    c = st.columns([4, 1], vertical_alignment="center")
    c[0].caption(f"{len(work)} de {len(w_total)} inscrições"
                 + ("" if texto.startswith("nenhum") else f" · {texto}"))
    if not len(work):
        st.warning("Nada para mostrar com esses filtros.")
        return
    with c[1]:
        _exportar(work, texto, len(w_total))

    _kpis(work)
    _situacao_e_notas(work)
    _regioes(work)
    _mapa(work)
    _tempo_e_cidades(work)
    _perfil_oscs(work)
    st.divider()
    _cidades_corrigidas(work)
    _alertas(work)
    _feedback_equipe()


def _kpis(work):
    em_class = work[work["Situação"].isin(rd.EM_CLASSIFICACAO)]
    c = st.columns(5)
    c[0].metric("Inscrições", len(work))
    c[1].metric("Estados", work["UF"].replace("", pd.NA).nunique())
    c[2].metric("Cidades", work["Local"].replace("", pd.NA).nunique())
    c[3].metric("Classificadas", int((work["Situação"] == "Classificada").sum()))
    media = em_class["Nota"].mean()
    c[4].metric("Nota média (em classificação)", f"{media:.0f}" if pd.notna(media) else "—")


def _situacao_e_notas(work):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Situação das inscrições")
        cont = _contagem(work["Situação"])
        fig = go.Figure(go.Pie(labels=cont.index, values=cont.values, hole=0.55, textinfo="label+value",
                               marker=dict(colors=[COR_SITUACAO.get(s, "#888") for s in cont.index])))
        _fig(fig)
    with col2:
        st.subheader("Distribuição das notas (em classificação)")
        notas = work.loc[work["Situação"].isin(rd.EM_CLASSIFICACAO), "Nota"].dropna()
        if len(notas):
            fig = px.histogram(x=notas, nbins=20, color_discrete_sequence=[AZUL])
            fig.update_layout(xaxis_title="Nota", yaxis_title="Inscrições", showlegend=False)
            _fig(fig)
        else:
            st.caption("Sem inscrições em classificação.")


def _regioes(work):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Inscrições por região")
        cont = _contagem(work["Região"], rd.ORDEM_REGIAO)
        fig = px.bar(x=cont.values, y=cont.index, orientation="h", color=cont.index, color_discrete_sequence=SEQ)
        fig.update_layout(xaxis_title="Inscrições", yaxis_title="", showlegend=False)
        _fig(fig)
    with col2:
        st.subheader("Inscrições por estado")
        cont = _contagem(work["UF"]).sort_values(ascending=False)
        fig = px.bar(x=cont.index, y=cont.values, color_discrete_sequence=[AZUL])
        fig.update_layout(xaxis_title="", yaxis_title="Inscrições")
        _fig(fig)


def _mapa(work):
    st.subheader("Mapa do Brasil — inscrições por estado")
    gj = geo.carregar_geojson()
    if gj is None:
        st.caption("Mapa indisponível (GeoJSON não encontrado).")
        return
    cont = _contagem(work["UF"])
    dfu = pd.DataFrame({"UF": list(geo.UF_NOME)})
    dfu["Estado"] = dfu["UF"].map(geo.UF_NOME)
    dfu["Inscrições"] = dfu["UF"].map(cont).fillna(0).astype(int)
    fig = px.choropleth(dfu, geojson=gj, locations="UF", featureidkey="properties.sigla", color="Inscrições",
                        color_continuous_scale=tema.ESCALA_ROXO, hover_name="Estado",
                        hover_data={"UF": False, "Inscrições": True})
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig.update_traces(marker_line_color="#FFFFFF", marker_line_width=0.6)
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      coloraxis_colorbar=dict(title="Inscrições"), dragmode=False)
    st.plotly_chart(fig, width="stretch", key="rel_mapa", config={"displayModeBar": False, "scrollZoom": False})


def _tempo_e_cidades(work):
    st.subheader("Dias com mais inscrições")
    datas = pd.Series([d for d in work.get("_envio", []) if d is not None])
    if len(datas):
        pordia = datas.value_counts().sort_index()
        fig = px.bar(x=pordia.index, y=pordia.values, color_discrete_sequence=[AZUL])
        fig.update_layout(xaxis_title="Data de envio", yaxis_title="Inscrições")
        _fig(fig, altura=300)
    else:
        st.caption("Sem datas de envio reconhecidas.")

    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Nuvem de cidades")
        arr = _wordcloud(_contagem(work["Cidade"]).to_dict())
        if arr is not None:
            st.image(arr, width="stretch")
        else:
            st.caption("Sem cidades para exibir.")
    with col2:
        st.subheader("Cidades mais frequentes")
        cont = _contagem(work["Local"]).head(12)
        if len(cont):
            fig = px.bar(x=cont.values, y=cont.index, orientation="h", color_discrete_sequence=[DOURADO])
            fig.update_layout(xaxis_title="Inscrições", yaxis_title="", yaxis=dict(autorange="reversed"))
            _fig(fig, altura=380)
        else:
            st.caption("Sem cidades.")


def _perfil_oscs(work):
    st.subheader("Perfil das OSCs")
    st.caption("Cada pergunta da inscrição em um gráfico.")
    col1, col2 = st.columns(2)
    with col1:
        _grafico_categorico(work, "p21", "Equipe (nº de pessoas)", ordem=list(pontuacao.EQUIPE))
    with col2:
        _grafico_categorico(work, "p22", "Receita bruta anual", ordem=list(pontuacao.RECEITA), horizontal=True)
    col3, col4 = st.columns(2)
    with col3:
        _grafico_categorico(work, "p23", "Infraestrutura administrativa", ordem=list(pontuacao.INFRA_ADMIN),
                            tipo="pie")
    with col4:
        _grafico_categorico(work, "p24", "Infraestrutura esportiva", ordem=list(pontuacao.INFRA_ESP), tipo="pie")
    col5, col6 = st.columns(2)
    with col5:
        _grafico_mecanismos(work, "p18", "Elaboração — nº de mecanismos que já escreveu")
    with col6:
        _grafico_mecanismos(work, "p19", "Execução — nº de mecanismos que já executou")
    col7, col8 = st.columns(2)
    with col7:
        st.markdown("**Canais digitais**")
        t = rd.tabela_canais(work)
        if len(t):
            fig = px.bar(t, x="Canal", y="Inscrições", color="Canal", color_discrete_sequence=SEQ)
            fig.update_layout(xaxis_title="", showlegend=False)
            _fig(fig)
        else:
            st.caption("Sem respostas.")
    with col8:
        if "p20_lie" in work.columns and (work["p20_lie"].astype(str).str.strip() != "").any():
            _grafico_categorico(work, "p20_lie", "Situação na Lei de Incentivo (LIE)", tipo="pie")
    st.markdown("**Modalidades esportivas**")
    t = rd.tabela_modalidades(work)
    arr = _wordcloud(dict(zip(t["Modalidade"], t["Inscrições"]))) if len(t) else None
    if arr is not None:
        st.image(arr, width="stretch")
    else:
        st.caption("Sem modalidades informadas.")


def _grafico_categorico(work, chave, titulo, ordem=None, tipo="bar", horizontal=False):
    st.markdown(f"**{titulo}**")
    if chave not in work.columns:
        st.caption("Pergunta não encontrada na base.")
        return
    cont = _contagem(work[chave], ordem=ordem)
    if not len(cont):
        st.caption("Sem respostas.")
        return
    if tipo == "pie":
        fig = go.Figure(go.Pie(labels=cont.index, values=cont.values, hole=0.4, marker=dict(colors=SEQ),
                               textinfo="percent+value"))
    elif horizontal:
        fig = px.bar(x=cont.values, y=cont.index, orientation="h", color_discrete_sequence=[AZUL])
        fig.update_layout(xaxis_title="Entidades", yaxis_title="", yaxis=dict(autorange="reversed"))
    else:
        fig = px.bar(x=cont.index, y=cont.values, color_discrete_sequence=[AZUL])
        fig.update_layout(xaxis_title="", yaxis_title="Entidades")
    _fig(fig)


def _grafico_mecanismos(work, chave, titulo):
    st.markdown(f"**{titulo}**")
    t = rd.tabela_mecanismos(work, chave)
    if not len(t):
        st.caption("Sem respostas.")
        return
    fig = px.bar(t, x="Mecanismos", y="Inscrições", color_discrete_sequence=[DOURADO])
    fig.update_layout(xaxis_title="Nº de mecanismos", yaxis_title="Entidades")
    _fig(fig)


def _cidades_corrigidas(work):
    t = rd.tabela_correcoes(work)
    if not len(t):
        return
    conferir = int(t.loc[t["Situação"] != "corrigida", "Inscrições"].sum())
    titulo = f"Cidades e estados corrigidos ({int(t['Inscrições'].sum())})"
    if conferir:
        titulo += f" · {conferir} a conferir"
    with st.expander(titulo):
        st.caption("Escritos de outro jeito na inscrição e padronizados pela lista do IBGE. "
                   "“A conferir”: o sistema não decidiu sozinho — veja a observação.")
        st.dataframe(t, hide_index=True, width="stretch")


def _alertas(work):
    linhas = []
    for chave, nome, tabela in [("p21", "Equipe", pontuacao.EQUIPE), ("p22", "Receita", pontuacao.RECEITA),
                                ("p23", "Infra administrativa", pontuacao.INFRA_ADMIN),
                                ("p24", "Infra esportiva", pontuacao.INFRA_ESP)]:
        if chave not in work.columns:
            continue
        s = work[chave].astype(str).str.strip()
        nao = s[(s != "") & ~s.isin(tabela.keys())]
        if len(nao):
            linhas.append({"Pergunta": nome, "Não reconhecidas": len(nao),
                           "Exemplos": ", ".join(sorted(nao.unique())[:3])})
    if linhas:
        with st.expander(f"Respostas que a régua não reconhece ({sum(x['Não reconhecidas'] for x in linhas)})"):
            st.caption("Viram nota zero no bloco. Se aparecerem muitas, confira o texto das opções no formulário.")
            st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)


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


def _wordcloud(freqs):
    freqs = {k: v for k, v in (freqs or {}).items() if str(k).strip()}
    if not freqs:
        return None
    from wordcloud import WordCloud
    wc = WordCloud(width=900, height=360, background_color="white", colormap="Purples",
                   prefer_horizontal=0.9, collocations=False)
    wc.generate_from_frequencies(freqs)
    return wc.to_array()
