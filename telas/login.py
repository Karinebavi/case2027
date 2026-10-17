# -*- coding: utf-8 -*-
"""Tela de login — cartão central moderno (estilo Polaris), com a marca do CASE."""
import base64
import os

import streamlit as st

from regras import auth

_LOGO = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")


def _logo_html():
    if os.path.exists(_LOGO):
        try:
            b64 = base64.b64encode(open(_LOGO, "rb").read()).decode()
            return f'<img class="login-logo" src="data:image/png;base64,{b64}" alt="CASE 2027"/>'
        except Exception:
            pass
    return '<div class="login-marca">CASE 2027</div>'


def _css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@700;800&family=Nunito+Sans:wght@400;600;700;900&display=swap');

    [data-testid="stSidebar"], [data-testid="stHeader"] { display: none !important; }
    .stApp {
        background:
          radial-gradient(900px 500px at 15% -10%, #EDE9FE 0%, rgba(237,233,254,0) 55%),
          radial-gradient(900px 520px at 100% 0%, #FCE7F3 0%, rgba(252,231,243,0) 50%),
          #F5F3FB !important;
        font-family: 'Nunito Sans', system-ui, 'Segoe UI', sans-serif !important;
    }
    .block-container { max-width: 480px !important; padding-top: 5vh !important; }

    /* o formulário vira o cartão central */
    [data-testid="stForm"] {
        background: #FFFFFF; border-radius: 22px; padding: 34px 34px 28px !important;
        border: 1px solid #ECE9FB;
        box-shadow: 0 1px 2px rgba(42,25,70,.04), 0 18px 48px -18px rgba(147,51,234,.28);
    }
    .login-logo { display:block; height:46px; margin: 0 auto 2px; }
    .login-marca { text-align:center; font-family:'Baloo 2',sans-serif; font-weight:800; font-size:27px; color:#9333EA; letter-spacing:-.5px; }
    .login-pill {
        width: max-content; margin: 10px auto 2px; padding: 4px 12px; border-radius: 999px;
        background: #ECFDF5; color: #047857; font-size: 11px; font-weight: 700; letter-spacing:.5px;
        border: 1px solid #A7F3D0;
    }
    .login-pill .dot { color:#10B981; }
    .login-h { text-align:center; font-family:'Baloo 2',sans-serif; font-size:28px; font-weight:800; color:#2A1A46; margin:12px 0 4px; }
    .login-sub { text-align:center; color:#6B6780; font-size:14px; margin:0 0 18px; }
    .login-lab { font-weight:700; color:#3E087C; font-size:13px; margin:2px 0 -6px; }

    /* campo de senha */
    [data-testid="stForm"] div[data-baseweb="input"] {
        border-radius: 10px !important; border:1px solid #E7E3F3 !important; background:#fff !important;
    }
    [data-testid="stForm"] div[data-baseweb="input"]:focus-within {
        border-color:#9333EA !important; box-shadow:0 0 0 3px rgba(147,51,234,.20) !important;
    }
    [data-testid="stForm"] input { font-size:15px !important; padding:6px 4px !important; }

    /* botão Entrar — gradiente roxo do CASE */
    [data-testid="stForm"] .stFormSubmitButton > button {
        width:100%; border:none !important; border-radius:11px !important; padding:11px 0 !important;
        font-weight:700 !important; font-size:15.5px !important; color:#fff !important;
        background: linear-gradient(100deg, #7E22CE 0%, #9333EA 55%, #A855F7 100%) !important;
        box-shadow: 0 10px 22px -10px rgba(147,51,234,.60) !important; margin-top:6px;
        transition: filter .15s ease, transform .05s ease;
    }
    [data-testid="stForm"] .stFormSubmitButton > button:hover { filter:brightness(1.06); }
    [data-testid="stForm"] .stFormSubmitButton > button:active { transform: translateY(1px); }
    .login-foot { text-align:center; color:#9A94B0; font-size:12px; margin-top:14px; }
    </style>
    """, unsafe_allow_html=True)


def mostrar():
    _css()
    with st.form("login"):
        st.markdown(_logo_html(), unsafe_allow_html=True)
        st.markdown('<div class="login-pill"><span class="dot">●</span> ACESSO SEGURO · CASE 2027</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="login-h">Bem-vindo de volta</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Entre para acessar a seleção de entidades do CASE 2027.</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="login-lab">Senha de acesso</div>', unsafe_allow_html=True)
        senha = st.text_input("Senha de acesso", type="password", label_visibility="collapsed",
                              placeholder="Digite a senha da equipe")
        entrar = st.form_submit_button("Entrar  →", type="primary", width="stretch")
        st.markdown('<div class="login-foot">Uso interno · Instituto Imaginação</div>', unsafe_allow_html=True)

    if entrar:
        if auth.conferir(senha):
            auth.entrar()
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")
