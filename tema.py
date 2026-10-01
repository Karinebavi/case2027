# -*- coding: utf-8 -*-
"""
A "cara" do sistema — identidade visual do CASE (case.org.br): roxo como cor
principal, lavanda nas superfícies, laranja como acento e tipografia amigável.
Estrutura limpa (cartões com borda arredondada), legível para dados.

Para ajustar a cor principal, mude ROXO aqui e primaryColor no config.toml.
"""
import streamlit as st

ROXO = "#9333EA"            # cor principal do CASE (botões, acento)
ROXO_ESCURO = "#3E087C"     # títulos
ROXO_HOVER = "#7E22CE"
LARANJA = "#FF9A2D"         # acento (traço dos títulos, como no site)
LAVANDA = "#F2F0FC"         # superfície suave
LAVANDA_CHIP = "#EAE4FB"


def aplicar():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@500;600;700&display=swap');

        :root {{
            --bg: #FFFFFF;
            --fg: #221F2E;             /* texto (quase preto, levemente roxo) */
            --muted: {LAVANDA};        /* superfície secundária (lavanda) */
            --muted-fg: #6B6780;       /* texto secundário */
            --border: #E7E3F3;         /* bordas (lavanda acinzentada) */
            --primary: {ROXO};
            --primary-fg: #FFFFFF;
            --heading: {ROXO_ESCURO};
            --accent: {LARANJA};
            --radius: 10px;
            --ring: rgba(147, 51, 234, 0.20);
            --shadow: 0 1px 2px rgba(42, 25, 70, 0.04), 0 1px 3px rgba(42, 25, 70, 0.07);
        }}

        /* Inter via herança a partir do .stApp; controles de formulário recebem
           explicitamente. NÃO citar 'span' nem classes st-* (quebra os ícones). */
        html, body, .stApp, button, input, textarea, select {{
            font-family: 'Inter', -apple-system, Segoe UI, Roboto, sans-serif;
        }}
        .stApp {{ background: var(--bg); color: var(--fg); }}
        .block-container {{ max-width: 1160px; padding-top: 1.1rem; }}

        /* Títulos na fonte amigável (Poppins) e no roxo escuro do CASE.
           Prefixo .stApp + !important para vencer o estilo padrão do Streamlit. */
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
            font-family: 'Poppins', 'Inter', sans-serif !important;
            color: var(--heading) !important; font-weight: 600; letter-spacing: -0.01em;
        }}
        .stApp h1 {{ font-size: 1.9rem; font-weight: 700 !important; }}
        .stApp h2 {{ font-size: 1.3rem; border-bottom: 3px solid var(--accent); padding-bottom: 6px; display: inline-block; }}
        .stApp h3 {{ font-size: 1.08rem; }}
        .stCaption, [data-testid="stCaptionContainer"] {{ color: var(--muted-fg); }}

        /* Cabeçalho institucional — faixa lavanda com acento roxo à esquerda */
        .case-header {{
            background: {LAVANDA}; color: var(--heading);
            border: 1px solid var(--border); border-left: 4px solid var(--primary);
            border-radius: var(--radius); box-shadow: var(--shadow);
            padding: 13px 18px; margin-bottom: 16px;
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;
        }}
        .case-header .t {{ font-family: 'Poppins', sans-serif; font-size: 16px; font-weight: 600; }}
        .case-header .c {{ font-size: 13px; color: var(--muted-fg); }}

        /* Cards de indicador (metric) */
        [data-testid="stMetric"] {{
            background: #FFFFFF; border: 1px solid var(--border); border-radius: var(--radius);
            padding: 14px 16px; box-shadow: var(--shadow);
        }}
        [data-testid="stMetricValue"] {{ font-family: 'Poppins', sans-serif; font-weight: 600; color: var(--heading); font-size: 1.7rem; }}
        [data-testid="stMetricLabel"] {{ color: var(--muted-fg); font-weight: 500; }}

        /* Botões — padrão branco com borda; principal no roxo */
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
            border-radius: var(--radius); font-weight: 500; border: 1px solid var(--border);
            background: #FFFFFF; color: var(--fg); box-shadow: var(--shadow);
            transition: background .15s ease, border-color .15s ease;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
            background: var(--muted); border-color: #D9D2F0; color: var(--heading);
        }}
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
            background: var(--primary); color: var(--primary-fg); border-color: var(--primary);
        }}
        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
            background: {ROXO_HOVER}; border-color: {ROXO_HOVER}; color: #FFFFFF;
        }}
        .stButton > button:focus, .stDownloadButton > button:focus {{
            box-shadow: 0 0 0 3px var(--ring); outline: none;
        }}

        /* Campos — borda neutra + anel roxo no foco */
        div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {{
            border-radius: var(--radius) !important; border-color: var(--border) !important;
            background: #FFFFFF !important;
        }}
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within,
        div[data-baseweb="textarea"]:focus-within {{
            border-color: var(--primary) !important; box-shadow: 0 0 0 3px var(--ring) !important;
        }}
        .stTextInput input, .stNumberInput input, .stDateInput input, textarea {{ color: var(--fg); }}

        /* Expansores e cartões com borda */
        [data-testid="stExpander"] details {{
            border: 1px solid var(--border) !important; border-radius: var(--radius) !important;
            background: #FFFFFF; box-shadow: var(--shadow); overflow: hidden;
        }}
        [data-testid="stExpander"] summary {{ font-weight: 500; }}
        [data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: var(--radius) !important; }}

        /* Tabelas */
        [data-testid="stDataFrame"], [data-testid="stTable"] {{
            border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden;
        }}

        /* Barra lateral — lavanda bem clara com borda à direita */
        [data-testid="stSidebar"] {{ background: #FBFAFE; border-right: 1px solid var(--border); }}
        [data-testid="stSidebar"] .stRadio label {{ font-size: 0.95rem; }}

        hr {{ border-color: var(--border); }}

        /* Chips do multiselect no lavanda/roxo */
        [data-baseweb="tag"] {{
            background: {LAVANDA_CHIP} !important; color: var(--primary) !important;
            border-radius: 6px !important;
        }}

        /* Barra de progresso no roxo */
        [data-testid="stProgress"] [role="progressbar"] > div {{ background-color: var(--primary); }}

        /* Links no roxo */
        a, a:visited {{ color: var(--primary); }}

        .case-box {{
            background: var(--muted); border: 1px solid var(--border); border-radius: var(--radius);
            padding: 12px 16px; margin: 6px 0 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
