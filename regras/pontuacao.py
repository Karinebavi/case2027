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

# Bloco 4 — Receita bruta anual (faixas do formulário FINAL; alvo: 51 a 150 mil).
# Curva mantida do quadro original (5, 8, 10, 3, 2), remapeada para as novas faixas.
RECEITA = {
    "Até R$ 25 mil": 5,
    "De R$ 25 mil a R$ 50 mil": 8,
    "De R$ 51 mil a R$ 150 mil": 10,
    "De R$ 151 mil a R$ 500 mil": 3,
    "Acima de R$ 500 mil": 2,
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


def _so_digitos(v):
    return "".join(c for c in str(v) if c.isdigit())


def _resumo_mecanismos(texto):
    """Mecanismos incentivados reconhecidos na resposta (para a memória)."""
    s = _txt(texto)
    achados = [t for t in ["Esporte", "Cultura", "Infância", "Idoso", "Emenda"] if t in s]
    if "PRONAS" in s or "PRONON" in s:
        achados.append("PRONAS/PRONON")
    return ", ".join(achados) if achados else "nenhum"


def _blocos_detalhe(g):
    """Memória de cálculo de UMA inscrição: por bloco, o que respondeu, quantos
    pontos deu (de no máx. 10) e como foi contado. Usa as MESMAS tabelas do
    cálculo, então nunca diverge da nota."""
    out = []
    n_elab = _conta_mecanismos(g("p18"))
    out.append({"Bloco": "1 · Elaboração de projetos", "Resposta": _resumo_mecanismos(g("p18")),
                "Pontos": _nota_mecanismo(n_elab), "Máx": 10,
                "Como foi contado": f"{n_elab} mecanismo(s) incentivado(s) → {_nota_mecanismo(n_elab)} pts"})
    n_exec = _conta_mecanismos(g("p19"))
    out.append({"Bloco": "2 · Execução de projetos", "Resposta": _resumo_mecanismos(g("p19")),
                "Pontos": _nota_mecanismo(n_exec), "Máx": 10,
                "Como foi contado": f"{n_exec} mecanismo(s) executado(s) → {_nota_mecanismo(n_exec)} pts"})
    r3 = _txt(g("p21")).strip()
    out.append({"Bloco": "3 · Equipe", "Resposta": r3 or "—", "Pontos": EQUIPE.get(r3, 0),
                "Máx": 10, "Como foi contado": "faixa de pessoas na equipe"})
    r4 = _txt(g("p22")).strip()
    out.append({"Bloco": "4 · Receita bruta anual", "Resposta": r4 or "—", "Pontos": RECEITA.get(r4, 0),
                "Máx": 10, "Como foi contado": "faixa de receita (alvo: 51–150 mil)"})
    r5 = _txt(g("p23")).strip()
    out.append({"Bloco": "5 · Infraestrutura administrativa", "Resposta": r5 or "—",
                "Pontos": INFRA_ADMIN.get(r5, 0), "Máx": 10, "Como foi contado": "tipo de espaço de gestão"})
    r6 = _txt(g("p24")).strip()
    out.append({"Bloco": "6 · Infraestrutura esportiva", "Resposta": r6 or "—",
                "Pontos": INFRA_ESP.get(r6, 0), "Máx": 10, "Como foi contado": "tipo de espaço das atividades"})
    tem_site = _txt(g("site")).strip() != ""
    tem_rede = any(_txt(g(k)).strip() != "" for k in ["instagram", "facebook", "outra_rede"])
    if tem_site and tem_rede:
        b7, como = 6, "site + redes sociais"
    elif tem_site:
        b7, como = 8, "só site"
    elif tem_rede:
        b7, como = 10, "só redes sociais"
    else:
        b7, como = 4, "sem canais digitais"
    canais = ", ".join(nome for nome, k in [("site", "site"), ("Instagram", "instagram"),
             ("Facebook", "facebook"), ("outra rede", "outra_rede")] if _txt(g(k)).strip()) or "nenhum"
    out.append({"Bloco": "7 · Presença digital", "Resposta": canais, "Pontos": b7, "Máx": 10,
                "Como foi contado": f"{como} → {b7} pts"})
    return out


def detalhar(dados, mapa, cnpj):
    """Memória de cálculo detalhada de uma entidade (localizada pelo CNPJ)."""
    col = mapa.get("cnpj")
    alvo = _so_digitos(cnpj)
    for _, row in dados.iterrows():
        if col and _so_digitos(row.get(col, "")) == alvo:
            return _blocos_detalhe(lambda ch: row.get(mapa.get(ch), "") if mapa.get(ch) else "")
    return []


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

        # Eliminatórias da Etapa 1 — SÓ as operacionais (requisitos para a
        # mentoria online). Estatuto/finalidade esportiva, tempo de 1 ano e
        # modalidades NÃO excluem mais aqui: são verificados na conferência
        # documental (Fase 2), onde está o filtro real de quem não segue.
        OPERACIONAIS = [
            ("computador", "Sem computador com câmera/microfone"),
            ("internet", "Sem internet para as reuniões"),
            ("disponibilidade", "Sem disponibilidade de 2h por semana"),
        ]
        motivos = [texto for chave, texto in OPERACIONAIS
                   if _txt(g(chave)).strip().lower() != "sim"]
        elegivel = not motivos

        anos = _anos(g("data_fundacao"), ref)  # informativo (coluna "Anos")

        # Sem corte de teto: ter muitos projetos (3+ elaborados/executados) NÃO
        # exclui mais a entidade — todas pontuam normalmente. O filtro real de
        # quem não segue é a conferência documental (Fase 2).
        total = 0 if not elegivel else (b1 + b2 + b3 + b4 + b5 + b6 + b7)
        if not elegivel:
            status = "Inelegível"
            motivo = " · ".join(motivos)
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
