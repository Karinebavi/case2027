# -*- coding: utf-8 -*-
"""
Números e tabelas dos Relatórios — a MESMA fonte para a tela e para o PDF, para os
dois nunca divergirem. Sem Streamlit aqui (testável). Nenhuma tabela traz nome de
entidade, CNPJ ou contato: só contagens, percentuais e estatísticas.

`montar_base(dados, scored)` junta as respostas (base) com a nota/situação e o local
já padronizado (regras/localidade.py). Os filtros (`aplicar_filtros`) trabalham sobre
essa base; tudo o que vem depois (tabelas, gráficos, PDF) usa o recorte filtrado.
"""
import re
from datetime import date

import pandas as pd

from regras import localidade, pontuacao
from regras.memoria import so_digitos

BLOCOS = [("b1", "1 · Elaboração de projetos"), ("b2", "2 · Execução de projetos"), ("b3", "3 · Equipe"),
          ("b4", "4 · Receita bruta anual"), ("b5", "5 · Infraestrutura administrativa"),
          ("b6", "6 · Infraestrutura esportiva"), ("b7", "7 · Presença digital")]
EM_CLASSIFICACAO = ("Classificada", "Fila de espera")
ORDEM_REGIAO = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul", "(não identificada)"]

# Perguntas de perfil: (chave, título, ordem das opções ou None)
PERFIL = [
    ("p21", "Equipe (nº de pessoas) — pergunta 24", list(pontuacao.EQUIPE)),
    ("p22", "Receita bruta anual — pergunta 25", list(pontuacao.RECEITA)),
    ("p23", "Infraestrutura administrativa — pergunta 26", list(pontuacao.INFRA_ADMIN)),
    ("p24", "Infraestrutura esportiva — pergunta 27", list(pontuacao.INFRA_ESP)),
    ("p20_lie", "Situação na Lei de Incentivo ao Esporte — pergunta 23", None),
]


def _pct(n, total):
    return round(100 * n / total, 1) if total else 0.0


# ------------------------------------------------------------------ base

def montar_base(dados, scored):
    """Respostas + nota/situação/local padronizado, uma linha por inscrição."""
    base = dados.copy()
    base["_dig"] = base["cnpj"].map(so_digitos) if "cnpj" in base.columns else ""
    info = scored.copy()
    info["_dig"] = info["CNPJ"].map(so_digitos)
    traz = [c for c in ["Situação", "Status", "Motivo", "Nota", "Posição", "Anos", "UF", "Região", "Cidade",
                        "b1", "b2", "b3", "b4", "b5", "b6", "b7", "_cidade_digitada", "_uf_digitada",
                        "_local_status", "_uf_status", "_local_sugestao", "_codigo_ibge"] if c in info.columns]
    if len(info) == len(base):
        # pontuacao.calcular percorre a base na ordem e a classificação não mexe no índice:
        # junta pela LINHA (CNPJ repetido não mistura duas inscrições)
        w = base.reset_index(drop=True)
        info = info.sort_index().reset_index(drop=True)
        for c in traz:
            w[c] = info[c].values
    else:
        w = base.merge(info[["_dig"] + traz].drop_duplicates("_dig"), on="_dig", how="left")
    w["Nota"] = pd.to_numeric(w.get("Nota"), errors="coerce")
    w["Anos"] = pd.to_numeric(w.get("Anos"), errors="coerce")
    w["_envio"] = w["data_envio"].map(pontuacao.parse_data) if "data_envio" in w.columns else None
    w["Local"] = [f"{c}/{u}" if c and u else (c or u or "") for c, u in zip(w.get("Cidade", ""), w.get("UF", ""))]
    return w


# ------------------------------------------------------------------ filtros

FILTROS_VAZIOS = {"situacao": [], "regiao": [], "uf": [], "cidade": [], "receita": [], "equipe": [],
                  "nota": None, "anos": None, "envio": None}


def aplicar_filtros(w, f):
    f = {**FILTROS_VAZIOS, **(f or {})}
    m = pd.Series(True, index=w.index)
    for chave, col in [("situacao", "Situação"), ("regiao", "Região"), ("uf", "UF"), ("cidade", "Local"),
                       ("receita", "p22"), ("equipe", "p21")]:
        if f[chave] and col in w.columns:
            m &= w[col].astype(str).isin(f[chave])
    if f["nota"]:
        m &= w["Nota"].between(*f["nota"])
    if f["anos"]:
        m &= w["Anos"].between(*f["anos"]) | w["Anos"].isna() & (f["anos"][0] == 0)
    if f["envio"] and "_envio" in w.columns:
        ini, fim = f["envio"]
        m &= w["_envio"].map(lambda d: d is not None and ini <= d <= fim)
    return w[m]


def descrever_filtros(f, nota_max=70, anos_max=None, envio_lim=None):
    """Texto curto dos filtros ativos (vai na tela e na capa do PDF)."""
    f = {**FILTROS_VAZIOS, **(f or {})}
    partes = []
    for chave, rot in [("situacao", "Situação"), ("regiao", "Região"), ("uf", "UF"), ("cidade", "Cidade"),
                       ("equipe", "Equipe"), ("receita", "Receita")]:
        if f[chave]:
            partes.append(f"{rot}: {', '.join(map(str, f[chave]))}")
    if f["nota"] and tuple(f["nota"]) != (0, nota_max):
        partes.append(f"Nota de {f['nota'][0]} a {f['nota'][1]}")
    if f["anos"] and anos_max is not None and tuple(f["anos"]) != (0, anos_max):
        partes.append(f"Tempo de existência de {f['anos'][0]} a {f['anos'][1]} anos")
    if f["envio"] and envio_lim and tuple(f["envio"]) != tuple(envio_lim):
        partes.append(f"Enviadas de {f['envio'][0]:%d/%m/%Y} a {f['envio'][1]:%d/%m/%Y}")
    return "; ".join(partes) or "nenhum (todas as inscrições)"


# ------------------------------------------------------------------ estatística

def estatisticas(serie):
    s = pd.to_numeric(serie, errors="coerce").dropna()
    if not len(s):
        return {"n": 0}
    r = lambda v: float(round(v, 1))  # noqa: E731
    return {"n": int(len(s)), "média": r(s.mean()), "mediana": r(s.median()),
            "desvio-padrão": r(s.std(ddof=1)) if len(s) > 1 else 0.0,
            "mínimo": r(s.min()), "1º quartil": r(s.quantile(0.25)),
            "3º quartil": r(s.quantile(0.75)), "máximo": r(s.max()),
            "coef. de variação (%)": r(100 * s.std(ddof=1) / s.mean()) if len(s) > 1 and s.mean() else 0.0}


def resumo(w):
    """Indicadores principais do recorte."""
    n = len(w)
    em = w[w["Situação"].isin(EM_CLASSIFICACAO)]
    elim = int((w["Status"] == "Eliminada").sum()) if "Status" in w.columns else 0
    cid = w.loc[w.get("Cidade", pd.Series(dtype=str)).astype(str) != "", "Local"].nunique() if n else 0
    est = estatisticas(em["Nota"])
    return {
        "Inscrições": n,
        "Estados (UF)": int(w["UF"].replace("", pd.NA).dropna().nunique()) if n else 0,
        "Municípios": int(cid),
        "Regiões": int(w["Região"].replace("(não identificada)", pd.NA).dropna().nunique()) if n else 0,
        "Em classificação": len(em),
        "Classificadas": int((w["Situação"] == "Classificada").sum()),
        "Eliminadas": elim,
        "Taxa de eliminação (%)": _pct(elim, n),
        "Nota média (em classificação)": est.get("média", "—"),
        "Nota mediana (em classificação)": est.get("mediana", "—"),
        "Desvio-padrão da nota": est.get("desvio-padrão", "—"),
    }


def tabela_notas(w):
    """Estatística descritiva da nota: em classificação x todas (inclui eliminadas)."""
    em = estatisticas(w.loc[w["Situação"].isin(EM_CLASSIFICACAO), "Nota"])
    todas = estatisticas(w["Nota"])
    linhas = [{"Medida": k, "Em classificação": em.get(k, "—"), "Todas (com eliminadas)": todas.get(k, "—")}
              for k in todas]
    return pd.DataFrame(linhas, dtype=object)  # object: "n" continua inteiro


def tabela_blocos(w):
    """Desempenho por bloco da régua (cada um vale de 0 a 10)."""
    linhas = []
    n = len(w)
    for col, rot in BLOCOS:
        if col not in w.columns:
            continue
        s = pd.to_numeric(w[col], errors="coerce").dropna()
        e = estatisticas(s)
        linhas.append({"Bloco": rot, "Média": e.get("média", "—"), "Mediana": e.get("mediana", "—"),
                       "Desvio-padrão": e.get("desvio-padrão", "—"),
                       "% com 10 (máx.)": _pct(int((s == 10).sum()), n),
                       "% com 0": _pct(int((s == 0).sum()), n)})
    return pd.DataFrame(linhas)


def tabela_territorio(w, nivel):
    """Por 'Região' ou 'UF': inscrições, %, nota média, classificadas e eliminadas."""
    n = len(w)
    if not n:
        return pd.DataFrame()
    g = w.assign(_k=w[nivel].replace("", "(não identificado)").fillna("(não identificado)"))
    linhas = []
    for k, sub in g.groupby("_k"):
        em = sub[sub["Situação"].isin(EM_CLASSIFICACAO)]
        linhas.append({nivel: k, "Inscrições": len(sub), "% do total": _pct(len(sub), n),
                       "Nota média": round(em["Nota"].mean(), 1) if len(em) else None,
                       "Classificadas": int((sub["Situação"] == "Classificada").sum()),
                       "Eliminadas": int((sub["Status"] == "Eliminada").sum())})
    t = pd.DataFrame(linhas)
    if nivel == "Região":
        t["_o"] = t["Região"].map({r: i for i, r in enumerate(ORDEM_REGIAO)}).fillna(99)
        return t.sort_values("_o").drop(columns="_o").reset_index(drop=True)
    return t.sort_values(["Inscrições", nivel], ascending=[False, True]).reset_index(drop=True)


def tabela_cidades(w, top=15):
    n = len(w)
    s = w.loc[w["Local"].astype(str) != "", "Local"]
    c = s.value_counts().head(top)
    return pd.DataFrame({"Município/UF": c.index, "Inscrições": c.values,
                         "% do total": [_pct(v, n) for v in c.values]})


def tabela_eliminacoes(w):
    """Motivos de eliminação (uma inscrição pode ter mais de um)."""
    n = len(w)
    elim = w[w["Status"] == "Eliminada"]
    cont = {}
    for motivo in elim["Motivo"].astype(str):
        for parte in motivo.split(" · "):
            parte = parte.strip()
            if parte and "não respondida" not in parte:
                cont[parte] = cont.get(parte, 0) + 1
    linhas = [{"Motivo": k, "Inscrições": v, "% das inscrições": _pct(v, n),
               "% das eliminadas": _pct(v, len(elim))} for k, v in sorted(cont.items(), key=lambda x: -x[1])]
    return pd.DataFrame(linhas)


def tabela_perfil(w, chave, ordem=None):
    """Frequência de uma pergunta: n, %, e nota média de quem respondeu cada opção."""
    if chave not in w.columns:
        return pd.DataFrame()
    s = w[chave].astype(str).str.strip()
    s = s[s != ""]
    n = len(s)
    c = s.value_counts()
    if ordem:
        c = c.reindex([o for o in ordem if o in c.index] + [o for o in c.index if o not in ordem])
    linhas = []
    for resp, qtd in c.items():
        notas = w.loc[w[chave].astype(str).str.strip() == resp, "Nota"]
        linhas.append({"Resposta": resp, "Inscrições": int(qtd), "%": _pct(qtd, n),
                       "Nota média": round(notas.mean(), 1) if notas.notna().any() else None})
    return pd.DataFrame(linhas)


def tabela_mecanismos(w, chave):
    """Perguntas 21/22: nº de mecanismos incentivados marcados (é o que a régua conta)."""
    if chave not in w.columns:
        return pd.DataFrame()

    def faixa(v):
        n = pontuacao._conta_mecanismos(v)
        return "3 ou mais" if n >= 3 else str(n)
    tmp = w.assign(_f=w[chave].map(faixa))
    total = len(tmp)
    linhas = []
    for f in ["0", "1", "2", "3 ou mais"]:
        sub = tmp[tmp["_f"] == f]
        if len(sub):
            linhas.append({"Mecanismos": f, "Pontos na régua": pontuacao._nota_mecanismo(4 if f == "3 ou mais" else int(f)),
                           "Inscrições": len(sub), "%": _pct(len(sub), total),
                           "Nota média": round(sub["Nota"].mean(), 1) if sub["Nota"].notna().any() else None})
    return pd.DataFrame(linhas)


def tabela_multipla(w, chave, rotulo, ignorar=()):
    """Pergunta de marcar várias opções: quantas inscrições marcaram cada uma."""
    if chave not in w.columns:
        return pd.DataFrame()
    n = len(w)
    cont, nomes = {}, {}
    for v in w[chave].astype(str):
        vistos = set()
        # vírgula/; separam as opções — menos dentro de parênteses:
        # "Lutas / Artes Marciais (Judô, Karatê, Jiu-Jitsu, etc.)" é UMA opção só
        for parte in re.split(r"[,;](?![^()]*\))", v):
            p = " ".join(parte.split())
            k = localidade.chave(p)
            if p and k not in vistos and p.lower() not in ignorar:
                vistos.add(k)
                cont[k] = cont.get(k, 0) + 1
                nomes.setdefault(k, p)  # "futebol", "Futebol " e "FUTEBOL" contam juntos
    return pd.DataFrame([{rotulo: nomes[k], "Inscrições": v, "% das inscrições": _pct(v, n)}
                         for k, v in sorted(cont.items(), key=lambda x: (-x[1], nomes[x[0]]))])


def tabela_canais(w):
    return tabela_multipla(w, "canais", "Canal")


def tabela_modalidades(w):
    return tabela_multipla(w, "modalidades", "Modalidade",
                           ignorar=("não trabalhamos com modalidades esportivas", "nan"))


def tabela_envios(w):
    """Inscrições por dia de envio, com o acumulado."""
    if "_envio" not in w.columns:
        return pd.DataFrame()
    d = pd.Series([x for x in w["_envio"] if isinstance(x, date)])
    if not len(d):
        return pd.DataFrame()
    c = d.value_counts().sort_index()
    return pd.DataFrame({"Data": c.index, "Inscrições": c.values, "Acumulado": c.cumsum().values})


# ------------------------------------------------------------------ qualidade dos dados

def tabela_qualidade(w):
    """Quantas cidades/estados vieram certos, foram corrigidos ou precisam de conferência."""
    n = len(w)
    linhas = []
    for col, rot in [("_uf_status", "Estado (UF)"), ("_local_status", "Cidade")]:
        if col not in w.columns:
            continue
        c = w[col].fillna("").replace("", "vazia").value_counts()
        for st_, qtd in c.items():
            linhas.append({"Campo": rot, "Situação": st_, "Inscrições": int(qtd), "%": _pct(qtd, n)})
    return pd.DataFrame(linhas)


def tabela_correcoes(w):
    """O que foi digitado -> como ficou (agrupado; sem nome de entidade)."""
    if "_local_status" not in w.columns:
        return pd.DataFrame()
    mudou = w[(w["_local_status"].isin([localidade.CORRIGIDA, localidade.A_CONFERIR, localidade.NAO_RECONHECIDA]))
              | (w["_uf_status"].isin([localidade.CORRIGIDA, "pela cidade", localidade.NAO_RECONHECIDA]))]
    if not len(mudou):
        return pd.DataFrame()
    t = pd.DataFrame({
        "Digitado (cidade / estado)": [f"{c or '—'} / {u or '—'}" for c, u in
                                       zip(mudou["_cidade_digitada"], mudou["_uf_digitada"])],
        "Padronizado": mudou["Local"].replace("", "—"),
        "Situação": mudou["_local_status"],
        "Observação": mudou["_local_sugestao"].fillna(""),
    })
    t = t.groupby(list(t.columns), dropna=False).size().reset_index(name="Inscrições")
    ordem = {localidade.A_CONFERIR: 0, localidade.NAO_RECONHECIDA: 1, localidade.CORRIGIDA: 2}
    return t.sort_values(by="Situação", key=lambda s: s.map(ordem).fillna(3)).reset_index(drop=True)


METODOLOGIA = (
    "Fonte: inscrições do formulário CASE 2027 (Wix), pontuadas pela régua da Etapa 1 "
    "(7 blocos de 0 a 10; nota máxima 70; curva com nota máxima no perfil intermediário). "
    "Eliminadas: resposta diferente de \"Sim\" nas perguntas 14 a 19 (Regulamento 8.1), CNPJ aberto "
    "depois de 01/03/2026 ou nome de empresa (Ltda, EIRELI, ME...). As estatísticas da nota usam só "
    "as inscrições em classificação, salvo indicação. Desvio-padrão amostral; quartis por interpolação "
    "linear. Estado e cidade foram padronizados pela lista oficial de municípios do IBGE (5.571): "
    "\"corrigida\" = erro de digitação, abreviação ou apelido resolvido com segurança; \"a conferir\" = "
    "o sistema não decide sozinho (cidade de outro estado, homônimos ou semelhança baixa); o texto "
    "original continua guardado na base. Percentuais sobre o total do recorte filtrado."
)
