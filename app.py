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
import streamlit as st

from regras import auth
from telas import (login, importar, resultado, analises, documental,
                   entrevistas, fichas, dashboard)
import tema

st.set_page_config(page_title="CASE 2027", layout="wide")
tema.aplicar()

# ---------- portão de login ----------
if not auth.esta_logado():
    login.mostrar()
    st.stop()

# ---------- navegação (as telas da Fase 1) ----------
with st.sidebar:
    st.markdown("### CASE 2027")
    st.caption("Seleção 2027 · uso interno")
    escolha = st.radio(
        "Navegação",
        ["1 · Importar", "2 · Resultado", "3 · Análises", "4 · Documental",
         "5 · Entrevistas", "6 · Fichas", "7 · Dashboard"],
        label_visibility="collapsed",
    )
    st.divider()
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
