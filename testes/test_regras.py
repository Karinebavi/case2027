# -*- coding: utf-8 -*-
"""
Testes das regras combinadas com a Karine (docs/LOGICA-DO-SISTEMA.md).
Rodam sozinhos no GitHub a cada envio. Usam só a base FICTÍCIA base/exemplo.csv
— nada de dado real aqui.
"""
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from leitura.parecer import _doc_incompleto
from regras import classificacao, mapeamento, pontuacao

HOJE = date(2026, 10, 1)


@pytest.fixture
def base():
    dados = pd.read_csv("base/exemplo.csv", dtype=str).fillna("")
    return dados, mapeamento.auto_map(list(dados.columns))


def _ranking(dados, mapa):
    return classificacao.classificar(pontuacao.calcular(dados, mapa, hoje=HOJE), vagas=10)


ELIMINATORIAS = ("estatuto", "mandato", "registro", "computador", "internet", "disponibilidade")


def _apta(dados, mapa, i=0):
    """Deixa a inscrição i respondendo 'Sim' em todas as eliminatórias e com CNPJ antigo."""
    for campo in ELIMINATORIAS:
        if mapa.get(campo):
            dados.loc[i, mapa[campo]] = "Sim"
    dados.loc[i, mapa["data_fundacao"]] = "2015-01-01"


def test_quem_atende_as_eliminatorias_fica_no_ranking(base):
    dados, mapa = base
    _apta(dados, mapa)
    linha = _ranking(dados, mapa).loc[0]
    assert linha["Status"] == "Em classificação" and pd.notna(linha["Posição"])


@pytest.mark.parametrize("campo,numero", [("computador", "17."), ("internet", "18."), ("disponibilidade", "19.")])
def test_nao_numa_eliminatoria_elimina_mas_continua_visivel(base, campo, numero):
    # Regulamento 8.1: perguntas 14 a 19 são eliminatórias (decisão da Karine em 16/11/2026)
    dados, mapa = base
    _apta(dados, mapa)
    dados.loc[0, mapa[campo]] = "Não"
    linha = _ranking(dados, mapa).loc[0]
    assert linha["Status"] == "Eliminada" and linha["Situação"] == "Eliminada"
    assert pd.isna(linha["Posição"])            # sem posição no ranking
    assert linha["Motivo"].startswith(numero)   # o motivo diz qual pergunta
    assert linha["Nota"] > 0                    # a nota continua aparecendo


def test_cnpj_aberto_depois_do_corte_elimina(base):
    dados, mapa = base
    _apta(dados, mapa)
    dados.loc[0, mapa["data_fundacao"]] = "2026-06-01"
    assert _ranking(dados, mapa).loc[0]["Status"] == "Eliminada"
    dados.loc[0, mapa["data_fundacao"]] = "2026-03-01"  # no dia do corte ainda vale
    assert _ranking(dados, mapa).loc[0]["Status"] == "Em classificação"


def test_pergunta_em_branco_nao_elimina_vira_atencao(base):
    dados, mapa = base
    _apta(dados, mapa)
    dados.loc[0, mapa["computador"]] = ""
    linha = _ranking(dados, mapa).loc[0]
    assert linha["Status"] == "Em classificação" and "17. não respondida" in linha["Motivo"]


def test_pergunta_que_nao_existe_no_formulario_pontua_zero(base):
    dados, mapa = base
    mapa = {**mapa, "p22": "", "p23": "", "p24": ""}  # como no formulário de 2026
    nota = pontuacao.calcular(dados, mapa, hoje=HOJE)
    assert (nota[["b4", "b5", "b6"]] == 0).all().all()
    assert (nota[["b1", "b2", "b7"]] > 0).all().all()


def test_regua_oficial_soma_70_pontos():
    # Régua oficial (docs/REGUA-DE-PONTUACAO.md): 7 blocos de até 10 pontos.
    maximos = [max(pontuacao.NOTA_MECANISMO.values())] * 2 + [
        max(t.values()) for t in (pontuacao.EQUIPE, pontuacao.RECEITA, pontuacao.INFRA_ADMIN, pontuacao.INFRA_ESP)
    ] + [10]
    assert maximos == [10] * 7 and sum(maximos) == 70
    # sem faixas do teste de 2026
    assert set(pontuacao.EQUIPE) == {"1 ou 2", "3 a 5", "6 a 8", "9 a 12", "Mais de 12"}


def test_estatuto_em_foto_e_incompleto_nao_falta_de_finalidade():
    foto = SimpleNamespace(sem_texto=False, n_paginas=1, texto="x" * 769)
    completo = SimpleNamespace(sem_texto=False, n_paginas=12, texto="x" * 20000)
    assert _doc_incompleto(foto)
    assert not _doc_incompleto(completo)
    assert not _doc_incompleto(None)
