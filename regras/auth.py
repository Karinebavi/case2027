# -*- coding: utf-8 -*-
"""
Motor de login — confere a senha. NÃO tem tela aqui (só regra).

A senha real vem de .streamlit/secrets.toml (chave senha_app).
Enquanto você não configurar, o sistema usa uma senha de teste,
pra conseguir abrir. A comparação é feita de forma segura.
"""
import hmac
import streamlit as st

SENHA_TESTE = "case2027"  # vale só até você configurar a senha real


def _senha_valida() -> str:
    # Se .streamlit/secrets.toml existir e tiver 'senha_app', usa ela.
    # Se não existir, cai na senha de teste (sem quebrar o app).
    try:
        return str(st.secrets["senha_app"])
    except Exception:
        return SENHA_TESTE


def conferir(tentativa: str) -> bool:
    """Compara a senha digitada com a correta, de forma segura."""
    return hmac.compare_digest(str(tentativa), _senha_valida())


def esta_logado() -> bool:
    return st.session_state.get("logado", False)


def entrar() -> None:
    st.session_state["logado"] = True


def sair() -> None:
    st.session_state["logado"] = False
