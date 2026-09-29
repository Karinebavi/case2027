# -*- coding: utf-8 -*-
"""
Mapeamento automático das colunas.
Liga cada campo que o sistema precisa (CNPJ, Estado, cada pergunta...) à
coluna certa do CSV, procurando as 'dicas' dentro do nome da coluna.
Lógica pura — não tem tela aqui.
"""
from base import campos as campos_def


def auto_map(colunas):
    """Devolve {chave_do_campo: nome_da_coluna} com o que o sistema conseguiu achar."""
    mapa = {}
    usadas = set()
    for _grupo, chave, _rotulo, _obrig, dicas in campos_def.CAMPOS:
        achou = ""
        for coluna in colunas:
            texto = str(coluna).lower()
            if coluna not in usadas and any(d.lower() in texto for d in dicas):
                achou = coluna
                usadas.add(coluna)
                break
        mapa[chave] = achou
    return mapa
