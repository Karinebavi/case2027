# -*- coding: utf-8 -*-
"""
Sistema CASE 2027 — índice do sistema.
=====================================
Faz duas coisas:
  1) o portão de login (só entra quem sabe a senha);
  2) a navegação entre as telas, em seções, cada uma com endereço próprio
     (o "voltar" do navegador funciona e dá para mandar o link de uma tela).

Cada tela mora no seu próprio arquivo, dentro da pasta telas/.
A lógica (regras) fica separada, dentro de regras/.
"""
import os

import streamlit as st

from regras import auth, nuvem, feedback
from telas import (login, importar, resultado, analises, documental,
                   entrevistas, fichas, dashboard, _calculo, _ui)
import tema

st.set_page_config(page_title="CASE 2027", page_icon=":material/sports_soccer:", layout="wide")
tema.aplicar()

# Logo oficial do CASE no topo da barra lateral (e canto superior)
_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo-case.png")
if os.path.exists(_LOGO):
    try:
        st.logo(_LOGO, size="large")
    except Exception:
        pass

# ---------- navegação: as etapas da seleção, na ordem do processo ----------
PAGINAS = {
    1: st.Page(importar.mostrar, title="Inscrições", icon=":material/inbox:", url_path="inscricoes",
               default=True),
    2: st.Page(resultado.mostrar, title="Ranking", icon=":material/leaderboard:", url_path="ranking"),
    3: st.Page(documental.mostrar, title="Documentos", icon=":material/folder_open:", url_path="documentos"),
    4: st.Page(analises.mostrar, title="Patrocinador", icon=":material/handshake:", url_path="patrocinador"),
    5: st.Page(entrevistas.mostrar, title="Entrevistas", icon=":material/forum:", url_path="entrevistas"),
    6: st.Page(fichas.mostrar, title="Selecionadas", icon=":material/workspace_premium:",
               url_path="selecionadas"),
    7: st.Page(dashboard.mostrar, title="Painel", icon=":material/monitoring:", url_path="painel"),
}
_ui.PAGINAS = PAGINAS

# ---------- portão de login ----------
if not auth.esta_logado():
    # A navegação existe (escondida) também no login: quem abriu o link de uma
    # tela cai nela depois de digitar a senha.
    st.navigation(list(PAGINAS.values()), position="hidden")
    login.mostrar()
    st.stop()

# ---------- dados: base de inscrições e estado do processo ----------
_calculo.reler_se_preciso()
if "dados" not in st.session_state:
    importar._carregar_base_para_sessao()

pagina = st.navigation({"Seleção": [PAGINAS[i] for i in range(1, 7)],
                        "Acompanhar": [PAGINAS[7]]}, position="sidebar")

with st.sidebar:
    st.caption(_ui.contexto())
    st.caption(f":material/cloud_done: Salvo na nuvem · {nuvem.quem()}" if nuvem.ativo()
               else ":material/computer: Salvo neste computador")
    with st.expander("Enviar feedback", icon=":material/feedback:"):
        if st.session_state.pop("_fb_ok", False):
            st.success("Enviado. Obrigado!")
            st.session_state["fb_texto"] = ""
        st.text_area("Feedback", key="fb_texto", height=80, label_visibility="collapsed",
                     placeholder="O que confundiu ou pode melhorar nesta tela?")
        if st.button("Enviar feedback", key="fb_btn"):
            if feedback.registrar(st.session_state.get("fb_texto", ""), tela=pagina.title):
                st.session_state["_fb_ok"] = True
                st.rerun()
            else:
                st.caption("Escreva algo antes de enviar.")
    if st.button("Sair", icon=":material/logout:", type="tertiary"):
        auth.sair()
        st.rerun()

pagina.run()
