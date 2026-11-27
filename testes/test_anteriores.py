# -*- coding: utf-8 -*-
"""Quem já participou do CASE é eliminado (nomes e CNPJs INVENTADOS)."""
import pandas as pd

from regras import anteriores, classificacao, mapeamento, pontuacao
from regras import cnpj as cnpj_mod

CNPJ = cnpj_mod.completar("112223330001")
LISTA = [{"cnpj": CNPJ, "nome": "Associação Esportiva Exemplo", "fontes": ["CASE 2026"]},
         {"cnpj": "", "nome": "Instituto Amigo de Todos", "fontes": ["CASE 2026 (desistiu)"]}]


def test_reconhece_por_cnpj_e_por_nome():
    assert "CASE 2026" in anteriores.conferir(cnpj_mod.formatar(CNPJ), "Outro nome qualquer", LISTA)
    assert "pelo nome" in anteriores.conferir("", "INSTITUTO AMIGO DE TODOS", LISTA)
    assert anteriores.conferir("", "Instituto Amigos do Bairro Novo", LISTA) == ""


def test_le_a_lista_colada_como_na_planilha():
    itens = anteriores.ler_colado("5º ESPORTE CLUBE EXEMPLO (repescagem)\t13.631.118.000.1-60\n\n"
                                  "INSTITUTO EXEMPLO\t47002273/0001-39")
    assert [i["cnpj"] for i in itens] == ["13631118000160", "47002273000139"]
    assert itens[0]["nome"] == "ESPORTE CLUBE EXEMPLO (repescagem)"
    assert len(anteriores.juntar(itens, itens)) == 2  # não duplica


def test_quem_ja_participou_fica_eliminada(monkeypatch):
    monkeypatch.setattr(anteriores, "carregar", lambda forcar=False: LISTA)
    dados = pd.read_csv("base/exemplo.csv", dtype=str).fillna("")
    mapa = mapeamento.auto_map(list(dados.columns))
    for campo in ("estatuto", "mandato", "registro", "computador", "internet", "disponibilidade"):
        if mapa.get(campo):
            dados.loc[0, mapa[campo]] = "Sim"
    dados.loc[0, mapa["data_fundacao"]] = "2015-01-01"
    dados.loc[0, mapa["cnpj"]] = cnpj_mod.formatar(CNPJ)
    linha = classificacao.classificar(pontuacao.calcular(dados, mapa), vagas=10).loc[0]
    assert linha["Status"] == "Eliminada" and "Já participou do CASE" in linha["Motivo"]
