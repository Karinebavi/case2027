# -*- coding: utf-8 -*-
"""Tela de login — o que a pessoa vê antes de entrar."""
import os
import streamlit as st

from regras import auth


def mostrar():
    # espaço reservado pro logo do Instituto (assets/logo.png)
    logo = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
    if os.path.exists(logo):
        st.image(logo, width=180)

    st.title("CASE 2027")
    st.caption("Acesso restrito à equipe. Informe a senha para continuar.")

    with st.form("login"):
        senha = st.text_input("Senha de acesso", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        if auth.conferir(senha):
            auth.entrar()
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")
