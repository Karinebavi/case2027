# -*- coding: utf-8 -*-
"""
Tela 2 — Resultado (pontuação e ranking)
========================================
Todas as organizações da base, em ordem de nota, com a situação em cor.
As melhores entram automaticamente no POOL da Fase 2 (documental) — por
padrão as 30 primeiras — e a meta final são as VAGAS (por padrão 10).
Aqui você também exporta a planilha (todas, com as vagas em destaque).
"""
import streamlit as st

from telas import _calculo, _ui
from regras import validacao, exportacao

SITUACOES = ["Classificada", "Fila de espera", "Fora do perfil", "Inelegível"]

CORES_SITUACAO = {
    "Classificada": "background-color:#E4F1E8;color:#1B5E20",
    "Fila de espera": "background-color:#FBF1DD;color:#7A5412",
    "Fora do perfil": "background-color:#ECECEC;color:#555555",
    "Inelegível": "background-color:#F6E4E4;color:#8A2A2A",
}


def mostrar():
    st.title("2 · Resultado")
    _ui.cabecalho()

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para ver o resultado.")
        return

    mapa = st.session_state["mapa"]
    st.session_state.setdefault("vagas", 10)
    st.session_state.setdefault("pool_fase2", 30)
    vagas = int(st.session_state["vagas"])
    pool_size = int(st.session_state["pool_fase2"])

    f = _calculo.funil_df(dados, mapa, vagas, pool_size)

    # Resumo
    total = len(f)
    no_pool = int(f["em_pool"].sum())
    c = st.columns(4)
    c[0].metric("Inscrições", total)
    c[1].metric("Aptas (passaram nas eliminatórias)", int(f["Status"].eq("Em classificação").sum()))
    c[2].metric(f"Vão à Fase 2 (as {pool_size} melhores)", no_pool)
    c[3].metric("Vagas finais", vagas)

    ca, cb, cc = st.columns([1, 1, 2])
    ca.number_input("Vagas finais", min_value=1, step=1, key="vagas",
                    help="Meta ao final de todo o processo.")
    cb.number_input("Quantas vão à Fase 2 (documental)", min_value=1, step=1, key="pool_fase2",
                    help="As melhores colocadas entram na análise documental. As demais ficam na fila (repescagem automática).")
    with cc:
        st.write("")
        st.write("")
        st.download_button(
            "Baixar planilha de pontuação (Excel)",
            exportacao.montar_planilha(f, vagas),
            "pontuacao_case2027.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
        st.caption("Todas as organizações, com as vagas em destaque e a coluna 'Interesse do patrocinador' para a aba Análises.")

    # ----------------------- Ranking -----------------------
    st.subheader("Ranking")
    st.caption(
        f"Ordenadas por nota. As **{pool_size}** melhores (coluna **Fase 2 = Sim**, em azul) vão à documental; "
        "as demais ficam na fila. A cor da situação mostra o porquê de quem não segue."
    )

    fcol1, fcol2, fcol3, fcol4 = st.columns([2, 1, 1, 1])
    busca = fcol1.text_input("Buscar entidade", placeholder="digite parte do nome...")
    situacoes = fcol2.multiselect("Situação", SITUACOES, placeholder="Todas")
    regioes = fcol3.multiselect("Região", sorted(r for r in f["Região"].unique() if r), placeholder="Todas")
    cidades = fcol4.multiselect("Cidade", sorted(c for c in f["Cidade"].unique() if c), placeholder="Todas")
    ver = st.radio("Ver", ["Todas", f"Só as {pool_size} da Fase 2", "Só as inelegíveis / fora do perfil"],
                   horizontal=True, label_visibility="collapsed")

    vista = f.sort_values(["Nota", "Entidade"], ascending=[False, True])
    if busca:
        vista = vista[vista["Entidade"].str.contains(busca, case=False, na=False)]
    if situacoes:
        vista = vista[vista["Situação"].isin(situacoes)]
    if regioes:
        vista = vista[vista["Região"].isin(regioes)]
    if cidades:
        vista = vista[vista["Cidade"].isin(cidades)]
    if ver.startswith("Só as") and "Fase 2" in ver:
        vista = vista[vista["em_pool"]]
    elif ver.startswith("Só as inelegíveis"):
        vista = vista[vista["Situação"].isin(["Inelegível", "Fora do perfil"])]

    st.caption(f"Mostrando {len(vista)} de {total} inscrições.")

    disp = vista.copy()
    disp["Fase 2"] = disp["em_pool"].map(lambda x: "Sim" if x else "")
    colunas = ["Posição", "Entidade", "Cidade", "UF", "Nota", "Anos", "Fase 2", "Situação", "Motivo"]
    disp = disp[colunas].rename(columns={"Anos": "Tempo (anos)", "Motivo": "Motivo (se não segue)"})

    def _cor_sit(v):
        return CORES_SITUACAO.get(v, "")

    def _cor_pool(v):
        return "background-color:#E7EEF6;color:#1F4E79;font-weight:600" if v == "Sim" else ""

    estilo = (
        disp.style
        .map(_cor_sit, subset=["Situação"])
        .map(_cor_pool, subset=["Fase 2"])
        .format({"Tempo (anos)": "{:.1f}"})
    )
    st.dataframe(
        estilo, width="stretch", hide_index=True, height=460,
        column_config={
            "Posição": st.column_config.NumberColumn("Posição", width="small"),
            "Nota": st.column_config.ProgressColumn("Nota", min_value=0, max_value=70, format="%d"),
            "Fase 2": st.column_config.TextColumn("Fase 2", width="small"),
            "Motivo (se não segue)": st.column_config.TextColumn("Motivo (se não segue)", width="large"),
        },
    )

    # ----------------------- Ficha da entidade -----------------------
    st.divider()
    st.subheader("Ficha da entidade")
    st.caption("Escolha uma entidade para ver a nota por bloco e o comparativo com a média.")
    nomes = list(vista.sort_values("Nota", ascending=False)["Entidade"])
    escolha_ficha = st.selectbox("Abrir ficha de:", ["—"] + nomes, key="ficha_sel")
    if escolha_ficha and escolha_ficha != "—":
        _ui.ficha(f, escolha_ficha)

    # ----------------------- Detalhes -----------------------
    st.divider()
    st.caption("A memória de cálculo (pontos de cada bloco) está na ficha acima e na planilha exportada.")

    v = validacao.validar(dados, mapa)
    with st.expander(f"Pendências na base ({len(v['pendencias'])})"):
        if len(v["pendencias"]) == 0:
            st.write("Nenhuma pendência encontrada.")
        else:
            st.caption(
                f"{v['repetido']} com CNPJ repetido · {v['invalido']} com CNPJ inválido · "
                f"{v['branco']} com campo em branco."
            )
            st.dataframe(v["pendencias"], width="stretch", hide_index=True)
