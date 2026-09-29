# -*- coding: utf-8 -*-
"""
Tela 3 — Análises (interesse do patrocinador)
=============================================
Aqui saem as organizações que estão na Fase 2 (as melhores do ranking) já com
a coluna de interesse do patrocinador. Você pode marcar o interesse de dois
jeitos: direto na tabela, ou subindo a planilha que o patrocinador preencheu.
O interesse apenas DESTACA — não elimina ninguém. Dá para limpar e recomeçar.
"""
import streamlit as st

from telas import _calculo, _ui
from regras import exportacao
from regras import processo as proc


def mostrar():
    st.title("3 · Análises")
    _ui.cabecalho()

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para usar as análises.")
        return

    mapa = st.session_state["mapa"]
    vagas = int(st.session_state.get("vagas", 10))
    pool_size = int(st.session_state.get("pool_fase2", 30))
    f = _calculo.funil_df(dados, mapa, vagas, pool_size)
    pool = f[f["em_pool"]].sort_values("Posição")

    st.caption(
        f"As **{len(pool)}** melhores do ranking vão à Fase 2. Marque na coluna **Interesse** "
        "as que o patrocinador quer destacar (as demais seguem na documental mesmo assim)."
    )

    # ---------- Marcar interesse direto na tabela ----------
    st.subheader("As organizações da Fase 2 · interesse do patrocinador")
    disp = pool[["Posição", "Entidade", "Cidade", "UF", "Nota"]].copy()
    disp.insert(0, "Interesse", pool["interesse"].astype(bool).values)
    edit = st.data_editor(
        disp, width="stretch", hide_index=True, height=430,
        disabled=[c for c in disp.columns if c != "Interesse"],
        column_config={
            "Interesse": st.column_config.CheckboxColumn("Interesse", help="Marque o interesse do patrocinador"),
            "Nota": st.column_config.NumberColumn("Nota"),
            "Posição": st.column_config.NumberColumn("Posição", width="small"),
        },
        key="editor_interesse",
    )
    estado = _calculo.estado()
    mudou = False
    for dig, novo in zip(pool["dig"].values, edit["Interesse"].values):
        reg = proc.registro(estado, dig)
        if bool(reg.get("interesse")) != bool(novo):
            reg["interesse"] = bool(novo)
            mudou = True
    if mudou:
        _calculo.salvar_estado()

    marcadas = int(edit["Interesse"].sum())
    st.caption(f"**{marcadas}** marcadas com interesse do patrocinador.")

    colr1, colr2 = st.columns([1, 3])
    if colr1.button("Limpar interesse (voltar ao original)"):
        for dig in f["dig"]:
            proc.registro(estado, dig)["interesse"] = False
        _calculo.salvar_estado()
        st.rerun()

    st.divider()

    # ---------- Planilha do patrocinador ----------
    with st.expander("Preferir pela planilha? Baixe, o patrocinador marca e você sobe aqui"):
        st.download_button(
            "Baixar planilha para o patrocinador (Excel)",
            exportacao.montar_planilha(f, vagas),
            "pontuacao_case2027.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.caption("A planilha traz a memória de cálculo (pontos por bloco) e a coluna 'Interesse do patrocinador'.")
        arquivo = st.file_uploader("Planilha marcada (Excel ou CSV)", type=["xlsx", "csv"], key="upload_marcacao")
        if arquivo is not None:
            marcados, aviso = exportacao.ler_marcacao(arquivo)
            if aviso:
                st.error(aviso)
            else:
                _validar_e_aplicar(f, marcados)


def _validar_e_aplicar(f, marcados):
    base_digs = set(f["dig"])
    reconhecidos = marcados & base_digs
    nao_encontrados = marcados - base_digs

    m = st.columns(3)
    m[0].metric("Marcações lidas", len(marcados))
    m[1].metric("Reconhecidas", len(reconhecidos))
    m[2].metric("Não encontradas", len(nao_encontrados))
    if not marcados:
        st.warning("Nenhuma linha marcada como 'Sim' na coluna de interesse.")
        return

    obs = f[f["dig"].isin(reconhecidos)].sort_values("Posição").copy()
    obs["No pool F2"] = obs["em_pool"].map(lambda x: "Sim" if x else "Não (fila)")
    st.dataframe(
        obs[["Posição", "Entidade", "Cidade", "UF", "Nota", "Situação", "No pool F2"]],
        width="stretch", hide_index=True,
        column_config={"Nota": st.column_config.NumberColumn("Nota")},
    )
    if nao_encontrados:
        st.caption(f"{len(nao_encontrados)} CNPJ(s) marcados não foram encontrados na base atual.")

    if st.button("Aplicar interesse da planilha", type="primary"):
        estado = _calculo.estado()
        for dig in base_digs:
            proc.registro(estado, dig)["interesse"] = dig in reconhecidos
        _calculo.salvar_estado()
        st.success(f"Interesse aplicado a {len(reconhecidos)} organizações.")
        st.rerun()
