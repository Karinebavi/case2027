# -*- coding: utf-8 -*-
"""
Tela 3 — Documentos (Fase 2)
============================
Para cada organização selecionada: sobe os documentos (PDF), o sistema
lê e SUGERE se o estatuto tem finalidade esportiva e se há registro em
cartório; você CONFIRMA cada item (com campo para identificar o trecho na
mão quando o PDF não puder ser lido). Marca o Instagram (peso 2x).

Os documentos são lidos no próprio app — nada é enviado para fora.
"""
import streamlit as st

from telas import _calculo, _ui
from regras import documentos as doc
from regras import classificacao


def mostrar():
    st.title("5 · Documentos (Fase 2)")
    _ui.cabecalho()

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para começar.")
        return

    cnpjs = st.session_state.get("fase2_cnpjs")
    if not cnpjs:
        st.info(
            "Nenhuma organização selecionada. Faça a seleção na aba 3 · Análises "
            "(planilha do patrocinador) ou na aba 2 · Resultado (seleção rápida)."
        )
        return

    mapa = st.session_state["mapa"]
    vagas = int(st.session_state.get("vagas", 10))
    df = _calculo.processar(dados, mapa, vagas)
    sel = df[df["CNPJ"].isin(cnpjs)].sort_values("Nota", ascending=False)
    verdicts = st.session_state.setdefault("fase2_docs", {})

    conferidas = sum(1 for c in cnpjs if verdicts.get(c, {}).get("conferida"))
    st.caption(f"{conferidas} de {len(cnpjs)} organizações conferidas.")

    labels = {f"{r.Entidade}  ·  nota {int(r.Nota)}": r.CNPJ for r in sel.itertuples()}
    escolha = st.selectbox("Escolha a organização para conferir", list(labels.keys()))
    cnpj = labels[escolha]
    org = sel[sel["CNPJ"] == cnpj].iloc[0]
    v = verdicts.setdefault(cnpj, {})

    st.markdown(f"### {org['Entidade']}")
    st.caption(
        f"Nota da Fase 1: {int(org['Nota'])} · {org['Anos']} anos de funcionamento "
        "(CNPJ com +1 ano já confirmado na Fase 1)."
    )

    st.markdown("**1. Documentos (PDF)**")
    c1, c2, c3 = st.columns(3)
    c1.file_uploader("Cartão CNPJ", type=["pdf"], key=f"doc_cnpj_{cnpj}")
    ata = c2.file_uploader("Ata", type=["pdf"], key=f"doc_ata_{cnpj}")
    estatuto = c3.file_uploader("Estatuto", type=["pdf"], key=f"doc_est_{cnpj}")

    st.markdown("**2. Conferências** — o sistema sugere pela leitura; você confirma")

    # Estatuto com finalidade esportiva
    texto_est = doc.extrair_texto(estatuto)
    if estatuto is not None and not texto_est:
        st.warning("Estatuto: não consegui ler o texto (PDF escaneado?). Confira e marque manualmente.")
    achou_esp, trecho_esp = doc.conferir_finalidade_esportiva(texto_est)
    if texto_est:
        st.write("Estatuto com finalidade esportiva — sugestão: **"
                 + ("Sim" if achou_esp else "não encontrei o termo") + "**")
        if trecho_esp:
            st.caption(f"Trecho encontrado: “...{trecho_esp}...”")
    est_ok = st.checkbox("Confirmo: estatuto tem finalidade esportiva", key=f"est_ok_{cnpj}")
    st.text_input("Se precisar, identifique o trecho na mão",
                  key=f"est_tr_{cnpj}", placeholder="cole aqui o trecho do estatuto")

    # Registro em cartório
    texto_reg = doc.extrair_texto(ata) or texto_est
    achou_reg, trecho_reg = doc.conferir_registro(texto_reg)
    if texto_reg:
        st.write("Documentos registrados em cartório — sugestão: **"
                 + ("Sim" if achou_reg else "não encontrei o termo") + "**")
        if trecho_reg:
            st.caption(f"Trecho encontrado: “...{trecho_reg}...”")
    reg_ok = st.checkbox("Confirmo: documentos registrados em cartório", key=f"reg_ok_{cnpj}")

    # Instagram
    st.markdown("**3. Instagram**")
    st.text_input("Link do Instagram", key=f"insta_{cnpj}", placeholder="https://instagram.com/...")
    esporte = st.checkbox("Tem fotos de prática esportiva (dá peso 2x na nota)", key=f"insta_esp_{cnpj}")

    st.divider()
    conferida = st.checkbox("Marcar esta organização como conferida", key=f"conf_{cnpj}")

    v["documentos_ok"] = bool(est_ok and reg_ok)
    v["tem_esporte"] = bool(esporte)
    v["conferida"] = bool(conferida)

    if conferida:
        if v["documentos_ok"]:
            msg = "Documentos conformes. Mantida na classificação"
            msg += " com peso 2x (esporte no Instagram)." if esporte else "."
            st.success(msg)
        else:
            st.error(
                "Documentos incompletos ou não conformes. Será excluída, e uma organização "
                "da fila de espera entra no lugar (na reclassificação)."
            )

    # --- Classificação final da Fase 2 ---
    st.divider()
    st.subheader("Classificação final da Fase 2")
    st.caption(
        "Exclui as conferidas com documento não conforme, repõe da fila de espera e aplica o "
        "peso 2x nas com esporte no Instagram. Atualiza conforme você confere as organizações."
    )

    f2 = classificacao.classificar_fase2(df, verdicts, vagas)
    classif2 = int((f2["Situação Fase 2"] == "Classificada").sum())
    excluidas = int((f2["Situação Fase 2"] == "Excluída (documento)").sum())
    com2x = int((f2["Nota Fase 2"] > f2["Nota"]).sum())
    m = st.columns(3)
    m[0].metric("Classificadas (Fase 2)", classif2)
    m[1].metric("Excluídas por documento", excluidas)
    m[2].metric("Com peso 2x (esporte)", com2x)

    ordem_sit = {"Classificada": 0, "Fila de espera": 1, "Excluída (documento)": 2}
    f2["_o"] = f2["Situação Fase 2"].map(ordem_sit).fillna(3)
    vista = f2.sort_values(["_o", "Nota Fase 2"], ascending=[True, False])
    st.dataframe(
        vista[["Posição Fase 2", "Entidade", "UF", "Região", "Nota", "Nota Fase 2", "Situação Fase 2"]],
        width="stretch", hide_index=True, height=460,
        column_config={
            "Nota": st.column_config.NumberColumn("Nota Fase 1"),
            "Nota Fase 2": st.column_config.NumberColumn("Nota Fase 2 (com 2x)"),
        },
    )

    classificadas_f2 = vista[vista["Situação Fase 2"] == "Classificada"][
        ["Posição Fase 2", "Entidade", "UF", "Região", "Nota", "Nota Fase 2"]
    ]
    st.download_button(
        "Baixar classificação final da Fase 2 (CSV)",
        classificadas_f2.to_csv(index=False).encode("utf-8"),
        "classificacao_fase2_case2027.csv", "text/csv",
    )
