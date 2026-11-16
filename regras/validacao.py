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

    from base import campos as campos_def
    rotulo = {c[1]: c[2] for c in campos_def.CAMPOS}

    def vazios(linha):
        """Quais campos obrigatórios estão em branco (pelo nome, para a equipe saber o quê)."""
        return [rotulo.get(chave, chave) for chave in NAO_PODE_BRANCO
                if mapa.get(chave) and str(linha.get(mapa[chave], "")).strip() == ""]
    em_branco = dados.apply(vazios, axis=1) if n else pd.Series([], dtype=object)
    branco = em_branco.map(bool) if n else pd.Series([], dtype=bool)

    problemas = []
    for iv, rp, vz in zip(invalido, repetido, em_branco):
        partes = []
        if rp:
            partes.append("CNPJ repetido")
        if iv:
            partes.append("CNPJ inválido")
        if vz:
            partes.append("em branco: " + ", ".join(vz))
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
