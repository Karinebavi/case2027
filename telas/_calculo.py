# -*- coding: utf-8 -*-
"""
Ponte entre as telas e as regras, com cache para aguentar bases grandes.
O cálculo pesado (pontuar cada inscrição) só roda de novo quando os dados
mudam — não a cada clique. Assim 1000+ inscrições continuam rápidas.
"""
import streamlit as st

from regras import pontuacao, classificacao, processo, funil


@st.cache_data(show_spinner=False)
def _pontuar(dados, mapa):
    return pontuacao.calcular(dados, mapa)


def processar(dados, mapa, vagas):
    """Devolve o DataFrame com nota, posição e situação de cada inscrição."""
    scored = _pontuar(dados, mapa)
    return classificacao.classificar(scored, vagas)


def estado():
    """Carrega o estado do processo na sessão (uma vez) e o devolve."""
    if "processo" not in st.session_state:
        st.session_state["processo"] = processo.carregar()
    return st.session_state["processo"]


def salvar_estado():
    processo.salvar(st.session_state.get("processo", {}))


def funil_df(dados, mapa, vagas, pool_size):
    """DataFrame com a fase de cada organização (pool, documental, entrevista...)."""
    scored = processar(dados, mapa, vagas)
    return funil.montar(scored, estado(), pool_size, vagas)
