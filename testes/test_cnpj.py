# -*- coding: utf-8 -*-
"""Conferência do CNPJ digitado — números e nomes INVENTADOS; a 'Receita' aqui é falsa."""
from base import campos as campos_def
from regras import cnpj, mapeamento

CERTO = cnpj.completar("112223330001")          # CNPJ válido inventado
OUTRO = cnpj.completar("998887770001")
NOME = "Associação Esportiva Exemplo"


def _receita(tabela):
    return lambda c: tabela.get(c)


def _troca(d, i):
    return d[:i] + str((int(d[i]) + 1) % 10) + d[i + 1:]


def test_digito_verificador():
    assert cnpj.valido(CERTO) and cnpj.valido(cnpj.formatar(CERTO))
    assert not cnpj.valido(_troca(CERTO, 5))
    assert not cnpj.valido("11111111111111")


def test_candidatos_acham_o_numero_certo():
    assert CERTO in dict(cnpj.candidatos(_troca(CERTO, 3)))                         # um dígito trocado
    invertido = CERTO[:4] + CERTO[5] + CERTO[4] + CERTO[6:]
    if invertido != CERTO:
        assert CERTO in dict(cnpj.candidatos(invertido))                            # dois invertidos
    assert CERTO in dict(cnpj.candidatos(CERTO[:12]))                               # faltam os 2 finais
    assert CERTO in dict(cnpj.candidatos(CERTO[:7] + CERTO[8:]))                    # um faltando
    assert set(dict(cnpj.candidatos(CERTO + OUTRO))) == {CERTO, OUTRO}             # dois colados


def test_semelhanca_de_nome():
    assert cnpj.semelhanca(NOME, "ASSOCIACAO ESPORTIVA EXEMPLO") >= cnpj.LIMIAR_NOME
    assert cnpj.semelhanca(NOME, "PADARIA BOM PAO LTDA") < cnpj.LIMIAR_NOME


def test_valido_e_nome_bate_confere():
    d = cnpj.diagnosticar(CERTO, NOME, consultar=_receita({CERTO: {"razao_social": "ASSOCIACAO ESPORTIVA EXEMPLO"}}))
    assert d["status"] == cnpj.ST_OK and not d["sugestoes"]


def test_valido_mas_de_outra_entidade():
    d = cnpj.diagnosticar(CERTO, NOME, consultar=_receita({CERTO: {"razao_social": "PADARIA BOM PAO LTDA"}}))
    assert d["status"] == cnpj.ST_OUTRA and "PADARIA" in d["detalhe"]


def test_digitado_errado_sugere_o_que_bate_na_receita():
    errado = _troca(CERTO, 9)
    d = cnpj.diagnosticar(errado, NOME, consultar=_receita({CERTO: {"razao_social": "ASSOC ESPORTIVA EXEMPLO",
                                                                     "municipio": "Cidade", "uf": "MG"}}))
    assert d["status"] == cnpj.ST_INVALIDO
    assert d["sugestoes"][0]["cnpj"] == CERTO and d["sugestoes"][0]["semelhanca"] >= cnpj.LIMIAR_NOME


def test_cartao_cnpj_vem_primeiro_e_confirmacao_diferente_avisa():
    d = cnpj.diagnosticar(_troca(CERTO, 2), NOME, cnpj_cartao=CERTO, consultar=_receita({}))
    assert d["sugestoes"][0]["cnpj"] == CERTO and d["sugestoes"][0]["fonte"].startswith("cartão")
    d = cnpj.diagnosticar(CERTO, NOME, confirmacao=OUTRO,
                          consultar=_receita({CERTO: {"razao_social": "ASSOCIACAO ESPORTIVA EXEMPLO"}}))
    assert d["status"] == cnpj.ST_CONFIRMACAO and d["sugestoes"][0]["cnpj"] == OUTRO


def test_campo_de_confirmacao_nao_rouba_a_coluna_do_cnpj():
    chaves = [c[1] for c in campos_def.CAMPOS]
    assert chaves.index("cnpj_confirmacao") < chaves.index("cnpj")
    mapa = mapeamento.auto_map(["Confirme o CNPJ", "Nome da entidade", "CNPJ da entidade", "Cartão CNPJ (arquivo)"])
    assert mapa["cnpj_confirmacao"] == "Confirme o CNPJ" and mapa["cnpj"] == "CNPJ da entidade"
