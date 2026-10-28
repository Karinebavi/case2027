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

# --- Paletas para GRÁFICOS e ESTADOS (use estas; não escreva hex solto nas telas) ---
# Sequência de categorias nos gráficos (na marca: roxo, laranja, lavandas, escuro).
SEQ_CASE = ["#9333EA", "#FF9A2D", "#B57BEE", "#3E087C", "#C2410C", "#6B6780", "#D8D8FF"]
ESCALA_ROXO = ["#F2F0FC", "#9333EA"]      # escala contínua (mapa/heatmap)
PRIMARIA_GRAF = ROXO                       # 1ª cor de destaque em gráficos
SECUNDARIA_GRAF = LARANJA                  # 2ª cor (comparativo/média)

# Cor da SITUAÇÃO — fonte ÚNICA (antes estava repetida em 3 telas, divergindo).
# Versão pastel (fundo, texto) para células de tabela:
SEMAFORO = {
    "Classificada": ("#E4F1E8", "#1B5E20"),
    "Fila de espera": ("#FBF1DD", "#7A5412"),
    "Fora do perfil": ("#ECECEC", "#555555"),
    "Inelegível": ("#F6E4E4", "#8A2A2A"),
}
# Versão saturada (uma cor) para barras/fatias de gráfico:
SEMAFORO_FORTE = {
    "Classificada": "#2E7D32", "Fila de espera": "#C99A2E",
    "Fora do perfil": "#9E9E9E", "Inelegível": "#B84A4A",
}
# "Quadradinhos" de status (fundo, texto) da Documental — mesma paleta do semáforo.
COR_STATUS = {
    "verde": SEMAFORO["Classificada"], "amarelo": SEMAFORO["Fila de espera"],
    "vermelho": SEMAFORO["Inelegível"], "cinza": SEMAFORO["Fora do perfil"],
}


def aplicar():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;700&family=Nunito+Sans:wght@400;600;700;900&display=swap');

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

        /* Corpo em Nunito Sans; controles de formulário recebem explicitamente.
           NÃO citar 'span' nem classes st-* (quebra os ícones Material Symbols). */
        html, body, .stApp, button, input, textarea, select {{
            font-family: 'Nunito Sans', -apple-system, Segoe UI, Roboto, sans-serif;
            font-size: 15.5px;
        }}
        .stApp {{ background: var(--bg); color: var(--fg); }}
        .block-container {{ max-width: 1160px; padding-top: 1.1rem; }}

        /* Títulos na fonte amigável (Baloo 2) e no roxo escuro do CASE.
           Prefixo .stApp + !important para vencer o estilo padrão do Streamlit. */
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
            font-family: 'Baloo 2', sans-serif !important;
            color: var(--heading) !important; font-weight: 700; letter-spacing: 0;
        }}
        .stApp h1 {{ font-size: 2.15rem; line-height: 1.15; }}
        .stApp h2 {{ font-size: 1.45rem; border-bottom: 3px solid var(--accent); padding-bottom: 5px; display: inline-block; }}
        .stApp h3 {{ font-size: 1.18rem; }}
        .stCaption, [data-testid="stCaptionContainer"] {{ color: var(--muted-fg); }}

        /* Cabeçalho institucional — faixa lavanda com acento roxo à esquerda */
        .case-header {{
            background: linear-gradient(100deg, {LAVANDA} 0%, #FBF8F2 100%); color: var(--heading);
            border: 1px solid var(--border); border-left: 5px solid var(--primary);
            border-radius: var(--radius); box-shadow: var(--shadow);
            padding: 14px 20px; margin-bottom: 14px;
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;
        }}
        .case-header .t {{ font-family: 'Baloo 2', sans-serif; font-size: 19px; font-weight: 700; }}
        .case-header .c {{ font-size: 13px; color: var(--muted-fg); font-weight: 600; }}

        /* Guia "passo a passo" no topo de cada tela */
        .case-steps {{ display: flex; align-items: center; flex-wrap: wrap; gap: 2px; margin: 2px 0 10px; }}
        .case-steps .step {{ display: flex; flex-direction: column; align-items: center; min-width: 58px; }}
        .case-steps .bola {{
            width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
            justify-content: center; font-family: 'Baloo 2', sans-serif; font-weight: 700; font-size: 13px;
            border: 2px solid var(--border); background: #fff; color: var(--muted-fg);
        }}
        .case-steps .rot {{ font-size: 10.5px; margin-top: 3px; color: var(--muted-fg); text-align: center; font-weight: 600; }}
        .case-steps .step.cur .bola {{ background: var(--primary); border-color: var(--primary); color: #fff; box-shadow: 0 0 0 4px var(--ring); }}
        .case-steps .step.cur .rot {{ color: var(--heading); font-weight: 700; }}
        .case-steps .step.done .bola {{ background: {LAVANDA_CHIP}; border-color: {LAVANDA_CHIP}; color: var(--primary); }}
        .case-steps .liga {{ flex: 1; height: 2px; background: var(--border); min-width: 10px; margin-top: -16px; }}

        /* Caixa "o que fazer aqui" */
        .case-guia {{
            background: #FFF7EA; border: 1px solid #FCE3BF; border-left: 4px solid var(--accent);
            border-radius: var(--radius); padding: 10px 14px; margin-bottom: 14px; font-size: 14px;
        }}
        .case-guia b {{ color: var(--heading); font-family: 'Baloo 2', sans-serif; }}

        /* Cartão-resumo do parecer (destaque no topo da análise documental) */
        .case-resumo {{
            border-radius: 14px; padding: 18px 22px; margin: 2px 0 16px; color: #FFFFFF;
            box-shadow: 0 8px 22px rgba(62,8,124,.18);
        }}
        .case-resumo .selo {{
            display: inline-block; background: rgba(255,255,255,.22); border-radius: 999px;
            padding: 3px 12px; font-family: 'Baloo 2', sans-serif; font-weight: 700;
            font-size: 11.5px; letter-spacing: .6px; margin-bottom: 9px;
        }}
        .case-resumo .res {{ font-family: 'Baloo 2', sans-serif; font-size: 1.7rem; font-weight: 800; line-height: 1.05; }}
        .case-resumo .ent {{ font-size: 15.5px; font-weight: 700; margin-top: 3px; opacity: .97; }}
        .case-resumo .fr {{ font-size: 13.5px; margin-top: 7px; opacity: .95; }}
        .case-resumo .destaques {{ margin-top: 13px; display: flex; flex-direction: column; gap: 7px; }}
        .case-resumo .d {{
            background: rgba(255,255,255,.14); border-left: 3px solid rgba(255,255,255,.75);
            border-radius: 8px; padding: 7px 11px; font-size: 13px;
        }}
        .case-resumo .d b {{ font-family: 'Baloo 2', sans-serif; font-weight: 700; }}
        .case-resumo .d .tr {{ display: block; font-size: 12px; opacity: .9; margin-top: 2px; font-style: italic; }}

        /* Cards de indicador (metric) */
        [data-testid="stMetric"] {{
            background: #FFFFFF; border: 1px solid var(--border); border-radius: var(--radius);
            padding: 14px 16px; box-shadow: var(--shadow);
        }}
        [data-testid="stMetricValue"] {{ font-family: 'Baloo 2', sans-serif; font-weight: 700; color: var(--heading); font-size: 1.95rem; }}
        /* rótulo do indicador: quebra linha em vez de cortar com "…" */
        [data-testid="stMetricLabel"] {{ color: var(--muted-fg); font-weight: 500; }}
        [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{
            white-space: normal !important; overflow: visible !important;
            text-overflow: clip !important; line-height: 1.25;
        }}
        /* rótulo de botão não corta (ex.: "Testar com exemplos") */
        .stButton > button p, .stDownloadButton > button p {{ white-space: normal !important; }}

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
