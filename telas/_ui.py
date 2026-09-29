# -*- coding: utf-8 -*-
"""Peças de interface reaproveitadas pelas telas (cabeçalho, ficha)."""
import streamlit as st

BLOCOS = ["Elaboração", "Execução", "Equipe", "Receita", "Infra adm.", "Infra esp.", "Digital"]
COLS_B = ["b1", "b2", "b3", "b4", "b5", "b6", "b7"]


def rotulos(df):
    """Rótulos únicos por entidade -> (rotulo_por_cnpj, cnpj_por_rotulo).

    Usado pela seleção da Fase 2 no Resultado e na aba Análises, para que os
    dois falem a mesma língua (mesmo rótulo para a mesma entidade).
    """
    rotulo_por_cnpj, cnpj_por_rotulo = {}, {}
    for r in df.sort_values("Nota", ascending=False).itertuples():
        lab = r.Entidade
        if lab in cnpj_por_rotulo:
            lab = f"{r.Entidade} · {r.Cidade}"
        if lab in cnpj_por_rotulo:
            lab = f"{r.Entidade} · {r.CNPJ}"
        cnpj_por_rotulo[lab] = r.CNPJ
        rotulo_por_cnpj[r.CNPJ] = lab
    return rotulo_por_cnpj, cnpj_por_rotulo


def cabecalho():
    """Faixa institucional com o contexto atual (ciclo, base, vagas)."""
    dados = st.session_state.get("dados")
    n = len(dados) if dados is not None else 0
    vagas = st.session_state.get("vagas", 10)
    if n:
        ctx = f"Ciclo 2027 · {n} inscrições carregadas · {vagas} vagas"
    else:
        ctx = "Ciclo 2027 · nenhuma base carregada"
    st.markdown(
        f'<div class="case-header"><div class="t">CASE 2027 — Seleção de Entidades</div>'
        f'<div class="c">{ctx}</div></div>',
        unsafe_allow_html=True,
    )


def ficha(df, entidade):
    """Mostra a ficha de uma entidade: nota por bloco, radar (entidade x média) e dados."""
    import plotly.graph_objects as go

    linha = df[df["Entidade"] == entidade]
    if linha.empty:
        return
    r = linha.iloc[0]
    valores = [int(r[c]) for c in COLS_B]

    em = df[df["Status"] == "Em classificação"]
    if len(em):
        medias = [round(float(em[c].mean()), 1) for c in COLS_B]
    else:
        medias = [0] * 7

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores + [valores[0]], theta=BLOCOS + [BLOCOS[0]],
        fill="toself", name=entidade[:24], line_color="#1F4E79",
    ))
    fig.add_trace(go.Scatterpolar(
        r=medias + [medias[0]], theta=BLOCOS + [BLOCOS[0]],
        name="Média das classificáveis", line_color="#B0863B",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 10], tickvals=[0, 2, 4, 6, 8, 10])),
        showlegend=True, height=380, margin=dict(l=50, r=50, t=30, b=30),
        legend=dict(orientation="h", y=-0.1),
    )

    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(fig, use_container_width=True)
    with c2:
        st.metric("Nota total", int(r["Nota"]))
        st.write(f"**Situação:** {r['Situação']}")
        pos = r.get("Posição")
        if pos is not None and str(pos) not in ("", "None", "nan"):
            st.write(f"**Posição no ranking:** {int(pos)}")
        st.write(f"**Cidade / UF:** {r['Cidade']} · {r['UF']}")
        st.write(f"**Região:** {r['Região']}")
        st.write(f"**Tempo de funcionamento:** {r['Anos']} anos")

    motivo = str(r.get("Motivo", "") or "")
    if motivo:
        st.warning(f"**Por que a nota é {int(r['Nota'])}:** {motivo}. "
                   "Os blocos abaixo mostram os pontos que teria, mas a nota final foi zerada por esse motivo.")

    st.markdown("**Memória de cálculo — pontos por bloco**")
    tabela = [{"Bloco": b, "Pontos": v, "Média das aptas": m} for b, v, m in zip(BLOCOS, valores, medias)]
    st.dataframe(tabela, width="stretch", hide_index=True)
