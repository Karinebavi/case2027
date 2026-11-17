# -*- coding: utf-8 -*-
"""Relatórios: estado/cidade padronizados, tabelas, filtros e PDF — só com a base FICTÍCIA."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from regras import classificacao, localidade, mapeamento, normalizacao, pontuacao
from regras import relatorio_dados as rd


@pytest.mark.parametrize("digitado,uf", [
    ("SP", "SP"), ("s.p.", "SP"), ("Sao paulo", "SP"), ("MINAS", "MG"), ("Minas Gerias", "MG"),
    ("Pernanbuco", "PE"), ("MG - Minas Gerais", "MG"), ("Rio grande do sul (RS)", "RS"),
    ("Paraná", "PR"), ("Para", "PA"), ("Sta Catarina", "SC"), ("Espirito Santos", "ES"),
])
def test_estado_escrito_de_varios_jeitos(digitado, uf):
    assert localidade.uf(digitado)["uf"] == uf


@pytest.mark.parametrize("cidade,uf,esperado", [
    ("BH", "MG", "Belo Horizonte/MG"), ("Belo Horisonte", "MG", "Belo Horizonte/MG"),
    ("belo horizonte - mg", "", "Belo Horizonte/MG"), ("S. José dos Campos", "SP", "São José dos Campos/SP"),
    ("Mogi das Cruses", "SP", "Mogi das Cruzes/SP"), ("Floripa", "", "Florianópolis/SC"),
    ("Ourilandia", "PA", "Ourilândia do Norte/PA"), ("Cidade de Recife", "", "Recife/PE"),
    ("Taguatinga", "DF", "Brasília/DF"), ("Niteroi", "RJ", "Niterói/RJ"),
])
def test_cidade_com_erro_vira_a_oficial(cidade, uf, esperado):
    r = localidade.local(cidade, uf)
    assert f"{r['cidade']}/{r['uf']}" == esperado
    assert r["status"] in (localidade.CONFERE, localidade.CORRIGIDA)


@pytest.mark.parametrize("cidade,uf", [("Campinas", "MG"), ("Bom Jesus", ""), ("Mogi", "SP")])
def test_quando_nao_da_para_decidir_fica_a_conferir_com_sugestao(cidade, uf):
    r = localidade.local(cidade, uf)
    assert r["status"] == localidade.A_CONFERIR and r["sugestao"]


def _base():
    bruto = pd.read_csv("base/exemplo.csv", dtype=str).fillna("")
    d = normalizacao.normalizar(bruto, mapeamento.auto_map(list(bruto.columns)))
    d.loc[0, "cidade"], d.loc[0, "uf"] = "Belo Horisonte", "Minas"
    d.loc[1, "cidade"], d.loc[1, "uf"] = "BH", "mg"
    s = classificacao.classificar(pontuacao.calcular(d, normalizacao.mapa_identidade()), vagas=10)
    return rd.montar_base(d, s)


def test_grafias_diferentes_contam_como_uma_cidade_so():
    w = _base()
    t = rd.tabela_cidades(w)
    assert int(t.loc[t["Município/UF"] == "Belo Horizonte/MG", "Inscrições"].iloc[0]) >= 2
    assert "Belo Horisonte/MG" not in set(t["Município/UF"])


def test_cnpj_repetido_nao_mistura_inscricoes():
    w = _base()  # a base de exemplo tem duas inscrições com o mesmo CNPJ
    assert len(w) == 10 and w["Local"].iloc[0] == "Belo Horizonte/MG"


def test_filtros_e_percentuais():
    w = _base()
    so_mg = rd.aplicar_filtros(w, {"uf": ["MG"]})
    assert len(so_mg) >= 2 and set(so_mg["UF"]) == {"MG"}
    t = rd.tabela_territorio(w, "Região")
    assert abs(t["% do total"].sum() - 100) < 0.5
    assert "MG" in rd.descrever_filtros({"uf": ["MG"]})
    assert rd.tabela_notas(w).iloc[0]["Medida"] == "n"


def test_pdf_sai_sem_nomes_de_entidade():
    from regras import relatorio_pdf
    w = _base()
    pdf = relatorio_pdf.gerar(w, "nenhum", len(w))
    assert pdf[:4] == b"%PDF" and len(pdf) > 20_000
    import io

    import pdfplumber
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        texto = " ".join(p.extract_text() or "" for p in doc.pages)
    assert "Mapa do Brasil" in texto and "Nuvem de cidades" in texto  # gráficos em imagem
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        assert sum(len(p.images) for p in doc.pages) >= 8
    for nome in w["nome_entidade"]:
        assert nome not in texto  # relatório só com números agregados


def test_tela_de_relatorios_abre(monkeypatch):
    monkeypatch.setenv("CASE_TESTE", "1")
    at = AppTest.from_string('''
import pandas as pd
import streamlit as st
from regras import mapeamento, normalizacao, nuvem
nuvem.ativo = lambda: False
from telas import dashboard
if "dados" not in st.session_state:
    bruto = pd.read_csv("base/exemplo.csv", dtype=str).fillna("")
    st.session_state["dados"] = normalizacao.normalizar(bruto, mapeamento.auto_map(list(bruto.columns)))
    st.session_state["mapa"] = normalizacao.mapa_identidade()
    st.session_state["mapa_ok"] = True
dashboard.mostrar()
''', default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.metric) == 5 and not at.tabs  # uma página só, sem abas


def test_opcao_com_virgula_entre_parenteses_conta_uma_vez_so():
    w = pd.DataFrame({"modalidades": [
        "Futebol / Futsal, Lutas / Artes Marciais (Judô, Karatê, Jiu-Jitsu, etc.), Capoeira",
        "Lutas / Artes Marciais (Judô, Karatê, Jiu-Jitsu, etc.); Outro: Rugby"]})
    t = rd.tabela_modalidades(w)
    assert "Karatê" not in set(t["Modalidade"]) and "etc.)" not in set(t["Modalidade"])
    lutas = t[t["Modalidade"].str.startswith("Lutas")]
    assert len(lutas) == 1 and int(lutas["Inscrições"].iloc[0]) == 2
