# -*- coding: utf-8 -*-
"""
Tela 3 — Painel & baixar (visão geral)
======================================
Gráficos e resumos do processo, e o download da planilha final.
"""
import io
import pandas as pd
import streamlit as st

from telas import _calculo, _ui


def mostrar():
    st.title("4 · Painel & baixar")
    _ui.cabecalho()

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para ver o painel.")
        return

    mapa = st.session_state["mapa"]
    vagas = int(st.session_state.get("vagas", 10))
    df = _calculo.processar(dados, mapa, vagas)

    total = len(df)
    em_classificacao = int(df["Situação"].isin(["Classificada", "Fila de espera"]).sum())
    classificadas = int((df["Situação"] == "Classificada").sum())
    fora = int((df["Situação"] == "Fora do perfil").sum())
    inelegiveis = int((df["Situação"] == "Inelegível").sum())

    c = st.columns(4)
    c[0].metric("Inscrições", total)
    c[1].metric("Classificadas", classificadas)
    c[2].metric("Fora do perfil", fora)
    c[3].metric("Inelegíveis", inelegiveis)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Classificadas por região")
        reg = (df[df["Situação"] == "Classificada"]
               .groupby("Região").size().rename("Classificadas").sort_values(ascending=False))
        if len(reg):
            st.bar_chart(reg)
        else:
            st.caption("Ainda não há classificadas.")
    with col2:
        st.subheader("Situação das inscrições")
        sit = df["Situação"].value_counts().rename("Inscrições")
        st.bar_chart(sit)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Distribuição das notas")
        notas = df[df["Situação"].isin(["Classificada", "Fila de espera"])]["Nota"]
        if len(notas):
            dist = notas.value_counts().sort_index().rename("Inscrições")
            dist.index.name = "Nota"
            st.bar_chart(dist)
        else:
            st.caption("Sem inscrições em classificação.")
    with col4:
        st.subheader("Funil da seleção")
        funil = pd.DataFrame(
            {"Quantidade": [total, em_classificacao, classificadas]},
            index=["Inscrições", "Em classificação", "Classificadas"],
        )
        st.bar_chart(funil)

    st.divider()
    st.subheader("Baixar")
    exportar = df.sort_values(["Nota", "Entidade"], ascending=[False, True]).drop(
        columns=[c for c in ["_data_fundacao"] if c in df.columns]
    )
    col_a, col_b = st.columns(2)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        exportar.to_excel(writer, index=False, sheet_name="Classificacao")
    col_a.download_button(
        "Baixar tudo (Excel)", buffer.getvalue(),
        "classificacao_case2027.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

    classificadas_df = exportar[exportar["Situação"] == "Classificada"][
        ["Posição", "Entidade", "UF", "Região", "Nota"]
    ]
    col_b.download_button(
        "Baixar só as classificadas (CSV)",
        classificadas_df.to_csv(index=False).encode("utf-8"),
        "classificadas_case2027.csv", "text/csv", width="stretch",
    )
