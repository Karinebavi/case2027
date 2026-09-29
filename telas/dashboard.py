# -*- coding: utf-8 -*-
"""
Tela 5 — Dashboard
==================
Visão completa das inscrições em gráficos: situação, notas, regiões, mapa do
Brasil, dias com mais inscrições, nuvem de cidades e o perfil das OSCs
(uma resposta de cada pergunta vira um gráfico). Dá para ver todas ou só as
melhores do ranking.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from telas import _calculo, _ui
from regras import pontuacao, geo
from regras.memoria import so_digitos

AZUL = "#1F4E79"
DOURADO = "#B0863B"
SEQ = ["#1F4E79", "#3B6EA5", "#6FA8DC", "#B0863B", "#8FB08C", "#9E9E9E", "#C46B6B"]
COR_SITUACAO = {
    "Classificada": "#2E7D32", "Fila de espera": "#C99A2E",
    "Fora do perfil": "#9E9E9E", "Inelegível": "#B84A4A",
}


_CONTADOR = [0]


def _fig(fig, altura=340):
    fig.update_layout(
        height=altura, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13), legend=dict(orientation="h", y=-0.15),
    )
    _CONTADOR[0] += 1
    st.plotly_chart(fig, use_container_width=True, key=f"g{_CONTADOR[0]}")


def _contagem(serie, ordem=None, remover_vazio=True):
    s = serie.astype(str).str.strip()
    if remover_vazio:
        s = s[s != ""]
    c = s.value_counts()
    if ordem:
        c = c.reindex([o for o in ordem if o in c.index]).dropna()
    return c


def mostrar():
    st.title("7 · Dashboard")
    _ui.cabecalho()

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para ver o dashboard.")
        return

    _CONTADOR[0] = 0
    mapa = st.session_state["mapa"]
    vagas = int(st.session_state.get("vagas", 10))
    scored = _calculo.processar(dados, mapa, vagas)

    # frame de trabalho: respostas (base) + situação/nota (scored), casados por CNPJ
    base = dados.copy()
    base["_dig"] = base["cnpj"].map(so_digitos) if "cnpj" in base.columns else ""
    info = scored.copy()
    info["_dig"] = info["CNPJ"].map(so_digitos)
    work = base.merge(
        info[["_dig", "Situação", "Nota", "UF", "Região", "Posição", "Anos"]],
        on="_dig", how="left",
    )

    # Filtro: todas x só as melhores
    modo = st.radio(
        "Ver", ["Todas as inscrições", f"Só as {vagas} melhores (dentro do corte)"],
        horizontal=True, label_visibility="collapsed",
    )
    if modo.startswith("Só"):
        work = work[work["Situação"] == "Classificada"]
    if len(work) == 0:
        st.warning("Nada para mostrar com esse filtro.")
        return

    _kpis(work)
    st.divider()
    _situacao_e_notas(work)
    st.divider()
    _regioes(work)
    st.divider()
    _mapa(work)
    st.divider()
    _tempo_e_cidades(work)
    st.divider()
    _perfil_oscs(work)
    st.divider()
    _alertas(work)


def _kpis(work):
    cidades = work["cidade"].astype(str).str.strip() if "cidade" in work.columns else pd.Series([], dtype=str)
    notas = pd.to_numeric(work["Nota"], errors="coerce")
    em_class = work[work["Situação"].isin(["Classificada", "Fila de espera"])]
    c = st.columns(5)
    c[0].metric("Inscrições", len(work))
    c[1].metric("Estados", work["UF"].nunique())
    c[2].metric("Cidades", cidades[cidades != ""].nunique())
    c[3].metric("Classificadas", int((work["Situação"] == "Classificada").sum()))
    media = pd.to_numeric(em_class["Nota"], errors="coerce").mean()
    c[4].metric("Nota média (em classificação)", f"{media:.0f}" if pd.notna(media) else "—")


def _situacao_e_notas(work):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Situação das inscrições")
        cont = _contagem(work["Situação"])
        fig = go.Figure(go.Pie(
            labels=cont.index, values=cont.values, hole=0.55,
            marker=dict(colors=[COR_SITUACAO.get(s, "#888") for s in cont.index]),
            textinfo="label+value",
        ))
        _fig(fig)
    with col2:
        st.subheader("Distribuição das notas (em classificação)")
        em = work[work["Situação"].isin(["Classificada", "Fila de espera"])]
        notas = pd.to_numeric(em["Nota"], errors="coerce").dropna()
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
        cont = _contagem(work["Região"])
        fig = px.bar(x=cont.values, y=cont.index, orientation="h",
                     color=cont.index, color_discrete_sequence=SEQ)
        fig.update_layout(xaxis_title="Inscrições", yaxis_title="", showlegend=False)
        _fig(fig)
    with col2:
        st.subheader("Inscrições por estado (UF)")
        cont = _contagem(work["UF"]).sort_values(ascending=False)
        fig = px.bar(x=cont.index, y=cont.values, color_discrete_sequence=[AZUL])
        fig.update_layout(xaxis_title="", yaxis_title="Inscrições")
        _fig(fig)


def _mapa(work):
    st.subheader("Mapa do Brasil — inscrições por estado")
    gj = geo.carregar_geojson()
    cont = _contagem(work["UF"])
    dfu = pd.DataFrame({"UF": list(geo.UF_NOME.keys())})
    dfu["Estado"] = dfu["UF"].map(geo.UF_NOME)
    dfu["Inscrições"] = dfu["UF"].map(cont).fillna(0).astype(int)
    if gj is None:
        st.caption("Mapa indisponível (GeoJSON não encontrado).")
        return
    fig = px.choropleth(
        dfu, geojson=gj, locations="UF", featureidkey="properties.sigla",
        color="Inscrições", color_continuous_scale="Blues",
        hover_name="Estado", hover_data={"UF": False, "Inscrições": True},
    )
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig.update_traces(marker_line_color="#FFFFFF", marker_line_width=0.6)
    fig.update_layout(
        height=560, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(title="Inscrições"),
        dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, key="mapa_uf",
                    config={"displayModeBar": False, "scrollZoom": False})


def _tempo_e_cidades(work):
    st.subheader("Dias com mais inscrições")
    if "data_envio" in work.columns:
        datas = work["data_envio"].map(pontuacao.parse_data)
        datas = pd.Series([d for d in datas if d is not None])
        if len(datas):
            pordia = datas.value_counts().sort_index()
            fig = px.bar(x=pordia.index, y=pordia.values, color_discrete_sequence=[AZUL])
            fig.update_layout(xaxis_title="Data de envio", yaxis_title="Inscrições")
            _fig(fig, altura=300)
        else:
            st.caption("Sem datas de envio reconhecidas na base.")
    else:
        st.caption("A base não tem a coluna de data de envio.")

    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Nuvem de cidades")
        freqs = _contagem(work["cidade"]).to_dict() if "cidade" in work.columns else {}
        arr = _wordcloud(freqs)
        if arr is not None:
            st.image(arr, use_container_width=True)
        else:
            st.caption("Sem cidades para exibir.")
    with col2:
        st.subheader("Cidades mais frequentes")
        cont = _contagem(work["cidade"]).head(12) if "cidade" in work.columns else pd.Series(dtype=int)
        if len(cont):
            fig = px.bar(x=cont.values, y=cont.index, orientation="h", color_discrete_sequence=[DOURADO])
            fig.update_layout(xaxis_title="Inscrições", yaxis_title="",
                              yaxis=dict(autorange="reversed"))
            _fig(fig, altura=380)
        else:
            st.caption("Sem cidades.")


def _perfil_oscs(work):
    st.subheader("Perfil das OSCs")
    st.caption("Cada pergunta da inscrição em um gráfico.")

    col1, col2 = st.columns(2)
    with col1:
        _grafico_categorico(work, "p21", "Equipe (nº de pessoas)",
                            ordem=list(pontuacao.EQUIPE.keys()), tipo="bar")
    with col2:
        _grafico_categorico(work, "p22", "Receita bruta anual",
                            ordem=list(pontuacao.RECEITA.keys()), tipo="bar", horizontal=True)

    col3, col4 = st.columns(2)
    with col3:
        _grafico_categorico(work, "p23", "Infraestrutura administrativa",
                            ordem=list(pontuacao.INFRA_ADMIN.keys()), tipo="pie")
    with col4:
        _grafico_categorico(work, "p24", "Infraestrutura esportiva",
                            ordem=list(pontuacao.INFRA_ESP.keys()), tipo="pie")

    col5, col6 = st.columns(2)
    with col5:
        _grafico_mecanismos(work, "p18", "Elaboração — nº de mecanismos que já escreveu")
    with col6:
        _grafico_mecanismos(work, "p19", "Execução — nº de mecanismos que já executou")

    col7, col8 = st.columns(2)
    with col7:
        st.markdown("**Presença digital**")
        rotulos = {"site": "Site", "instagram": "Instagram", "facebook": "Facebook", "outra_rede": "Outra rede"}
        contagem = {}
        for ch, rot in rotulos.items():
            if ch in work.columns:
                contagem[rot] = int((work[ch].astype(str).str.strip() != "").sum())
        if contagem:
            fig = px.bar(x=list(contagem.keys()), y=list(contagem.values()),
                         color=list(contagem.keys()), color_discrete_sequence=SEQ)
            fig.update_layout(xaxis_title="", yaxis_title="Entidades", showlegend=False)
            _fig(fig)
    with col8:
        if "p20_lie" in work.columns and (work["p20_lie"].astype(str).str.strip() != "").any():
            _grafico_categorico(work, "p20_lie", "Situação na Lei de Incentivo (LIE)", tipo="pie")
        else:
            st.markdown("**Modalidades esportivas**")
            freqs = _freq_tokens(work["modalidades"]) if "modalidades" in work.columns else {}
            arr = _wordcloud(freqs)
            if arr is not None:
                st.image(arr, use_container_width=True)
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
        fig = go.Figure(go.Pie(labels=cont.index, values=cont.values, hole=0.4,
                               marker=dict(colors=SEQ), textinfo="percent+value"))
    elif horizontal:
        fig = px.bar(x=cont.values, y=cont.index, orientation="h", color_discrete_sequence=[AZUL])
        fig.update_layout(xaxis_title="Entidades", yaxis_title="", yaxis=dict(autorange="reversed"))
    else:
        fig = px.bar(x=cont.index, y=cont.values, color_discrete_sequence=[AZUL])
        fig.update_layout(xaxis_title="", yaxis_title="Entidades")
    _fig(fig)


def _grafico_mecanismos(work, chave, titulo):
    st.markdown(f"**{titulo}**")
    if chave not in work.columns:
        st.caption("Pergunta não encontrada na base.")
        return
    def faixa(v):
        n = pontuacao._conta_mecanismos(v)
        return "3 ou mais" if n >= 3 else str(n)
    cont = work[chave].map(faixa).value_counts().reindex(["0", "1", "2", "3 ou mais"]).dropna()
    if not len(cont):
        st.caption("Sem respostas.")
        return
    fig = px.bar(x=cont.index, y=cont.values, color_discrete_sequence=[DOURADO])
    fig.update_layout(xaxis_title="Nº de mecanismos", yaxis_title="Entidades")
    _fig(fig)


def _alertas(work):
    st.subheader("Respostas não reconhecidas na régua")
    st.caption("Respostas que não batem com as opções da pontuação (viram nota zero no bloco). "
               "Se aparecerem muitas, vale conferir o texto das opções no formulário.")
    checagem = [
        ("p21", "Equipe", pontuacao.EQUIPE),
        ("p22", "Receita", pontuacao.RECEITA),
        ("p23", "Infra administrativa", pontuacao.INFRA_ADMIN),
        ("p24", "Infra esportiva", pontuacao.INFRA_ESP),
    ]
    linhas = []
    for chave, nome, tabela in checagem:
        if chave not in work.columns:
            continue
        s = work[chave].astype(str).str.strip()
        s = s[s != ""]
        nao_reco = s[~s.isin(tabela.keys())]
        if len(nao_reco):
            exemplos = ", ".join(sorted(nao_reco.unique())[:3])
            linhas.append({"Pergunta": nome, "Não reconhecidas": len(nao_reco), "Exemplos": exemplos})
    if linhas:
        st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)
    else:
        st.success("Todas as respostas das perguntas de nota foram reconhecidas.")


def _freq_tokens(serie):
    freqs = {}
    for valor in serie.astype(str):
        for parte in valor.replace(";", ",").split(","):
            t = parte.strip()
            if t and t.lower() not in ("nan", "não trabalhamos com modalidades esportivas"):
                freqs[t] = freqs.get(t, 0) + 1
    return freqs


def _wordcloud(freqs):
    freqs = {k: v for k, v in (freqs or {}).items() if str(k).strip()}
    if not freqs:
        return None
    from wordcloud import WordCloud
    wc = WordCloud(width=900, height=360, background_color="white",
                   colormap="Blues", prefer_horizontal=0.9, collocations=False)
    wc.generate_from_frequencies(freqs)
    return wc.to_array()
