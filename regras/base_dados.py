# -*- coding: utf-8 -*-
"""
Base acumulada de inscrições.

A cada arquivo que você importa, as inscrições são somadas a uma base única
que fica guardada em dados_base/inscricoes.csv. O CNPJ é a chave: se a mesma
entidade aparecer de novo, a versão mais recente (pela Data de envio)
substitui a antiga — a base não duplica, só cresce com as novas.

Observação: os dados ficam nesta máquina/pasta (LGPD). Na nuvem, use os
botões de baixar/subir a base para levá-la de um lugar a outro.
"""
import os
import pandas as pd

from regras import normalizacao
from regras.memoria import so_digitos
from regras.pontuacao import parse_data

PASTA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados_base")
ARQUIVO = os.path.join(PASTA, "inscricoes.csv")


def caminho():
    return ARQUIVO


def carregar():
    """Lê a base acumulada (ou uma tabela vazia com as colunas canônicas)."""
    if os.path.exists(ARQUIVO):
        try:
            return pd.read_csv(ARQUIVO, dtype=str, keep_default_na=False)
        except Exception:
            pass
    return pd.DataFrame({chave: [] for chave in normalizacao.chaves()})


def salvar(df):
    os.makedirs(PASTA, exist_ok=True)
    df.to_csv(ARQUIVO, index=False, encoding="utf-8")


def limpar():
    if os.path.exists(ARQUIVO):
        os.remove(ARQUIVO)


def _ordem_data(v):
    d = parse_data(v)
    return d.toordinal() if d else 0


def acumular(base, novos):
    """Junta 'novos' (normalizados) à 'base' (normalizada), sem duplicar CNPJ.

    Devolve (base_final, cnpjs_novos, n_atualizados).
    """
    base = base.copy()
    novos = novos.copy()
    for df in (base, novos):
        if "cnpj" not in df.columns:
            df["cnpj"] = ""
    base["_cnpj"] = base["cnpj"].map(so_digitos)
    novos["_cnpj"] = novos["cnpj"].map(so_digitos)

    existentes = set(base["_cnpj"]) - {""}
    cnpjs_novos = sorted({c for c in novos["_cnpj"] if c and c not in existentes})
    n_atualizados = len({c for c in novos["_cnpj"] if c and c in existentes})

    juntas = pd.concat([base, novos], ignore_index=True)
    juntas["_ordem"] = juntas["data_envio"].map(_ordem_data) if "data_envio" in juntas.columns else 0
    # mantém a mais recente (maior data de envio) quando o CNPJ se repete
    juntas = juntas.sort_values("_ordem", kind="stable")
    com_cnpj = juntas[juntas["_cnpj"] != ""].drop_duplicates("_cnpj", keep="last")
    sem_cnpj = juntas[juntas["_cnpj"] == ""]
    final = pd.concat([com_cnpj, sem_cnpj], ignore_index=True)

    final = final.drop(columns=[c for c in ["_cnpj", "_ordem"] if c in final.columns])
    colunas = [c for c in normalizacao.chaves() if c in final.columns]
    return final[colunas], set(cnpjs_novos), n_atualizados
