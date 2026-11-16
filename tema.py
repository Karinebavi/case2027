# -*- coding: utf-8 -*-
"""
A "cara" do sistema — identidade visual do CASE (case.org.br): roxo como cor
principal, lavanda nas superfícies, laranja como acento.

Fontes, cores, bordas e raios ficam no tema oficial (.streamlit/config.toml).
Aqui só o que o tema não alcança: a cor dos títulos, legendas legíveis
(o Streamlit as deixa 40% transparentes), os cartões de indicador, a faixa de
andamento e o idioma da página (português, para leitores de tela).

Para ajustar a cor principal, mude ROXO aqui e primaryColor no config.toml.
"""
import streamlit as st

ROXO = "#9333EA"            # cor principal do CASE (botões, acento)
ROXO_ESCURO = "#3E087C"     # títulos
ROXO_HOVER = "#7E22CE"
LARANJA = "#FF9A2D"         # acento
LAVANDA = "#F2F0FC"         # superfície suave
LAVANDA_CHIP = "#EAE4FB"

# --- Paletas para GRÁFICOS e ESTADOS (use estas; não escreva hex solto nas telas) ---
SEQ_CASE = ["#9333EA", "#FF9A2D", "#B57BEE", "#3E087C", "#C2410C", "#6B6780", "#D8D8FF"]
ESCALA_ROXO = ["#F2F0FC", "#9333EA"]      # escala contínua (mapa/heatmap)
PRIMARIA_GRAF = ROXO                       # 1ª cor de destaque em gráficos
SECUNDARIA_GRAF = LARANJA                  # 2ª cor (comparativo/média)

# Cor da SITUAÇÃO — fonte ÚNICA. Versão pastel (fundo, texto) para células de tabela:
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

_CSS = f"""
<style>
:root {{ --heading: {ROXO_ESCURO}; --muted-fg: #625E75; --border: #E4DFF2; --lavanda: {LAVANDA}; }}

/* Títulos no roxo escuro da marca (a fonte vem do tema) */
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ color: var(--heading); }}
.stApp h1 {{ letter-spacing: -0.01em; margin-bottom: 0.1rem; }}

/* Legendas legíveis: sem a transparência padrão (contraste 2,4 -> 6,1) */
[data-testid="stCaptionContainer"] {{ opacity: 1 !important; color: var(--muted-fg); }}

/* Cartões de indicador */
[data-testid="stMetric"] {{
    background: #FFFFFF; border: 1px solid var(--border); border-radius: 10px; padding: 12px 16px;
}}
[data-testid="stMetricValue"] {{ color: var(--heading); }}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{
    white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}}

/* Faixa de andamento da seleção (links para cada etapa, com os números) */
.st-key-andamento {{ margin: 0.25rem 0 0.75rem; }}
.st-key-andamento [data-testid="stPageLink"] a {{
    background: var(--lavanda); border: 1px solid var(--border); border-radius: 999px;
    padding: 0.15rem 0.75rem;
}}
.st-key-andamento [data-testid="stPageLink"] a:hover {{ border-color: {ROXO}; }}
.st-key-andamento [data-testid="stPageLink"] a[aria-disabled="true"],
.st-key-andamento [data-testid="stPageLink"] [disabled] {{
    background: {ROXO}; border-color: {ROXO}; opacity: 1;
}}
.st-key-andamento [data-testid="stPageLink"] a[aria-disabled="true"] *,
.st-key-andamento [data-testid="stPageLink"] [disabled] * {{ color: #FFFFFF !important; }}

/* Seleção de texto e barra de progresso na cor da marca */
::selection {{ background: {LAVANDA_CHIP}; color: {ROXO_ESCURO}; }}
[data-testid="stProgress"] [role="progressbar"] > div {{ background-color: {ROXO}; }}
</style>
"""

# A página é em português (leitores de tela pronunciam certo).
_IDIOMA = "<script>document.documentElement.lang = 'pt-BR';</script>"


def aplicar():
    st.html(_CSS)
    st.html(_IDIOMA, unsafe_allow_javascript=True)
