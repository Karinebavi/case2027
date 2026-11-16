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
from regras import pontuacao
from regras.memoria import so_digitos


@st.cache_data(show_spinner=False)
def _conferencia(dados, mapa):
    return pontuacao.conferencia(dados, mapa)

SITUACOES = ["Classificada", "Fila de espera"]

# Cor da situação derivada da fonte única (tema.SEMAFORO).
CORES_SITUACAO = {k: f"background-color:{bg};color:{fg}" for k, (bg, fg) in tema.SEMAFORO.items()}


def mostrar():
    _ui.cabecalho(2, "Todas as organizações em ordem de nota. As mais bem colocadas seguem para a "
                     "análise de documentos.")

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Ainda não há inscrições. Elas chegam sozinhas do Wix na etapa Inscrições.")
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
    com_atencao = int(f["Motivo"].fillna("").str.strip().ne("").sum())
    c = st.columns(3)
    c[0].metric("Inscrições", total)
    c[1].metric("Na Fase 2 (documentos)", no_pool,
                help=(f"As {pool_size} mais bem colocadas vão à Fase 2."
                      + (f" Por enquanto há só {total} inscrições." if total < pool_size else "")))
    c[2].metric("Com atenção", com_atencao,
                help="Entram no ranking normalmente — o selo só avisa o mentor. Ninguém é excluído aqui.")

    # ----------------------- Ranking -----------------------
    with st.container(horizontal=True, vertical_alignment="bottom", gap="small"):
        busca = st.text_input("Buscar entidade", placeholder="digite parte do nome", width=280,
                              icon=":material/search:")
        ver = st.segmented_control("Ver", ["Todas", "Fase 2", "Com atenção"], default="Todas",
                                   key="ranking_ver") or "Todas"
        mostrar_col = st.pills("Mostrar também", ["Pontos por bloco", "Experiência esportiva"],
                               selection_mode="multi", key="ranking_colunas")
        with st.popover("Filtros", icon=":material/filter_list:"):
            situacoes = st.multiselect("Situação", SITUACOES, placeholder="Todas")
            regioes = st.multiselect("Região", sorted(r for r in f["Região"].unique() if r), placeholder="Todas")
            cidades = st.multiselect("Cidade", sorted(c for c in f["Cidade"].unique() if c), placeholder="Todas")
        with st.popover("Ajustar corte", icon=":material/tune:"):
            st.number_input("Vagas finais", min_value=1, step=1, key="vagas",
                            help="Meta ao final de todo o processo.")
            st.number_input("Quantas vão à Fase 2 (documentos)", min_value=1, step=1, key="pool_fase2",
                            help="As mais bem colocadas entram na análise de documentos. As demais ficam "
                                 "na fila (entram sozinhas se alguém for excluído).")
        st.download_button("Planilha", exportacao.montar_planilha(f, vagas), "pontuacao_case2027.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           icon=":material/download:",
                           help="Todas as organizações, com as vagas em destaque e a coluna "
                                "'Interesse do patrocinador'.")
    por_bloco = "Pontos por bloco" in (mostrar_col or [])
    experiencia = "Experiência esportiva" in (mostrar_col or [])

    vista = f.sort_values(["Nota", "Entidade"], ascending=[False, True])
    if busca:
        vista = vista[vista["Entidade"].str.contains(busca, case=False, na=False, regex=False)]
    if situacoes:
        vista = vista[vista["Situação"].isin(situacoes)]
    if regioes:
        vista = vista[vista["Região"].isin(regioes)]
    if cidades:
        vista = vista[vista["Cidade"].isin(cidades)]
    if ver == "Fase 2":
        vista = vista[vista["em_pool"]]
    elif ver == "Com atenção":
        vista = vista[vista["Motivo"].fillna("").str.strip().ne("")]

    st.caption(f"{len(vista)} de {total} inscrições, por nota. As {pool_size} melhores (Fase 2 = Sim, em lilás) "
               "vão aos documentos; a coluna Atenção sinaliza pendências — ninguém é excluído aqui. "
               "Clique numa linha para ver a ficha.")

    disp = vista.copy()
    disp["Fase 2"] = disp["em_pool"].map(lambda x: "Sim" if x else "")
    BLOCO_COL = {"b1": "Elaboração", "b2": "Execução", "b3": "Equipe", "b4": "Receita",
                 "b5": "Infra adm.", "b6": "Infra esp.", "b7": "Digital"}
    bloco_cols = list(BLOCO_COL) if por_bloco else []
    dig = disp["CNPJ"].map(so_digitos)
    if por_bloco:
        # "pontos · resposta" — a mesma conta da nota, para conferir sem abrir a ficha
        conf = _conferencia(dados, mapa)
        for i, b in enumerate(BLOCO_COL):
            disp[b] = dig.map(lambda d, i=i: conf[d][i] if d in conf else "")
    exp_cols = []
    if experiencia:
        exp = _experiencia(dados)
        disp["Modalidades"] = dig.map(lambda d: exp.get(d, {}).get("modalidades", ""))
        disp["Pessoas atendidas"] = dig.map(lambda d: exp.get(d, {}).get("beneficiarios", ""))
        disp["Projetos (3 anos)"] = dig.map(lambda d: exp.get(d, {}).get("projetos", ""))
        exp_cols = ["Modalidades", "Pessoas atendidas", "Projetos (3 anos)"]
    # O que decide vem primeiro; detalhes depois.
    colunas = (["Posição", "Entidade", "Nota", "Fase 2", "Situação", "Motivo", "Cidade", "UF", "Anos"]
               + bloco_cols + exp_cols)
    disp = disp[colunas].rename(columns={**BLOCO_COL, "Anos": "Tempo (anos)", "Motivo": "Atenção"})

    def _cor_sit(v):
        return CORES_SITUACAO.get(v, "")

    def _cor_pool(v):
        return f"background-color:{tema.LAVANDA};color:{tema.ROXO_ESCURO};font-weight:600" if v == "Sim" else ""

    def _cor_conferencia(v):
        # resposta que a régua não reconhece: vermelho, para conferir no formulário
        cor = tema.COR_STATUS["vermelho"]
        return f"background-color:{cor[0]};color:{cor[1]}" if str(v).startswith("0 · não reconhecida") else ""

    estilo = (
        disp.style
        .map(_cor_sit, subset=["Situação"])
        .map(_cor_pool, subset=["Fase 2"])
        .format({"Tempo (anos)": "{:.1f}"})
    )
    blocos_vis = [c for c in BLOCO_COL.values() if c in disp.columns]
    if blocos_vis:
        estilo = estilo.map(_cor_conferencia, subset=blocos_vis)
    col_cfg = {
        "Posição": st.column_config.NumberColumn("Posição", width="small", pinned=True),
        "Entidade": st.column_config.TextColumn("Entidade", width="large", pinned=True),
        "Nota": st.column_config.ProgressColumn("Nota", min_value=0, max_value=70, format="%d", width="small"),
        "Fase 2": st.column_config.TextColumn("Fase 2", width="small"),
        "Atenção": st.column_config.TextColumn("Atenção", width="medium",
                                               help="Pendência sinalizada (não exclui). Confirmada nos documentos."),
        "Modalidades": st.column_config.TextColumn("Modalidades", width="large"),
        "Pessoas atendidas": st.column_config.TextColumn("Pessoas atendidas", width="small"),
        "Projetos (3 anos)": st.column_config.TextColumn("Projetos (3 anos)", width="large"),
    }
    for rot in blocos_vis:
        col_cfg[rot] = st.column_config.TextColumn(
            rot, width="medium", help="Pontos deste bloco (máx. 10) · o que a entidade respondeu")
    altura = min(36 * (len(disp) + 1) + 4, 640)
    sel = st.dataframe(estilo, width="stretch", hide_index=True, height=altura, column_config=col_cfg,
                       on_select="rerun", selection_mode="single-row", key="ranking_tabela")
    if blocos_vis:
        st.caption("Em vermelho: resposta que a régua não reconhece (pontuou 0) — confira a opção no "
                   "formulário do Wix.")

    # ----------------------- Ficha da entidade clicada -----------------------
    linhas = sel.selection.rows if sel else []
    if linhas:
        entidade = disp.iloc[linhas[0]]["Entidade"]
        with st.container(border=True):
            st.subheader(entidade)
            _ui.ficha(f, entidade, dados, mapa)

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


def _experiencia(dados):
    """CNPJ (dígitos) -> modalidades (com a 'outra atividade') e pessoas atendidas."""
    out = {}
    for _, row in dados.iterrows():
        d = so_digitos(row.get("cnpj", ""))
        if not d:
            continue
        mods = [m.strip() for m in str(row.get("modalidades", "") or "").split(",") if m.strip()]
        outra = str(row.get("outra_modalidade", "") or "").strip()
        if outra:
            mods.append(outra)
        out[d] = {"modalidades": ", ".join(mods), "beneficiarios": str(row.get("beneficiarios", "") or "").strip(),
                  "projetos": " ".join(str(row.get("projetos_3anos", "") or "").split())}
    return out
