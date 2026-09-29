# -*- coding: utf-8 -*-
"""
Motor do funil das fases (a partir do ranking + estado do processo).

Regras combinadas com a Karine:
  - Pool da Fase 2 (documental) = as N melhores do ranking que ainda não
    foram excluídas (repescagem AUTOMÁTICA: excluiu uma, a próxima entra).
  - Todas as APROVADAS na documental avançam para a entrevista (Fase 3).
  - Não comparecimento / parecer negativo na entrevista exclui e repesca.
  - Selecionadas finais = as 'vagas' melhores que passaram nas duas fases.

Devolve um DataFrame com uma coluna "Fase" por organização, pronto para as
telas. Não grava nada — quem grava é regras/processo.py.
"""
from regras.memoria import so_digitos
from regras import processo as proc


def _excluida(reg):
    return reg.get("doc_status") == "excluida" or reg.get("entrevista_status") == "excluida"


def montar(scored, estado, pool_size, vagas):
    f = scored.copy()
    f["dig"] = f["CNPJ"].map(so_digitos)

    padrao = proc._padrao()
    for col in ["interesse", "doc_status", "doc_motivo", "entrevista_mentor",
                "entrevista_compareceu", "entrevista_status", "entrevista_motivo"]:
        f[col] = [estado.get(d, {}).get(col, padrao[col]) for d in f["dig"]]

    # Ranking dos elegíveis (Em classificação), na ordem de posição
    eleg = f[f["Status"] == "Em classificação"].sort_values("Posição")

    # Pool da Fase 2 = primeiras 'pool_size' não excluídas
    pool = []
    for d in eleg["dig"]:
        reg = estado.get(d, {})
        if _excluida(reg):
            continue
        pool.append(d)
        if len(pool) >= pool_size:
            break
    pool_set = set(pool)
    pos_pool = {d: i + 1 for i, d in enumerate(pool)}
    f["em_pool"] = f["dig"].isin(pool_set)
    f["pos_pool"] = f["dig"].map(pos_pool)

    def rotulo(r):
        if r["Status"] == "Inelegível":
            return "Inelegível"
        if r["Status"] == "Fora do perfil":
            return "Fora do perfil"
        if r["doc_status"] == "excluida":
            return "Excluída (documental)"
        if r["entrevista_status"] == "excluida":
            return "Excluída (entrevista)"
        if not r["em_pool"]:
            return "Fila de espera"
        if r["doc_status"] == "pendente":
            return "Documental (pendente)"
        if r["entrevista_status"] == "pendente":
            return "Entrevista (pendente)"
        return "Aprovada"

    f["Fase"] = f.apply(rotulo, axis=1)

    # Selecionadas finais = as 'vagas' melhores entre as aprovadas nas duas fases
    aprovadas = f[(f["doc_status"] == "aprovada") & (f["entrevista_status"] == "aprovada")].sort_values("Posição")
    selecionadas = set(aprovadas["dig"].head(vagas))
    f.loc[f["dig"].isin(selecionadas), "Fase"] = "Selecionada"
    reservas = set(aprovadas["dig"]) - selecionadas
    f.loc[f["dig"].isin(reservas), "Fase"] = "Aprovada (reserva)"

    return f


# ---- recortes prontos para as telas ----

def pool_documental(f):
    """As organizações que estão na análise documental agora (na ordem do pool)."""
    return f[f["em_pool"]].sort_values("pos_pool")


def para_entrevista(f):
    """Aprovadas na documental que seguem para a entrevista."""
    aptas = f[(f["doc_status"] == "aprovada") & (f["entrevista_status"] != "excluida") & f["em_pool"]]
    return aptas.sort_values("Posição")


def selecionadas(f):
    return f[f["Fase"].isin(["Selecionada", "Aprovada (reserva)"])].sort_values("Posição")


def descartadas(f):
    """Banco à parte: excluídas na documental ou na entrevista, com o motivo."""
    d = f[f["Fase"].isin(["Excluída (documental)", "Excluída (entrevista)"])].copy()
    d["Motivo"] = [
        (m1 or m2) for m1, m2 in zip(d["doc_motivo"], d["entrevista_motivo"])
    ]
    return d.sort_values("Posição")


def contagem(f):
    return {
        "pool": int(f["em_pool"].sum()),
        "doc_pendente": int((f["Fase"] == "Documental (pendente)").sum()),
        "entrevista_pendente": int((f["Fase"] == "Entrevista (pendente)").sum()),
        "selecionadas": int((f["Fase"] == "Selecionada").sum()),
        "reservas": int((f["Fase"] == "Aprovada (reserva)").sum()),
        "descartadas": int(f["Fase"].isin(["Excluída (documental)", "Excluída (entrevista)"]).sum()),
    }
