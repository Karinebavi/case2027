# -*- coding: utf-8 -*-
"""
Tela 1 — Importar (base acumulada)
==================================
Sobe o CSV das inscrições exportado do Wix. O sistema reconhece as colunas,
normaliza e SOMA à base — que fica guardada e cresce a cada arquivo, sem
duplicar entidades (o CNPJ é a chave). Você pode baixar a base e zerá-la.
"""
import streamlit as st

from regras import leitura, mapeamento, normalizacao, base_dados
from base import campos as campos_def
from telas import _ui


def _carregar_base_para_sessao():
    """Garante que a base acumulada esteja carregada na sessão."""
    base = base_dados.carregar()
    st.session_state["dados"] = base
    st.session_state["mapa"] = normalizacao.mapa_identidade()
    st.session_state["mapa_ok"] = len(base) > 0
    return base


def mostrar():
    if "dados" not in st.session_state:
        _carregar_base_para_sessao()

    st.title("1 · Importar")
    _ui.cabecalho()

    st.caption("Suba o CSV exportado do Wix. As inscrições somam à base já existente.")
    arquivo = st.file_uploader("Arquivo CSV das inscrições", type=["csv"], key="upload_csv")

    if arquivo is not None:
        _processar_upload(arquivo)

    st.divider()
    _painel_base(st.session_state["dados"])


def _processar_upload(arquivo):
    try:
        novo = leitura.ler_csv(arquivo)
    except leitura.ArquivoCorrompido as aviso:
        st.error(str(aviso))
        return
    except Exception as erro:
        st.error(f"Não consegui ler esse arquivo. Detalhe técnico: {erro}")
        return

    colunas = list(novo.columns)
    auto = mapeamento.auto_map(colunas)

    # Correção só das obrigatórias que o sistema não reconheceu
    obrig = [(ch, rot) for (_g, ch, rot, ob, _d) in campos_def.CAMPOS if ob]
    faltando = [(ch, rot) for ch, rot in obrig if not auto.get(ch)]
    manual = {}
    if faltando:
        st.warning("Algumas colunas obrigatórias não foram reconhecidas. Indique a coluna certa:")
        opcoes = ["— não encontrada —"] + colunas
        for ch, rot in faltando:
            escolha = st.selectbox(rot, opcoes, key=f"map_{ch}")
            if escolha and not escolha.startswith("—"):
                manual[ch] = escolha

    mapa = dict(auto)
    mapa.update(manual)
    ainda_falta = [rot for ch, rot in obrig if not mapa.get(ch)]

    st.write(f"**{len(novo)}** inscrições no arquivo. "
             + ("Tudo reconhecido." if not ainda_falta else f"Faltam: {', '.join(ainda_falta)}."))

    if st.button("Somar à base", type="primary", disabled=bool(ainda_falta)):
        novos_norm = normalizacao.normalizar(novo, mapa)
        base = base_dados.carregar()
        final, cnpjs_novos, n_atualizados = base_dados.acumular(base, novos_norm)
        base_dados.salvar(final)
        st.session_state["dados"] = final
        st.session_state["mapa"] = normalizacao.mapa_identidade()
        st.session_state["mapa_ok"] = len(final) > 0
        st.session_state["novos_cnpjs"] = cnpjs_novos
        # limpa caches de cálculo para refletir a base nova
        st.cache_data.clear()
        st.success(
            f"{len(cnpjs_novos)} novas · {n_atualizados} atualizadas · "
            f"base agora com {len(final)} inscrições."
        )
        st.rerun()


def _painel_base(base):
    n = len(base)
    st.subheader("Base acumulada")
    if n == 0:
        st.info("A base está vazia. Suba um CSV para começar.")
        return

    novos = st.session_state.get("novos_cnpjs") or set()
    c = st.columns(3)
    c[0].metric("Inscrições na base", n)
    c[1].metric("Novas na última importação", len(novos))
    ufs = base["uf"].nunique() if "uf" in base.columns else 0
    c[2].metric("Estados representados", ufs)

    st.caption("Prossiga para a tela 2 · Resultado para ver as pontuações.")
    with st.expander("Ver base (colunas principais)"):
        cols = [c for c in ["nome_entidade", "cnpj", "cidade", "uf", "data_envio", "data_fundacao"]
                if c in base.columns]
        st.dataframe(
            base[cols].rename(columns={
                "nome_entidade": "Entidade", "cnpj": "CNPJ", "cidade": "Cidade",
                "uf": "UF", "data_envio": "Data de envio", "data_fundacao": "Fundação",
            }),
            width="stretch", hide_index=True, height=320,
        )

    col_a, col_b = st.columns(2)
    col_a.download_button(
        "Baixar base (CSV)", base.to_csv(index=False).encode("utf-8"),
        "base_case2027.csv", "text/csv", width="stretch",
    )
    if col_b.button("Zerar base", width="stretch"):
        st.session_state["_confirmar_zerar"] = True
    if st.session_state.get("_confirmar_zerar"):
        st.warning("Isto apaga TODAS as inscrições da base. Tem certeza?")
        z1, z2, _ = st.columns([1, 1, 3])
        if z1.button("Sim, zerar tudo", type="primary"):
            base_dados.limpar()
            for k in ["dados", "mapa", "mapa_ok", "novos_cnpjs", "_confirmar_zerar",
                      "fase2_ms", "fase2_cnpjs"]:
                st.session_state.pop(k, None)
            st.cache_data.clear()
            st.rerun()
        if z2.button("Cancelar"):
            st.session_state["_confirmar_zerar"] = False
            st.rerun()
