# -*- coding: utf-8 -*-
"""
Tela 6 — Fichas (Fase 4)
========================
As organizações selecionadas aparecem como mini-cartões com toda a informação:
pontuação, dados, interesse do patrocinador, mentor responsável e o resultado
da entrevista. Aqui você também aloca/ajusta o mentor de cada uma.
"""
import io

import pandas as pd
import streamlit as st

from telas import _calculo, _ui
from regras import funil
from regras import processo as proc


def mostrar():
    st.title("6 · Fichas (Fase 4)")
    _ui.cabecalho()

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para começar.")
        return

    mapa = st.session_state["mapa"]
    vagas = int(st.session_state.get("vagas", 10))
    pool_size = int(st.session_state.get("pool_fase2", 30))
    f = _calculo.funil_df(dados, mapa, vagas, pool_size)

    sel = funil.selecionadas(f)
    selecionadas = sel[sel["Fase"] == "Selecionada"]
    reservas = sel[sel["Fase"] == "Aprovada (reserva)"]

    c = st.columns(3)
    c[0].metric("Selecionadas (vagas)", len(selecionadas))
    c[1].metric("Reservas aprovadas", len(reservas))
    c[2].metric("Meta (vagas)", vagas)

    if len(sel) == 0:
        st.info("Ainda não há organizações aprovadas nas duas fases. Conclua a Documental e a Entrevista.")
        return

    st.download_button(
        "Baixar fichas das selecionadas (Excel)",
        _exportar(sel),
        "fichas_selecionadas_case2027.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.subheader("Selecionadas")
    _grade(f, selecionadas)

    if len(reservas):
        st.divider()
        st.subheader("Reservas aprovadas")
        _grade(f, reservas)


def _grade(f, df):
    linhas = list(df.itertuples())
    for i in range(0, len(linhas), 2):
        cols = st.columns(2)
        for col, r in zip(cols, linhas[i:i + 2]):
            with col:
                _cartao(f, r.dig)


def _cartao(f, dig):
    r = f[f["dig"] == dig].iloc[0]
    estado = _calculo.estado()
    reg = proc.registro(estado, dig)
    selecionada = r["Fase"] == "Selecionada"

    with st.container(border=True):
        badge = "SELECIONADA" if selecionada else "RESERVA"
        cor = "#1F4E79" if selecionada else "#7A5412"
        st.markdown(
            f"<span style='background:{cor};color:#fff;padding:2px 8px;border-radius:4px;"
            f"font-size:12px'>{badge}</span>", unsafe_allow_html=True)
        st.markdown(f"### {r['Entidade']}")
        st.caption(f"Posição {int(r['Posição'])} · nota {int(r['Nota'])} · {r['Cidade']}/{r['UF']} · "
                   f"{r['Região']} · {r['Anos']} anos")

        info = st.columns(2)
        info[0].markdown(f"**Interesse do patrocinador:** {'Sim' if r['interesse'] else 'Não'}")
        comp = {True: "Sim", False: "Não", None: "—"}[reg.get("entrevista_compareceu")]
        info[1].markdown(f"**Compareceu à entrevista:** {comp}")

        mentor = st.text_input("Mentor responsável", value=reg.get("entrevista_mentor", ""), key=f"fmentor_{dig}")
        if mentor != reg.get("entrevista_mentor", ""):
            if st.button("Salvar mentor", key=f"fsalvar_{dig}"):
                reg["entrevista_mentor"] = mentor.strip()
                _calculo.salvar_estado()
                st.rerun()

        relato = reg.get("entrevista_relato", "")
        if relato:
            st.markdown(f"**Relato da reunião:** {relato}")

        with st.expander("Pontuação por bloco (radar)"):
            _ui.ficha(f, r["Entidade"])


def _exportar(sel):
    cols = ["Posição", "Entidade", "CNPJ", "Cidade", "UF", "Região", "Nota", "Anos",
            "Fase", "interesse", "entrevista_mentor", "entrevista_compareceu", "entrevista_relato"]
    cols = [c for c in cols if c in sel.columns]
    tab = sel[cols].rename(columns={
        "Anos": "Tempo (anos)", "Fase": "Situação", "interesse": "Interesse patrocinador",
        "entrevista_mentor": "Mentor", "entrevista_compareceu": "Compareceu",
        "entrevista_relato": "Relato da reunião",
    })
    if "Interesse patrocinador" in tab.columns:
        tab["Interesse patrocinador"] = tab["Interesse patrocinador"].map({True: "Sim", False: "Não"})
    if "Compareceu" in tab.columns:
        tab["Compareceu"] = tab["Compareceu"].map({True: "Sim", False: "Não"}).fillna("—")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        tab.to_excel(writer, index=False, sheet_name="Selecionadas")
    return buffer.getvalue()
