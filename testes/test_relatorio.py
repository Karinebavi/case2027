# -*- coding: utf-8 -*-
"""Relatório da conferência por entidade — com uma leitura INVENTADA (sem dados reais)."""
import copy
import datetime as dt

from leitura import relatorio
from testes.test_regras_ia import BASE


def test_relatorio_tem_decisao_leitura_e_paginas():
    L = copy.deepcopy(BASE)
    L["paginas"] = [{"arquivo": "e.pdf", "pagina": 1, "tipo": "estatuto", "entidade": None},
                    {"arquivo": "e.pdf", "pagina": 2, "tipo": "estatuto", "entidade": None},
                    {"arquivo": "e.pdf", "pagina": 3, "tipo": "negativa_alteracoes", "entidade": None}]
    L["observacoes"] = ["Selo parcialmente cortado <script>"]
    h = relatorio.montar("Associação Exemplo", L, {"modelo": "claude-opus-5-5"}, cnpj="11.222.333/0001-81",
                         cidade_uf="Cidade Exemplo/MG", data_inscricao=dt.date(2026, 11, 6),
                         data_leitura="06/11/2026")
    assert "<h1>Associação Exemplo</h1>" in h
    assert "Apto" in h and "O que o sistema decidiu" in h
    assert "promover a prática esportiva" in h            # trecho da finalidade
    assert "p.1–2 estatuto · p.3 certidão negativa" in h   # páginas agrupadas pelo conteúdo
    assert "vários documentos" in h
    assert "<script>" not in h and "&lt;script&gt;" in h   # texto da IA nunca vira HTML


def test_relatorio_sem_estatuto_nem_ata_nao_quebra():
    L = copy.deepcopy(BASE)
    L["estatuto"], L["atas"] = None, []
    h = relatorio.montar("Associação Exemplo", L)
    assert "Não encontrado" in h and "Nenhuma ata" in h
