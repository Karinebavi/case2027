# -*- coding: utf-8 -*-
"""21/22 x 23: respostas que não combinam (dados INVENTADOS)."""
from regras import coerencia, contato

LIE = "Leis de Incentivo ao Esporte , Fundo da Infância e da Adolescência (FIA)"
AINDA = "Ainda não tenho projeto na LIE"


def test_lie_na_21_e_ainda_nao_na_23_nao_combina():
    assert coerencia.checar({"p18": LIE, "p19": "Nunca executamos projetos", "p20_lie": AINDA})
    assert coerencia.perguntas_marcadas({"p18": LIE, "p19": LIE}) == ["21", "22"]


def test_combina_quando_a_23_tem_cadastro_ou_projeto():
    for r23 in ("Tenho cadastro no Sistema da Lei de Incentivo (SLI), mas ainda sem projeto elaborado",
                "Tenho projeto elaborado, submetido ou em fase de captação (ainda não executado)",
                "Já executei ou estou executando projeto(s) na LIE"):
        assert coerencia.checar({"p18": LIE, "p20_lie": r23}) == []
    assert coerencia.checar({"p18": "Leis de Incentivo à Cultura", "p20_lie": AINDA}) == []


def test_email_pede_confirmacao_e_traz_o_link():
    corpo = contato.modelo_coerencia_lie("Associação Exemplo", ["21"], AINDA, "Ana Exemplo",
                                         coerencia.LINK_FORMULARIO)
    assert corpo.startswith("Olá, Ana!") and "pergunta 21" in corpo and AINDA in corpo
    assert "www.case.org.br/inscricoes2027" in corpo and "refaça a inscrição" in corpo


_TELA = """
import pandas as pd
import streamlit as st
from regras import mapeamento, normalizacao, nuvem
nuvem.ativo = lambda: False
from telas import resultado
if "dados" not in st.session_state:
    bruto = pd.read_csv("base/exemplo.csv", dtype=str).fillna("")
    d = normalizacao.normalizar(bruto, mapeamento.auto_map(list(bruto.columns)))
    d["p18"] = d["p18"].astype(object)
    d.loc[0, "p18"] = "Leis de Incentivo ao Esporte"
    d["p20_lie"] = ""
    d.loc[0, "p20_lie"] = "Ainda não tenho projeto na LIE"
    d.loc[0, "email"] = "contato@exemplo.org"
    st.session_state["dados"] = d
    st.session_state["mapa"] = normalizacao.mapa_identidade()
    st.session_state["mapa_ok"] = True
resultado.mostrar()
"""


def test_ranking_mostra_a_lista_e_a_caixa_de_email(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("CASE_TESTE", "1")
    at = AppTest.from_string(_TELA, default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("não combinam" in e.label for e in at.expander)
    assert any("Lei de Incentivo ao Esporte" in t.value for t in at.text_area)
