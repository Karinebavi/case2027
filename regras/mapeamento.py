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
        # As dicas vão da mais específica para a mais genérica: tenta cada dica
        # em TODAS as colunas antes de passar à próxima. Assim "executou" acha a
        # pergunta certa antes que "execu" pegue "local para a execução das
        # atividades" (o Wix não entrega as colunas na ordem do formulário).
        achou = ""
        for d in dicas:
            achou = next((c for c in colunas if c not in usadas and d.lower() in str(c).lower()), "")
            if achou:
                usadas.add(achou)
                break
        mapa[chave] = achou
    return mapa
