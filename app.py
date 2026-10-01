# -*- coding: utf-8 -*-
"""
Sistema CASE 2027 — esqueleto (Passo 0)
=======================================
Este arquivo é só o "índice" do sistema. Ele faz duas coisas:
  1) o portão de login (só entra quem sabe a senha);
  2) a navegação entre as telas.

Cada tela mora no seu próprio arquivo, dentro da pasta telas/.
A lógica (regras) fica separada, dentro de regras/. Assim, mexer numa
tela não quebra a outra, e as regras podem ser reaproveitadas depois.
"""
import os

import streamlit as st

from regras import auth, nuvem
from telas import (login, importar, resultado, analises, documental,
                   entrevistas, fichas, dashboard, _calculo)
import tema

st.set_page_config(page_title="CASE 2027", layout="wide")
tema.aplicar()

# Logo oficial do CASE no topo da barra lateral (e canto superior)
_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo-case.png")
if os.path.exists(_LOGO):
    try:
        st.logo(_LOGO, size="large")
    except Exception:
        pass

# ---------- portão de login ----------
if not auth.esta_logado():
    login.mostrar()
    st.stop()

# ---------- dados: base de inscrições e estado do processo ----------
_calculo.reler_se_preciso()
if "dados" not in st.session_state:
    importar._carregar_base_para_sessao()

# ---------- navegação (as telas da Fase 1) ----------
with st.sidebar:
    st.caption("Seleção 2027 · uso interno")
    escolha = st.radio(
        "Navegação",
        ["1 · Importar", "2 · Resultado", "3 · Análises", "4 · Documental",
         "5 · Entrevistas", "6 · Fichas", "7 · Dashboard"],
        label_visibility="collapsed",
    )
    st.divider()
    if nuvem.ativo():
        st.caption(f"Dados salvos na nuvem · {nuvem.quem()}")
    else:
        st.caption("Dados salvos neste computador")
    if st.button("Sair"):
        auth.sair()
        st.rerun()

# mostra a tela escolhida
if escolha.startswith("1"):
    importar.mostrar()
elif escolha.startswith("2"):
    resultado.mostrar()
elif escolha.startswith("3"):
    analises.mostrar()
elif escolha.startswith("4"):
    documental.mostrar()
elif escolha.startswith("5"):
    entrevistas.mostrar()
elif escolha.startswith("6"):
    fichas.mostrar()
else:
    dashboard.mostrar()
