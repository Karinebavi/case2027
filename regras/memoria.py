# -*- coding: utf-8 -*-
"""
Memória das inscrições já conferidas — para marcar quais são NOVAS.

A memória é só uma lista dos CNPJs que você já tinha visto. Fica num
arquivo que você baixa e sobe de volta na próxima vez — nada é guardado
no servidor (os dados continuam só com você).
"""
import pandas as pd


def so_digitos(cnpj):
    return "".join(c for c in str(cnpj) if c.isdigit())


def carregar(arquivo):
    """Lê o arquivo de memória e devolve o conjunto de CNPJs já conferidos."""
    df = pd.read_csv(arquivo, dtype=str, keep_default_na=False)
    coluna = df.columns[0]
    return {so_digitos(v) for v in df[coluna] if so_digitos(v)}


def gerar(dados, mapa):
    """Gera o CSV de memória (a lista de CNPJs) a partir das inscrições atuais."""
    col = mapa.get("cnpj")
    cnpjs = sorted({so_digitos(v) for v in dados[col] if so_digitos(v)}) if col else []
    return pd.DataFrame({"cnpj": cnpjs}).to_csv(index=False).encode("utf-8")
