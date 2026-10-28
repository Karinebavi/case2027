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


def test_fase1_ninguem_e_excluido(base):
    clf = _ranking(*base)
    assert (clf["Status"] == "Em classificação").all()
    assert clf["Posição"].notna().all()


def test_pendencia_vira_atencao_e_continua_no_ranking(base):
    dados, mapa = base
    for campo in ("computador", "internet", "disponibilidade"):
        dados.loc[0, mapa[campo]] = "Não"
    dados.loc[0, mapa["data_fundacao"]] = "2026-06-01"  # menos de 1 ano
    linha = _ranking(dados, mapa).loc[0]
    assert "Sem internet" in linha["Motivo"]
    assert "Menos de 1 ano" in linha["Motivo"]
    assert pd.notna(linha["Posição"])
    assert linha["Nota"] > 0  # pendência não zera a nota


def test_pergunta_que_nao_existe_no_formulario_pontua_zero(base):
    dados, mapa = base
    mapa = {**mapa, "p22": "", "p23": "", "p24": ""}  # como no formulário de 2026
    nota = pontuacao.calcular(dados, mapa, hoje=HOJE)
    assert (nota[["b4", "b5", "b6"]] == 0).all().all()
    assert (nota[["b1", "b2", "b7"]] > 0).all().all()


def test_faixas_de_equipe_de_2026_pontuam():
    assert pontuacao.EQUIPE["Acima de 2 colaboradores"] == 10
    assert pontuacao.EQUIPE["1 e 2 colaboradores"] == 8


def test_estatuto_em_foto_e_incompleto_nao_falta_de_finalidade():
    foto = SimpleNamespace(sem_texto=False, n_paginas=1, texto="x" * 769)
    completo = SimpleNamespace(sem_texto=False, n_paginas=12, texto="x" * 20000)
    assert _doc_incompleto(foto)
    assert not _doc_incompleto(completo)
    assert not _doc_incompleto(None)
