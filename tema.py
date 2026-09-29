# -*- coding: utf-8 -*-
"""
A "cara" do sistema — cores e estilo.
Cor de destaque provisória (azul institucional). TROCAR pelas cores
oficiais do CASE/Instituto em .streamlit/config.toml e na variável abaixo.
"""
import streamlit as st

ACENTO = "#1F4E79"          # cor institucional provisória
ACENTO_CLARO = "#EAF1F8"


def aplicar():
    st.markdown(
        f"""
        <style>
        .block-container {{ max-width: 1200px; padding-top: 1.1rem; }}

        /* Cabeçalho institucional */
        .case-header {{
            background: {ACENTO}; color: #FFFFFF; border-radius: 12px;
            padding: 14px 20px; margin-bottom: 16px;
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;
        }}
        .case-header .t {{ font-size: 18px; font-weight: 700; letter-spacing: .2px; }}
        .case-header .c {{ font-size: 13px; opacity: .9; }}

        /* Cards de indicador */
        [data-testid="stMetric"] {{
            background: #FFFFFF; border: 1px solid #E3E8EC; border-radius: 12px;
            padding: 14px 16px;
        }}
        [data-testid="stMetricValue"] {{ font-weight: 800; color: {ACENTO}; }}
        [data-testid="stMetricLabel"] {{ color: #5A6B73; }}

        /* Cabeçalhos de seção */
        h1, h2, h3 {{ color: #1B2A33; }}
        h2 {{ border-bottom: 2px solid {ACENTO_CLARO}; padding-bottom: 4px; }}

        /* Caixa de seleção da Fase 2 */
        .case-box {{
            background: {ACENTO_CLARO}; border: 1px solid #D6E2F0; border-radius: 12px;
            padding: 12px 16px; margin: 6px 0 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
