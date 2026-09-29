# -*- coding: utf-8 -*-
"""
Pontuação de cada inscrição — régua CASE 2027 (Etapa 1).

Curva assimétrica: nota máxima no perfil intermediário de cada bloco;
cai para os dois lados (iniciante demais ou avançada demais).
7 blocos, total máximo 70.

Para recalibrar, edite as TABELAS abaixo. Nenhuma tela precisa mudar.
"""
from datetime import datetime, date
import pandas as pd

from regras import regiao as regiao_mod

# Mecanismos incentivados contados nas perguntas de elaboração/execução.
TOKENS = ["Esporte", "Cultura", "Infância", "Idoso", "PRONAS", "PRONON", "Emenda"]

# Blocos 1 e 2 — nº de mecanismos incentivados -> nota
NOTA_MECANISMO = {0: 5, 1: 10, 2: 3}  # 3 ou mais -> 2

# Bloco 3 — Composição da equipe (alvo: 3 a 5)
EQUIPE = {"1 ou 2": 8, "3 a 5": 10, "6 a 8": 4, "9 a 12": 3, "Mais de 12": 2}

# Bloco 4 — Receita bruta anual (faixas do quadro; alvo: 101 a 250 mil)
RECEITA = {
    "Até R$ 25 mil": 5,
    "De R$ 26 mil a R$ 100 mil": 8,
    "De R$ 101 mil a R$ 250 mil": 10,
    "De R$ 251 mil a R$ 500 mil": 3,
    "Acima de R$ 501 mil": 2,
}

# Bloco 5 — Infraestrutura administrativa (alvo: espaço cedido)
INFRA_ADMIN = {
    "Não possui espaço próprio para gestão administrativa": 6,
    "Utiliza espaço cedido por parceiros ou instituições": 10,
    "Possui sede administrativa alugada": 7,
    "Possui sede administrativa própria": 5,
}

# Bloco 6 — Infraestrutura esportiva (alvo: instalações públicas/cedidas)
INFRA_ESP = {
    "Não possui local para as atividades": 6,
    "Utiliza instalações públicas ou cedidas por parceiros (praças, escolas, ginásios, etc.)": 10,
    "Possui espaço esportivo alugado": 7,
    "Possui espaço esportivo próprio": 5,
}


def _txt(v):
    return "" if v is None else str(v)


def _conta_mecanismos(texto):
    s = _txt(texto)
    # conta cada mecanismo uma vez (PRONAS/PRONON contam como um)
    n = sum(1 for t in ["Esporte", "Cultura", "Infância", "Idoso", "Emenda"] if t in s)
    if "PRONAS" in s or "PRONON" in s:
        n += 1
    return n


def _nota_mecanismo(n):
    return NOTA_MECANISMO.get(n, 2)  # 3 ou mais -> 2


def parse_data(v):
    s = _txt(v).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _anos(v, ref):
    d = parse_data(v)
    if d is None:
        return None
    return (ref - d).days / 365.25


def calcular(dados, mapa, hoje=None):
    """Devolve um DataFrame com a nota de cada bloco, o total e o status."""
    ref = hoje or date.today()
    linhas = []
    for _, row in dados.iterrows():
        def g(chave):
            col = mapa.get(chave)
            return row.get(col, "") if col else ""

        n_elab = _conta_mecanismos(g("p18"))
        n_exec = _conta_mecanismos(g("p19"))
        b1 = _nota_mecanismo(n_elab)
        b2 = _nota_mecanismo(n_exec)
        b3 = EQUIPE.get(_txt(g("p21")).strip(), 0)
        b4 = RECEITA.get(_txt(g("p22")).strip(), 0)
        b5 = INFRA_ADMIN.get(_txt(g("p23")).strip(), 0)
        b6 = INFRA_ESP.get(_txt(g("p24")).strip(), 0)

        tem_site = _txt(g("site")).strip() != ""
        tem_rede = any(_txt(g(k)).strip() != "" for k in ["instagram", "facebook", "outra_rede"])
        if tem_site and tem_rede:
            b7 = 6
        elif tem_site:
            b7 = 8
        elif tem_rede:
            b7 = 10
        else:
            b7 = 4

        # Eliminatórias — guarda o motivo de cada falha
        motivos = []
        if _txt(g("estatuto")).strip().lower() != "sim":
            motivos.append("Estatuto sem finalidade esportiva")
        if _txt(g("computador")).strip().lower() != "sim":
            motivos.append("Sem computador com câmera/microfone")
        if _txt(g("internet")).strip().lower() != "sim":
            motivos.append("Sem internet para as reuniões")
        if _txt(g("disponibilidade")).strip().lower() != "sim":
            motivos.append("Sem disponibilidade de 1h30 por semana")

        # Nova eliminatória: modalidades esportivas (só aplica se a coluna existir)
        mod_ok = True
        if mapa.get("modalidades"):
            mod = _txt(g("modalidades")).strip().lower()
            mod_ok = mod != "" and "não trabalhamos" not in mod and "nao trabalhamos" not in mod
            if not mod_ok:
                motivos.append("Não trabalha com modalidades esportivas")

        anos = _anos(g("data_fundacao"), ref)
        tem_1_ano = anos is not None and anos >= 1
        if not tem_1_ano:
            motivos.append("Menos de 1 ano de funcionamento")

        elimin = all(
            _txt(g(k)).strip().lower() == "sim"
            for k in ["estatuto", "computador", "internet", "disponibilidade"]
        )
        elegivel = elimin and mod_ok and tem_1_ano
        teto = (n_elab >= 3 and n_exec >= 3)

        total = 0 if (not elegivel or teto) else (b1 + b2 + b3 + b4 + b5 + b6 + b7)
        if not elegivel:
            status = "Inelegível"
            motivo = " · ".join(motivos)
        elif teto:
            status = "Fora do perfil"
            motivo = "Perfil avançado (3+ mecanismos elaborados e executados) — corte de teto"
        else:
            status = "Em classificação"
            motivo = ""

        linhas.append({
            "Entidade": _txt(g("nome_entidade")),
            "CNPJ": _txt(g("cnpj")).strip(),
            "Cidade": _txt(g("cidade")).strip(),
            "UF": regiao_mod.para_uf(g("uf")) or _txt(g("uf")).strip(),
            "Região": regiao_mod.regiao_de(g("uf")) or "(não identificada)",
            "b1": b1, "b2": b2, "b3": b3, "b4": b4, "b5": b5, "b6": b6, "b7": b7,
            "Nota": total,
            "Status": status,
            "Motivo": motivo,
            "Anos": round(anos, 1) if anos is not None else None,
            "_data_fundacao": _txt(g("data_fundacao")),
        })
    return pd.DataFrame(linhas)
