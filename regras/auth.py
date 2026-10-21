# -*- coding: utf-8 -*-
"""
Motor de login — confere a senha. NÃO tem tela aqui (só regra).

A senha real vem de .streamlit/secrets.toml (chave senha_app).
Enquanto você não configurar, o sistema usa uma senha de teste,
pra conseguir abrir. A comparação é feita de forma segura.
"""
import hmac
import time

import streamlit as st

SENHA_TESTE = "case2027"  # vale só até você configurar a senha real
MAX_TENTATIVAS = 5        # a partir daqui, impõe espera (anti-força-bruta)


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


def espera_restante() -> float:
    """Segundos ainda a aguardar após tentativas demais (0 = liberado)."""
    n = st.session_state.get("_tentativas", 0)
    if n < MAX_TENTATIVAS:
        return 0.0
    limite = min(60, 2 ** (n - MAX_TENTATIVAS + 1))   # backoff: 2, 4, 8… até 60s
    passou = time.time() - st.session_state.get("_ultima_tentativa", 0.0)
    return max(0.0, limite - passou)


def registrar_falha() -> None:
    st.session_state["_tentativas"] = st.session_state.get("_tentativas", 0) + 1
    st.session_state["_ultima_tentativa"] = time.time()


def limpar_tentativas() -> None:
    st.session_state.pop("_tentativas", None)
    st.session_state.pop("_ultima_tentativa", None)


def esta_logado() -> bool:
    return st.session_state.get("logado", False)


def entrar() -> None:
    st.session_state["logado"] = True


def sair() -> None:
    st.session_state["logado"] = False
