# -*- coding: utf-8 -*-
"""A tela do Ranking abre de verdade (Streamlit AppTest) — com a base FICTÍCIA, sem nuvem."""
from streamlit.testing.v1 import AppTest

_SCRIPT = '''
import pandas as pd
import streamlit as st
from regras import mapeamento, normalizacao, nuvem
nuvem.ativo = lambda: False            # nada de banco real no teste
from telas import resultado, _calculo

if "dados" not in st.session_state:
    bruto = pd.read_csv("base/exemplo.csv", dtype=str).fillna("")
    st.session_state["dados"] = normalizacao.normalizar(bruto, mapeamento.auto_map(list(bruto.columns)))
    st.session_state["mapa"] = normalizacao.mapa_identidade()
    st.session_state["mapa_ok"] = True
resultado.mostrar()

# a comparação lado a lado (o que aparece ao marcar 2+ linhas)
d = st.session_state["dados"]
f = _calculo.funil_df(d, st.session_state["mapa"], 10, 30).copy()
from regras.memoria import so_digitos
f["dig"] = f["CNPJ"].map(so_digitos)
f["Problemas"] = f["Motivo"]
resultado._comparar(f.head(3), d, st.session_state["mapa"])
'''


def test_ranking_abre_com_todas_as_respostas_e_comparacao(tmp_path, monkeypatch):
    monkeypatch.setenv("CASE_TESTE", "1")
    at = AppTest.from_string(_SCRIPT, default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    # a tabela do ranking e a da comparação foram desenhadas
    assert len(at.dataframe) >= 2
