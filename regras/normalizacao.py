# -*- coding: utf-8 -*-
"""
Normalização das inscrições.

Cada export do Wix pode vir com nomes de coluna diferentes. Aqui a gente
converte qualquer arquivo (já com o mapa de colunas) para um formato
canônico: uma coluna por CAMPO do sistema (as 'chaves' de base/campos.py).

Com isso, dá para ACUMULAR bases de formatos diferentes na mesma tabela e
pontuar tudo com um mapa 'identidade' (cada chave aponta para si mesma).
"""
import pandas as pd

from base import campos as campos_def


def chaves():
    """Lista das chaves canônicas, na ordem de base/campos.py."""
    return [chave for (_g, chave, _r, _o, _d) in campos_def.CAMPOS]


def mapa_identidade():
    """Mapa para pontuar/validar a base já normalizada (chave -> própria chave)."""
    return {chave: chave for chave in chaves()}


def normalizar(dados, mapa):
    """Devolve um DataFrame com uma coluna por chave canônica (texto)."""
    n = len(dados)
    out = {}
    for chave in chaves():
        col = mapa.get(chave)
        if col and col in dados.columns:
            out[chave] = dados[col].astype(str).values
        else:
            out[chave] = [""] * n
    return pd.DataFrame(out)
