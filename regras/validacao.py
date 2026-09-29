# -*- coding: utf-8 -*-
"""
Validação da base — sem tela.
Confere três coisas em cada inscrição:
  - CNPJ inválido (dígitos não batem)
  - CNPJ repetido (aparece mais de uma vez)
  - campo obrigatório em branco
Devolve um resumo com as contagens e a lista das pendências.
"""
import pandas as pd

from regras import cnpj as cnpj_mod

# campos que não podem ficar em branco (chaves do mapa)
NAO_PODE_BRANCO = ["cnpj", "uf", "data_fundacao", "p18", "p19", "p21", "p22", "p23", "p24"]


def validar(dados, mapa):
    n = len(dados)
    col_cnpj = mapa.get("cnpj")
    col_nome = mapa.get("nome_entidade")
    col_uf = mapa.get("uf")

    cnpjs = dados[col_cnpj].astype(str).str.strip() if col_cnpj else pd.Series([""] * n)
    invalido = ~cnpjs.map(cnpj_mod.cnpj_valido)
    repetido = cnpjs.duplicated(keep=False) & cnpjs.ne("")

    def tem_branco(linha):
        for chave in NAO_PODE_BRANCO:
            col = mapa.get(chave)
            if col and str(linha.get(col, "")).strip() == "":
                return True
        return False
    branco = dados.apply(tem_branco, axis=1)

    problemas = []
    for iv, rp, br in zip(invalido, repetido, branco):
        partes = []
        if rp:
            partes.append("CNPJ repetido")
        if iv:
            partes.append("CNPJ inválido")
        if br:
            partes.append("campo obrigatório em branco")
        problemas.append(" · ".join(partes))

    pendentes = (invalido | repetido | branco).values
    tabela = pd.DataFrame({
        "Entidade": dados[col_nome].values if col_nome else [""] * n,
        "Estado": dados[col_uf].values if col_uf else [""] * n,
        "CNPJ": cnpjs.values,
        "Problema": problemas,
    })[pendentes]

    return {
        "total": n,
        "prontas": int((~(invalido | repetido | branco)).sum()),
        "repetido": int(repetido.sum()),
        "invalido": int(invalido.sum()),
        "branco": int(branco.sum()),
        "pendencias": tabela,
    }
