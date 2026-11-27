# -*- coding: utf-8 -*-
"""Áreas da Vale: destaque no Ranking e na planilha (base FICTÍCIA)."""
import io

import pandas as pd

from regras import areas, classificacao, exportacao, mapeamento, pontuacao

LISTA = [{"cidade": "Belo Horizonte", "uf": "MG", "codigo_ibge": "3106200"},
         {"cidade": "Santa Luzia", "uf": "MA", "codigo_ibge": "2110005"}]


def test_le_a_lista_no_formato_colado():
    itens, nao = areas.ler_colado("Juatuaba\tgabinete@exemplo.org\nMA (Maranhão)\nBacabeira *\n"
                                  "Itapecuru-mirim\nES (Espírito Santo)\nCidade Inventada XYZ")
    # Juatuaba (erro de digitação, sem UF) só existe em MG: o sistema acha Juatuba/MG sozinho
    assert [(x["cidade"], x["uf"]) for x in itens] == [("Juatuba", "MG"), ("Bacabeira", "MA"),
                                                       ("Itapecuru Mirim", "MA")]
    assert nao == ["Cidade Inventada XYZ"]


def test_cidade_padronizada_e_mesma_uf():
    assert areas.e_area("Belo Horizonte", "MG", LISTA)
    assert areas.e_area("Santa Luzia", "MA", LISTA) and not areas.e_area("Santa Luzia", "MG", LISTA)


def test_destaque_no_ranking_e_na_planilha(monkeypatch):
    monkeypatch.setattr(areas, "carregar", lambda forcar=False: LISTA)
    dados = pd.read_csv("base/exemplo.csv", dtype=str).fillna("")
    mapa = mapeamento.auto_map(list(dados.columns))
    dados.loc[0, mapa["cidade"]], dados.loc[0, mapa["uf"]] = "BH", "Minas"
    f = classificacao.classificar(pontuacao.calcular(dados, mapa), vagas=10)
    assert bool(f.loc[0, "Área Vale"]) and int(f["Área Vale"].sum()) >= 1
    xlsx = pd.read_excel(io.BytesIO(exportacao.montar_planilha(f, 10)), header=1, dtype=str).fillna("")
    assert "Área Vale" in xlsx.columns and (xlsx["Área Vale"] == "Sim").sum() == int(f["Área Vale"].sum())
