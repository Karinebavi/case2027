# -*- coding: utf-8 -*-
"""
Tela 1 — Importar (base acumulada)
==================================
Sobe o CSV das inscrições exportado do Wix. O sistema reconhece as colunas,
normaliza e SOMA à base — que fica guardada e cresce a cada arquivo, sem
duplicar entidades (o CNPJ é a chave). Você pode baixar a base e zerá-la.
"""
import re

import streamlit as st

import pandas as pd

from regras import leitura, mapeamento, normalizacao, base_dados, nuvem, wix
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
    _ui.cabecalho(1, "Suba o CSV das inscrições exportado do Wix. A cada arquivo, as inscrições "
                     "somam à base — sem duplicar (o CNPJ é a chave).")

    st.caption("Suba o CSV exportado do Wix. As inscrições somam à base já existente.")
    arquivo = st.file_uploader("Arquivo CSV das inscrições", type=["csv"], key="upload_csv")

    if arquivo is not None:
        _processar_upload(arquivo)

    st.divider()
    _sincronizar_wix()

    st.divider()
    _painel_base(st.session_state["dados"])
    _historico()


def _historico():
    """Trilha de auditoria: quem fez o quê e quando (só com a nuvem ativa)."""
    if not nuvem.ativo():
        return
    with st.expander("Histórico de alterações (quem fez o quê)"):
        try:
            linhas = nuvem.historico(300)
        except Exception as erro:
            st.warning(f"Não consegui ler o histórico agora ({erro}).")
            return
        if not linhas:
            st.caption("Nenhuma alteração registrada ainda.")
            return
        df = pd.DataFrame(linhas)
        df["quando"] = (pd.to_datetime(df["quando"], utc=True)
                        .dt.tz_convert("America/Sao_Paulo").dt.strftime("%d/%m/%Y %H:%M"))
        df["detalhe"] = df["detalhe"].astype(str)
        st.dataframe(df.rename(columns={"quando": "Quando", "quem": "Quem",
                                        "acao": "Ação", "detalhe": "Detalhe"}),
                     width="stretch", hide_index=True, height=300)


def _processar_upload(arquivo):
    try:
        novo = leitura.ler_csv(arquivo)
    except leitura.ArquivoCorrompido as aviso:
        st.error(str(aviso))
        return
    except Exception as erro:
        st.error(f"Não consegui ler esse arquivo. Detalhe técnico: {erro}")
        return
    _processar_df(novo, origem=getattr(arquivo, "name", ""), sufixo="csv")


def _processar_df(novo, origem, sufixo):
    """Núcleo compartilhado: mapeia, confirma e soma à base. Serve tanto para o
    CSV quanto para a sincronização com o Wix (o `novo` já é um DataFrame)."""
    colunas = list(novo.columns)
    auto = mapeamento.auto_map(colunas)

    # Essenciais para a base: sem nome e CNPJ não dá para pontuar nem deduplicar.
    # As demais perguntas obrigatórias, se não vierem no formulário (ex.: uma
    # pergunta que só existe este ano), NÃO bloqueiam — elas pontuam 0.
    ESSENCIAIS = {"nome_entidade", "cnpj"}
    obrig = [(ch, rot) for (_g, ch, rot, ob, _d) in campos_def.CAMPOS if ob]
    faltando = [(ch, rot) for ch, rot in obrig if not auto.get(ch)]
    manual = {}
    if faltando:
        st.caption("Perguntas que o sistema não reconheceu neste formulário. Se existirem com "
                   "outro nome, aponte a coluna; as que não existirem pontuam 0.")
        opcoes = ["— não encontrada —"] + colunas
        for ch, rot in faltando:
            escolha = st.selectbox(rot, opcoes, key=f"map_{ch}_{sufixo}")
            if escolha and not escolha.startswith("—"):
                manual[ch] = escolha

    mapa = dict(auto)
    mapa.update(manual)
    falta_ess = [rot for ch, rot in obrig if ch in ESSENCIAIS and not mapa.get(ch)]
    falta_pont = [rot for ch, rot in obrig if ch not in ESSENCIAIS and not mapa.get(ch)]

    if falta_ess:
        st.warning(f"**{len(novo)}** inscrições. Faltam campos essenciais ({', '.join(falta_ess)}) — "
                   "aponte a coluna certa acima para continuar.")
    elif falta_pont:
        st.info(f"**{len(novo)}** inscrições. As perguntas não encontradas "
                f"({', '.join(falta_pont)}) vão pontuar 0 — o resto é somado normalmente.")
    else:
        st.write(f"**{len(novo)}** inscrições. Tudo reconhecido.")

    if st.button("Somar à base", type="primary", disabled=bool(falta_ess), key=f"somar_{sufixo}"):
        novos_norm = normalizacao.normalizar(novo, mapa)
        base = base_dados.carregar()
        final, cnpjs_novos, n_atualizados = base_dados.acumular(base, novos_norm)
        base_dados.salvar(final)
        nuvem.registrar("importar", {
            "origem": origem, "linhas_no_arquivo": len(novo),
            "novas": len(cnpjs_novos), "atualizadas": n_atualizados, "total_base": len(final)})
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


@st.cache_data(ttl=600, show_spinner=False)
def _wix_formularios():
    """Lista (id, nome) dos formulários: primeiro o configurado no Secrets, depois
    os de inscrição do ano mais recente (o 1º da lista é o que vem escolhido)."""
    forms = wix.listar_formularios()
    configurado = wix._cfg().get("form_id")

    def ordem(f):
        fid, nome = f[0], (f[1] or "")
        anos = [int(a) for a in re.findall(r"\b20\d{2}\b", nome)]
        return (fid != configurado, "inscri" not in nome.lower(), -max(anos, default=0), nome)
    return sorted(forms, key=ordem)


def _sincronizar_wix():
    """Botão opcional: puxa as inscrições direto do Wix e soma à base."""
    if not wix.ativo():
        st.caption(":material/sync: Sincronização com o Wix desligada — configure a seção [wix] "
                   "no Secrets (api_key e site_id) para ativar.")
        return
    st.markdown("**Sincronizar com o Wix**")
    st.caption("Puxa as inscrições direto do formulário. Os documentos NÃO vêm por aqui — "
               "no formulário eles são enviados por um link à parte.")

    form_id_sel = None
    try:
        forms = _wix_formularios()
    except Exception as erro:
        forms = []
        st.caption(f"Não consegui listar os formulários agora ({erro}).")
    if forms:
        nomes = {nome: fid for fid, nome in forms}
        escolha = st.selectbox(
            "De qual formulário puxar?", list(nomes.keys()), key="wix_form_sel",
            help="Para o teste com o ano passado, escolha o formulário de inscrição de 2026. "
                 "As perguntas que só existem este ano pontuam 0 automaticamente.")
        form_id_sel = nomes.get(escolha)

    if st.button("Buscar inscrições do Wix", key="wix_buscar", icon=":material/sync:"):
        with st.spinner("Buscando as inscrições no Wix…"):
            try:
                df, info = wix.sincronizar(form_id=form_id_sel)
                st.session_state["_wix_df"] = df
                st.session_state["_wix_info"] = info
                st.session_state.pop("_wix_erro", None)
            except Exception as e:
                st.session_state["_wix_df"] = None
                st.session_state["_wix_erro"] = str(e)
        st.rerun()
    if st.session_state.get("_wix_erro"):
        st.error(st.session_state["_wix_erro"])
    wdf = st.session_state.get("_wix_df")
    if wdf is not None and len(wdf):
        st.caption(st.session_state.get("_wix_info", ""))
        _processar_df(wdf, origem="Wix", sufixo="wix")


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
            nuvem.registrar("zerar_base", {"inscricoes_apagadas": len(base),
                                           "copia_de_seguranca": nuvem.ativo()})
            for k in ["dados", "mapa", "mapa_ok", "novos_cnpjs", "_confirmar_zerar",
                      "fase2_ms", "fase2_cnpjs"]:
                st.session_state.pop(k, None)
            st.cache_data.clear()
            st.rerun()
        if z2.button("Cancelar"):
            st.session_state["_confirmar_zerar"] = False
            st.rerun()
