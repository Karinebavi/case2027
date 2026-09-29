# -*- coding: utf-8 -*-
"""
Ponte entre as telas e as regras, com cache para aguentar bases grandes.
O cálculo pesado (pontuar cada inscrição) só roda de novo quando os dados
mudam — não a cada clique. Assim 1000+ inscrições continuam rápidas.
"""
import json
import time

import streamlit as st

from regras import pontuacao, classificacao, processo, funil, nuvem

# na nuvem, relê o que os outros mentores salvaram a cada X segundos
_RELER_A_CADA = 30


@st.cache_data(show_spinner=False)
def _pontuar(dados, mapa):
    return pontuacao.calcular(dados, mapa)


def processar(dados, mapa, vagas):
    """Devolve o DataFrame com nota, posição e situação de cada inscrição."""
    scored = _pontuar(dados, mapa)
    return classificacao.classificar(scored, vagas)


def _foto(est):
    return {d: processo.serializar(r) for d, r in est.items()}


def reler_se_preciso():
    """Na nuvem, descarta a cópia da sessão se ficou velha, para enxergar o
    que outros mentores salvaram. Chamado UMA vez no topo de cada execução
    (app.py) — nunca no meio de uma tela, para não perder uma edição."""
    velho = time.time() - st.session_state.get("_processo_lido_em", 0) > _RELER_A_CADA
    if nuvem.ativo() and velho:
        st.session_state.pop("processo", None)


def estado():
    """Carrega o estado do processo na sessão (se preciso) e o devolve."""
    if "processo" not in st.session_state:
        est = processo.carregar()
        st.session_state["processo"] = est
        st.session_state["_processo_foto"] = _foto(est)
        st.session_state["_processo_lido_em"] = time.time()
    return st.session_state["processo"]


_RESUMO = ["doc_status", "doc_motivo", "entrevista_mentor", "entrevista_compareceu",
           "entrevista_status", "entrevista_motivo", "interesse"]


def salvar_estado():
    """Grava só as organizações que mudaram e anota cada mudança no histórico."""
    est = st.session_state.get("processo", {})
    foto = st.session_state.get("_processo_foto", {})
    atual = _foto(est)
    vazio = processo.serializar(processo._padrao())
    # registros em branco criados só por abrir a organização não contam
    mudou = [d for d, js in atual.items()
             if foto.get(d) != js and not (d not in foto and js == vazio)]
    if not mudou:
        return
    processo.salvar(est, so_estes=mudou)
    for d in mudou:
        antes = json.loads(foto[d]) if d in foto else processo._padrao()
        depois = est[d]
        campos = {k: depois.get(k) for k in _RESUMO if antes.get(k) != depois.get(k)}
        if antes.get("doc_check") != depois.get("doc_check"):
            campos["doc_check"] = depois.get("doc_check")
        for k in ("doc_obs", "entrevista_parecer", "entrevista_relato"):
            if antes.get(k) != depois.get(k):
                campos[k] = "(alterado)"
        nuvem.registrar("processo", {"cnpj": d, "mudancas": campos})
    st.session_state["_processo_foto"] = atual


def funil_df(dados, mapa, vagas, pool_size):
    """DataFrame com a fase de cada organização (pool, documental, entrevista...)."""
    scored = processar(dados, mapa, vagas)
    return funil.montar(scored, estado(), pool_size, vagas)
