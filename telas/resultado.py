# -*- coding: utf-8 -*-
"""
Tela 2 — Ranking (pontuação e classificação)
===========================================
UMA lista só: todas as organizações, com a nota, a situação, TODOS os problemas
(eliminatórias, CNPJ inválido/repetido, campo em branco, avisos) na mesma linha e
todas as respostas do formulário — para ver por que uma subiu e outra não.

- Eliminada (Regulamento 8.1): respondeu "Não" numa das perguntas 14 a 19 ou abriu o
  CNPJ depois de 01/03/2026. Continua visível, com a nota e o motivo, sem posição e
  fora da Fase 2.
- As mais bem colocadas (padrão 30) vão à Fase 2 (documentos); a meta são as VAGAS.
- Clicando em UMA linha: a ficha completa. Em DUAS ou mais: comparação lado a lado.
"""
import pandas as pd
import streamlit as st

from base import campos as campos_def
from telas import _calculo, _ui
from regras import validacao, exportacao
import tema
from regras import pontuacao
from regras.memoria import so_digitos


@st.cache_data(show_spinner=False)
def _conferencia(dados, mapa):
    return pontuacao.conferencia(dados, mapa)


SITUACOES = ["Classificada", "Fila de espera", "Eliminada"]
CORES_SITUACAO = {k: f"background-color:{bg};color:{fg}" for k, (bg, fg) in tema.SEMAFORO.items()}
BLOCO_COL = {"b1": "Elaboração", "b2": "Execução", "b3": "Equipe", "b4": "Receita",
             "b5": "Infra adm.", "b6": "Infra esp.", "b7": "Digital"}
# Respostas que viram colunas, NA ORDEM E COM O NÚMERO do formulário do Wix
# (www.case.org.br/inscricoes2027). Ficam de fora os contatos pessoais (estão na tela
# Selecionadas) e o que já aparece no começo da linha (nome, CNPJ, cidade, UF).
_FORA = {"responsavel", "email", "whatsapp", "cnpj", "nome_entidade", "cidade", "uf",
         "email_institucional", "presidente"}
_ROTULO = {k: r for _g, k, r, _o, _d in campos_def.CAMPOS}


def _ordem(num):
    a, _, b = num.partition(".")
    return int(a), int(b or 0)


# (chave, "21. Elaboração — ...", coluna do bloco de nota ou None)
RESPOSTAS = sorted(((k, f"{n}. {_ROTULO[k]}", campos_def.BLOCO_DA_PERGUNTA.get(k))
                    for k, n in campos_def.NUMERO_FORMULARIO.items() if k not in _FORA),
                   key=lambda x: _ordem(campos_def.NUMERO_FORMULARIO[x[0]]))


def _col_pontos(chave):
    return f"{campos_def.NUMERO_FORMULARIO[chave]} · pontos"


def mostrar():
    _ui.cabecalho(2, "Todas as organizações numa lista só: nota, situação, problemas e todas as respostas. "
                     "Clique numa linha para a ficha; em duas ou mais, para comparar.")

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Ainda não há inscrições. Elas chegam sozinhas do Wix na etapa Inscrições.")
        return

    mapa = st.session_state["mapa"]
    st.session_state.setdefault("vagas", 10)
    st.session_state.setdefault("pool_fase2", 30)
    vagas = int(st.session_state["vagas"])
    pool_size = int(st.session_state["pool_fase2"])

    f = _calculo.funil_df(dados, mapa, vagas, pool_size).copy()
    f["dig"] = f["CNPJ"].map(so_digitos)

    # Problemas numa coluna só: eliminatórias e avisos (Motivo) + pendências da base
    v = validacao.validar(dados, mapa)
    da_base = {so_digitos(c): p for c, p in zip(v["pendencias"]["CNPJ"], v["pendencias"]["Problema"])}
    f["Problemas"] = [" · ".join(x for x in [str(m or "").strip(), da_base.get(d, "")] if x)
                      for m, d in zip(f["Motivo"], f["dig"])]
    eliminada = f["Status"] == "Eliminada"

    total = len(f)
    c = st.columns(4)
    c[0].metric("Inscrições", total)
    c[1].metric("Na Fase 2 (documentos)", int(f["em_pool"].sum()),
                help=(f"As {pool_size} mais bem colocadas (não eliminadas) vão à Fase 2."
                      + (f" Por enquanto há só {total} inscrições." if total < pool_size else "")))
    c[2].metric("Eliminadas", int(eliminada.sum()),
                help="Responderam \"Não\" numa das perguntas 14 a 19 ou abriram o CNPJ depois de 01/03/2026 "
                     "(Regulamento 8.1). Ficam visíveis, sem posição e fora da Fase 2.")
    c[3].metric("Com problema", int(((f["Problemas"] != "") & ~eliminada).sum()),
                help="Não eliminadas, mas com algo a conferir: CNPJ inválido ou repetido, campo em branco, "
                     "pergunta não respondida.")

    # ----------------------- controles -----------------------
    with st.container(horizontal=True, vertical_alignment="bottom", gap="small"):
        busca = st.text_input("Buscar entidade", placeholder="digite parte do nome", width=260,
                              icon=":material/search:")
        ver = st.segmented_control("Ver", ["Todas", "Fase 2", "Com problema", "Eliminadas"], default="Todas",
                                   key="ranking_ver") or "Todas"
        todas_resp = st.toggle("Respostas e pontos", value=True, key="ranking_respostas",
                               help="Todas as respostas, na numeração do formulário, com os pontos ao lado "
                                    "de cada pergunta que vale nota.")
        with st.popover("Filtros", icon=":material/filter_list:"):
            situacoes = st.multiselect("Situação", SITUACOES, placeholder="Todas")
            regioes = st.multiselect("Região", sorted(r for r in f["Região"].unique() if r), placeholder="Todas")
            cidades = st.multiselect("Cidade", sorted(c for c in f["Cidade"].unique() if c), placeholder="Todas")
        with st.popover("Ajustar corte", icon=":material/tune:"):
            st.number_input("Vagas finais", min_value=1, step=1, key="vagas",
                            help="Meta ao final de todo o processo.")
            st.number_input("Quantas vão à Fase 2 (documentos)", min_value=1, step=1, key="pool_fase2",
                            help="As mais bem colocadas entram na análise de documentos. As demais ficam "
                                 "na fila (entram sozinhas se alguém for excluído).")
        st.download_button("Planilha", exportacao.montar_planilha(f, vagas), "pontuacao_case2027.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           icon=":material/download:",
                           help="Todas as organizações, com as vagas em destaque e a coluna "
                                "'Interesse do patrocinador'.")

    # Ordem: quem está no ranking (pela posição) e, no fim, as eliminadas (pela nota)
    f["_ord"] = [(1 if el else 0, p if p not in (None, "") and str(p) != "nan" else 10 ** 6, -n)
                 for el, p, n in zip(eliminada, f["Posição"], f["Nota"])]
    vista = f.sort_values("_ord")
    if busca:
        vista = vista[vista["Entidade"].str.contains(busca, case=False, na=False, regex=False)]
    if situacoes:
        vista = vista[vista["Situação"].isin(situacoes)]
    if regioes:
        vista = vista[vista["Região"].isin(regioes)]
    if cidades:
        vista = vista[vista["Cidade"].isin(cidades)]
    if ver == "Fase 2":
        vista = vista[vista["em_pool"]]
    elif ver == "Com problema":
        vista = vista[(vista["Problemas"] != "") & (vista["Status"] != "Eliminada")]
    elif ver == "Eliminadas":
        vista = vista[vista["Status"] == "Eliminada"]

    st.caption(f"{len(vista)} de {total} inscrições. As {pool_size} melhores não eliminadas (Fase 2 = Sim, em "
               "lilás) vão aos documentos. A coluna Problemas junta tudo o que há para conferir. Clique numa "
               "linha para a ficha; marque duas ou mais para comparar.")

    disp = vista.copy()
    disp["Fase 2"] = disp["em_pool"].map(lambda x: "Sim" if x else "")
    resp_cols, pts_cols, nao_reconhecida = [], [], {}
    if todas_resp:
        por_dig = {so_digitos(r.get("cnpj", "")): r.to_dict() for _, r in dados.iterrows()}
        conf = _conferencia(dados, mapa)
        for chave, rotulo, bloco in RESPOSTAS:
            if bloco:  # pergunta que vale nota: os pontos vêm ANTES da resposta da mesma pergunta
                col = _col_pontos(chave)  # ("21 · pontos" | "21. Elaboração"), lendo da esquerda
                disp[col] = disp[bloco].astype(int)  # para a direita, sem parecer da pergunta seguinte
                resp_cols.append(col)
                pts_cols.append(col)
                i = int(bloco[1:]) - 1  # resposta que a régua não reconhece: marcar em vermelho
                nao_reconhecida[rotulo] = [str((conf.get(d) or [""] * 7)[i]).startswith("0 · não reconhecida")
                                           for d in disp["dig"]]
            disp[rotulo] = disp["dig"].map(lambda d, k=chave: str((por_dig.get(d) or {}).get(k, "") or "").strip())
            resp_cols.append(rotulo)
    colunas =["Posição", "Entidade", "Nota", "Situação", "Fase 2", "Problemas", "Cidade", "UF", "Anos"] + resp_cols
    disp = disp[colunas].rename(columns={"Anos": "Tempo (anos)"})
    # Eliminada não tem posição: mostra "—". Texto com espaços à esquerda para a ordem
    # continuar certa ao clicar no título (" 2" vem antes de "10"; "—" vai para o fim).
    disp["Posição"] = pd.to_numeric(disp["Posição"], errors="coerce").map(
        lambda v: "—" if pd.isna(v) else f"{int(v):>3}")

    def _cor_sit(val):
        return CORES_SITUACAO.get(val, "")

    def _cor_pool(val):
        return f"background-color:{tema.LAVANDA};color:{tema.ROXO_ESCURO};font-weight:600" if val == "Sim" else ""

    vermelho = tema.COR_STATUS["vermelho"]

    def _cor_nao_reconhecida(col):
        marcas = nao_reconhecida.get(col.name, [False] * len(col))
        return [f"background-color:{vermelho[0]};color:{vermelho[1]}" if m else "" for m in marcas]

    estilo = disp.style.map(_cor_sit, subset=["Situação"]).map(_cor_pool, subset=["Fase 2"]) \
        .format({"Tempo (anos)": "{:.1f}"}, na_rep="")
    if nao_reconhecida:
        estilo = estilo.apply(_cor_nao_reconhecida, subset=list(nao_reconhecida))
    col_cfg = {
        "Posição": st.column_config.TextColumn("Posição", width="small", pinned=True,
                                               help="Eliminadas não têm posição (—)."),
        "Entidade": st.column_config.TextColumn("Entidade", width="large", pinned=True),
        "Nota": st.column_config.ProgressColumn("Nota", min_value=0, max_value=70, format="%d", width="small"),
        "Fase 2": st.column_config.TextColumn("Fase 2", width="small"),
        "Problemas": st.column_config.TextColumn("Problemas", width="large",
                                                 help="Eliminatórias, CNPJ, campos em branco e avisos — tudo junto."),
    }
    for rot in resp_cols:
        if rot in pts_cols:
            col_cfg[rot] = st.column_config.ProgressColumn(rot, min_value=0, max_value=10, format="%d",
                                                           width="small",
                                                           help="Pontos que esta resposta deu (de 0 a 10).")
        else:
            col_cfg[rot] = st.column_config.TextColumn(rot, width="medium")
    altura = min(36 * (len(disp) + 1) + 4, 640)
    sel = st.dataframe(estilo, width="stretch", hide_index=True, height=altura, column_config=col_cfg,
                       on_select="rerun", selection_mode="multi-row", key="ranking_tabela")
    if todas_resp:
        st.caption("As perguntas seguem a numeração do formulário. Nas que valem nota (21, 22, 24 a 28), "
                   "a coluna “pontos” vem logo ANTES da resposta, com o mesmo número: “21 · pontos” é a nota "
                   "da resposta 21, de 0 a 10. "
                   "Em vermelho: resposta que a régua não reconhece (pontuou 0) — confira no formulário do Wix.")

    # ----------------------- ficha (1 linha) ou comparação (2+) -----------------------
    linhas = sel.selection.rows if sel else []
    if len(linhas) == 1:
        entidade = disp.iloc[linhas[0]]["Entidade"]
        with st.container(border=True):
            st.subheader(entidade)
            _ui.ficha(f, entidade, dados, mapa)
    elif len(linhas) >= 2:
        _comparar(vista.iloc[linhas], dados, mapa)


def _comparar(sel, dados, mapa):
    """Lado a lado: nota, situação, problemas e cada resposta com os pontos que deu."""
    por_dig = {so_digitos(r.get("cnpj", "")): r.to_dict() for _, r in dados.iterrows()}
    nomes = [str(n) for n in sel["Entidade"]]
    nomes = [n if nomes.count(n) == 1 else f"{n} ({i + 1})" for i, n in enumerate(nomes)]
    linhas = {"Nota": [int(x) for x in sel["Nota"]], "Situação": list(sel["Situação"]),
              "Problemas": [p or "—" for p in sel["Problemas"]]}
    for chave, rotulo, bloco in RESPOSTAS:
        valores = []
        for d, (_, linha) in zip(sel["dig"], sel.iterrows()):
            resp = str((por_dig.get(d) or {}).get(chave, "") or "").strip() or "—"
            valores.append(f"{int(linha[bloco])} pts · {resp}" if bloco else resp)
        linhas[rotulo] = valores
    tabela = pd.DataFrame(linhas, index=nomes).T
    with st.container(border=True):
        st.subheader(f"Comparando {len(nomes)} entidades")
        st.caption("Nota, situação, problemas e cada pergunta na numeração do formulário. Nas que valem nota, "
                   "os pontos aparecem antes da resposta.")
        st.dataframe(tabela, width="stretch", height=min(36 * (len(tabela) + 1) + 4, 900),
                     column_config={"_index": st.column_config.TextColumn("Pergunta", width="medium",
                                                                          pinned=True)})
