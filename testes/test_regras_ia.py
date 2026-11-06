# -*- coding: utf-8 -*-
"""Regras da conferência aplicadas à leitura da IA — com leituras INVENTADAS (sem dados reais)."""
import copy
import datetime as dt
import json
import os

import pytest

from leitura import regras_ia as R

INSCRICAO = dt.date(2026, 11, 6)


def _reg(**k):
    base = {"situacao": "registrado", "cartorio_nome": "Registro Civil das Pessoas Jurídicas de Cidade Exemplo",
            "e_registro_civil_pessoas_juridicas": True, "numero_registro": "100", "averbacao": "AV 3",
            "livro": "A-1", "folha": "10", "protocolo": "999", "data_registro": "10/01/2025", "selo": None,
            "cidade_cartorio": "Cidade Exemplo/MG", "arquivo": "x.pdf", "pagina": 2,
            "posicao_na_pagina": "rodapé", "trecho": "REGISTRADO", "incertezas": None}
    base.update(k)
    return base


BASE = {
    "paginas": [],
    "entidade": {"nome": "Associação Exemplo", "cnpj": None, "cidade_uf_sede": "Cidade Exemplo/MG",
                 "todos_os_documentos_sao_da_mesma_entidade": True, "observacao": None},
    "cartao": {"arquivo": "c.pdf", "pagina": 1, "nome_empresarial": "ASSOCIACAO EXEMPLO", "cnpj": None,
               "data_emissao": "06/11/2026", "situacao_cadastral": "ATIVA", "natureza_codigo": "399-9",
               "natureza_descricao": "Associação Privada", "data_abertura": "01/02/2010",
               "municipio_uf": "CIDADE EXEMPLO/MG"},
    "estatuto": {"arquivo": "e.pdf", "paginas": "1-8", "data_do_estatuto": "01/01/2020",
                 "finalidade": {"local": "artigo_de_finalidades", "artigo": "Art. 3º",
                                "titulo_secao": "Das Finalidades", "frase_de_abertura": "tem por finalidade",
                                "trecho": "promover a prática esportiva", "pagina": 1, "explicacao": None},
                 "outras_mencoes_esporte": [], "numeracao_artigos": {"sequencia_ok": True, "falhas": []},
                 "mandato_diretoria": {"duracao_anos": 4, "artigo": "Art. 20", "trecho": "mandato de 4 anos",
                                       "pagina": 4, "data_fixa_trecho": None, "prorrogacao_trecho": None},
                 "registro": _reg(arquivo="e.pdf", pagina=8)},
    "outros_estatutos": [],
    "atas": [{"arquivo": "a.pdf", "paginas": "1-2", "tipo": "eleicao_e_posse", "elege_ou_empossa_diretoria": True,
              "data_assembleia": "10/03/2025", "data_convocacao": None, "periodo_trecho": "mandato de 4 anos",
              "inicio_mandato": None, "fim_mandato": None, "duracao_anos": 4, "clausula_exercicio_trecho": None,
              "prorrogacao_trecho": None, "pagina_periodo": 1, "registro": _reg(arquivo="a.pdf")}],
    "outros_selos": [], "observacoes": [],
}


def _leitura(**mudar):
    L = copy.deepcopy(BASE)
    for caminho, valor in mudar.items():
        alvo = L
        partes = caminho.split("__")
        for p in partes[:-1]:
            alvo = alvo[int(p)] if p.isdigit() else alvo[p]
        alvo[partes[-1]] = valor
    return L


def _av(L, **k):
    return R.avaliar(L, data_inscricao=k.get("data", INSCRICAO), cnpj=k.get("cnpj"))


def _status(av, bloco, item_contem=""):
    return [i["status"] for i in av["itens"] if i["bloco"] == bloco and item_contem in i["item"]]


def test_tudo_certo_e_apto():
    av = _av(_leitura())
    assert av["resultado"] == "APTO", av["itens"]


@pytest.mark.parametrize("campo,valor", [
    ("cartao__situacao_cadastral", "BAIXADA"),
    ("cartao__natureza_codigo", "206-2"),
    ("cartao__nome_empresarial", "EXEMPLO ESPORTES LTDA"),
    ("cartao__data_abertura", "02/03/2026"),
])
def test_cartao_nao_apto(campo, valor):
    assert _av(_leitura(**{campo: valor}))["resultado"] == "NAO_APTO"


def test_abertura_no_dia_do_corte_ainda_vale():
    assert _status(_av(_leitura(cartao__data_abertura="01/03/2026")), "cartao", "abertura") == ["OK"]


def test_emissao_diferente_da_inscricao_e_atencao():
    assert _status(_av(_leitura(cartao__data_emissao="01/10/2026")), "cartao", "emissão") == ["ATENCAO"]


@pytest.mark.parametrize("local", ["prerrogativas", "meios_ou_atividades", "outro_artigo", "natureza_ou_carater"])
def test_esporte_fora_do_artigo_de_finalidades_e_atencao(local):
    assert _status(_av(_leitura(estatuto__finalidade__local=local)), "finalidade", "esportiva") == ["ATENCAO"]


def test_sem_esporte_e_pendencia():
    av = _av(_leitura(estatuto__finalidade__local="nao_encontrado"))
    assert _status(av, "finalidade", "esportiva") == ["PENDENCIA"]


def test_numeracao_quebrada_e_atencao():
    L = _leitura(estatuto__numeracao_artigos={"sequencia_ok": False,
                                               "falhas": [{"descricao": "Art. 52 repetido", "pagina": 9}]})
    assert _status(_av(L), "finalidade", "Numeração") == ["ATENCAO"]


def test_mandato_pelo_estatuto_quando_a_ata_nao_diz_duracao():
    L = _leitura(atas__0__duracao_anos=None)
    item = [i for i in _av(L)["itens"] if i["item"] == "Mandato vigente"][0]
    assert item["status"] == "OK" and "estatuto" in item["motivo"]


def test_mandato_vencido_e_pendencia_e_com_prorrogacao_e_atencao():
    L = _leitura(atas__0__data_assembleia="10/03/2020")
    assert _status(_av(L), "mandato", "vigente") == ["PENDENCIA"]
    L = _leitura(atas__0__data_assembleia="10/03/2020", atas__0__prorrogacao_trecho="prorroga-se até a posse")
    assert _status(_av(L), "mandato", "vigente") == ["ATENCAO"]


def test_ata_de_fundacao_vale_se_o_mandato_esta_vigente():
    L = _leitura(atas__0__tipo="fundacao", atas__0__data_assembleia="01/02/2025")
    assert _status(_av(L), "mandato", "vigente") == ["OK"]


def test_periodo_so_com_mes_e_ano_vai_ate_o_fim_do_mes():
    L = _leitura(atas__0__inicio_mandato="06/2026", atas__0__fim_mandato="06/2028")
    item = [i for i in _av(L)["itens"] if i["item"] == "Mandato vigente"][0]
    assert item["status"] == "OK" and "30/06/2028" in item["motivo"]


def test_ata_e_estatuto_com_duracao_diferente_e_atencao():
    assert _status(_av(_leitura(atas__0__duracao_anos=2)), "mandato", "estatuto") == ["ATENCAO"]


def test_escolhe_a_ata_mais_recente_da_diretoria():
    L = _leitura()
    velha = copy.deepcopy(L["atas"][0])
    velha["data_assembleia"] = "10/03/2019"
    L["atas"].insert(0, velha)
    assert _status(_av(L), "mandato", "vigente") == ["OK"]


def test_so_protocolado_e_pendencia():
    L = _leitura(estatuto__registro=_reg(situacao="so_protocolado"))
    assert _status(_av(L), "cartorio", "estatuto") == ["PENDENCIA"]


def test_carimbo_ilegivel_e_confira_visualmente_nunca_pendencia():
    L = _leitura(atas__0__registro=_reg(situacao="ilegivel"))
    assert _status(_av(L), "cartorio", "ata") == ["CONFIRA"]


def test_numero_incerto_no_carimbo_pede_conferencia_visual():
    L = _leitura(atas__0__registro=_reg(incertezas="AV 45 ou 46"))
    assert "CONFIRA" in _status(_av(L), "cartorio", "ata")


def test_cartorio_que_nao_e_pessoa_juridica_e_atencao():
    L = _leitura(estatuto__registro=_reg(e_registro_civil_pessoas_juridicas=False,
                                         cartorio_nome="Tabelionato de Notas"))
    assert _status(_av(L), "cartorio", "Registro do estatuto") == ["ATENCAO"]


def test_cartorio_em_outra_cidade_e_atencao():
    L = _leitura(atas__0__registro=_reg(cidade_cartorio="Outra Cidade/MG"))
    assert _status(_av(L), "cartorio", "Cidade") == ["ATENCAO"]


def test_documentos_de_outro_cnpj_sao_pendencia():
    L = _leitura(cartao__cnpj="11.222.333/0001-81")
    av = _av(L, cnpj="11222333000100")
    assert _status(av, "documentos") == ["PENDENCIA"]


def test_datas_mes_e_ano():
    assert R.data("06/2028", fim_do_mes=True) == dt.date(2028, 6, 30)
    assert R.data("02/2028", fim_do_mes=True) == dt.date(2028, 2, 29)
    assert R.data("05/05/2025") == dt.date(2025, 5, 5)


# ---------------------------------------------------------------- gabarito (só nesta máquina)
# As leituras reais ficam em testes/gabarito/resultados/ (fora do GitHub). No GitHub estes testes pulam.
_RES = os.path.join(os.path.dirname(__file__), "gabarito", "resultados")
_ESPERADO = {
    "caso_01": {"cartao": "OK", "mandato": "OK"},
    # finalidade do caso 2: a decidir pela Karine (o PDF repete o Art. 36 — Atenção ou OK?);
    # cartório: registrado, mas o protocolo da ata está pouco legível = Confira visualmente
    "caso_02": {"cartao": "OK", "mandato": "OK", "cartorio": "CONFIRA"},
    "caso_03": {"cartao": "OK", "finalidade": "ATENCAO", "mandato": "OK", "cartorio": "OK"},
    "caso_04": {"cartao": "OK", "mandato": "OK", "cartorio": "OK"},
}


_INSCRICAO_CASO = {"caso_01": dt.date(2026, 6, 9), "caso_02": dt.date(2026, 4, 27),
                   "caso_03": dt.date(2026, 5, 28), "caso_04": dt.date(2026, 4, 1)}


def _leituras_salvas():
    if not os.path.isdir(_RES):
        return []
    from leitura.leitor_ia import MODELO_PADRAO  # mede o modelo em uso (o comparativo fica no script)
    return sorted(f for f in os.listdir(_RES) if f.endswith(f"__{MODELO_PADRAO}.json"))


@pytest.mark.skipif(not _leituras_salvas(), reason="gabarito só existe na máquina da Karine")
@pytest.mark.parametrize("arquivo", _leituras_salvas() or ["-"])
def test_gabarito(arquivo):
    caso = arquivo[:7]  # "caso_01"... (os nomes das pastas ficam só na máquina)
    with open(os.path.join(_RES, arquivo), encoding="utf-8") as f:
        L = json.load(f)["leitura"]
    av = R.avaliar(L, data_inscricao=_INSCRICAO_CASO[caso])
    for bloco, st in _ESPERADO[caso].items():
        assert av["blocos"].get(bloco) == st, (bloco, [i for i in av["itens"] if i["bloco"] == bloco])
