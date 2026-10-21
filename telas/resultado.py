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
import tema

SITUACOES = ["Classificada", "Fila de espera", "Fora do perfil", "Inelegível"]

# Cor da situação derivada da fonte única (tema.SEMAFORO).
CORES_SITUACAO = {k: f"background-color:{bg};color:{fg}" for k, (bg, fg) in tema.SEMAFORO.items()}


def mostrar():
    st.title("2 · Resultado")
    _ui.cabecalho(2, "Veja a pontuação de todas as organizações. As melhores (padrão 30) seguem "
                     "para a Fase 2; defina as vagas e, se quiser, baixe a planilha.")

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

    ca, cb, cc = st.columns([1, 1, 2], vertical_alignment="bottom")
    ca.number_input("Vagas finais", min_value=1, step=1, key="vagas",
                    help="Meta ao final de todo o processo.")
    cb.number_input("Quantas vão à Fase 2 (documental)", min_value=1, step=1, key="pool_fase2",
                    help="As melhores colocadas entram na análise documental. As demais ficam na fila (repescagem automática).")
    with cc:
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

    busca = st.text_input("Buscar entidade", placeholder="digite parte do nome...")
    ver = st.radio("Ver", ["Todas", f"Só as {pool_size} da Fase 2", "Só as inelegíveis / fora do perfil"],
                   horizontal=True, label_visibility="collapsed")
    por_bloco = st.toggle("Ver pontos por bloco (como a nota foi formada)", value=False, key="ver_blocos")
    with st.expander("Mais filtros (situação, região, cidade)"):
        fcol2, fcol3, fcol4 = st.columns(3)
        situacoes = fcol2.multiselect("Situação", SITUACOES, placeholder="Todas")
        regioes = fcol3.multiselect("Região", sorted(r for r in f["Região"].unique() if r), placeholder="Todas")
        cidades = fcol4.multiselect("Cidade", sorted(c for c in f["Cidade"].unique() if c), placeholder="Todas")

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
    BLOCO_COL = {"b1": "Elaboração", "b2": "Execução", "b3": "Equipe", "b4": "Receita",
                 "b5": "Infra adm.", "b6": "Infra esp.", "b7": "Digital"}
    bloco_cols = list(BLOCO_COL) if por_bloco else []
    colunas = (["Posição", "Entidade", "Cidade", "UF", "Nota"] + bloco_cols
               + ["Anos", "Fase 2", "Situação", "Motivo"])
    disp = disp[colunas].rename(columns={**BLOCO_COL, "Anos": "Tempo (anos)",
                                         "Motivo": "Motivo (se não segue)"})

    def _cor_sit(v):
        return CORES_SITUACAO.get(v, "")

    def _cor_pool(v):
        return f"background-color:{tema.LAVANDA};color:{tema.ROXO};font-weight:600" if v == "Sim" else ""

    estilo = (
        disp.style
        .map(_cor_sit, subset=["Situação"])
        .map(_cor_pool, subset=["Fase 2"])
        .format({"Tempo (anos)": "{:.1f}"})
    )
    col_cfg = {
        "Posição": st.column_config.NumberColumn("Posição", width="small"),
        "Nota": st.column_config.ProgressColumn("Nota", min_value=0, max_value=70, format="%d"),
        "Fase 2": st.column_config.TextColumn("Fase 2", width="small"),
        "Motivo (se não segue)": st.column_config.TextColumn("Motivo (se não segue)", width="large"),
    }
    for rot in BLOCO_COL.values():
        if rot in disp.columns:
            col_cfg[rot] = st.column_config.NumberColumn(rot, width="small", format="%d",
                                                         help="Pontos deste bloco (máx. 10)")
    st.dataframe(estilo, width="stretch", hide_index=True, height=460, column_config=col_cfg)

    # ----------------------- Ficha da entidade -----------------------
    st.divider()
    st.subheader("Ficha da entidade")
    st.caption("Escolha uma entidade para ver a nota por bloco e o comparativo com a média.")
    nomes = list(vista.sort_values("Nota", ascending=False)["Entidade"])
    escolha_ficha = st.selectbox("Abrir ficha de:", ["—"] + nomes, key="ficha_sel")
    if escolha_ficha and escolha_ficha != "—":
        _ui.ficha(f, escolha_ficha, dados, mapa)

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
