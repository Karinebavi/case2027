# -*- coding: utf-8 -*-
"""
Testes da Documental: ligação inscrição ↔ documentos do Wix e o resumo que
alimenta o quadro do pool. Só dados FICTÍCIOS (dados_exemplo/documentos).
"""
import os

import pytest

from leitura import conferencia, resumo
from regras import contato, wix

DOCS = "dados_exemplo/documentos"


def _envio(entidade="", cnpj="", emails=(), _id="x", grupos=("cartao_cnpj", "estatuto", "ata")):
    return {"entidade": entidade, "cnpj": cnpj, "emails": list(emails), "_id": _id, "_data": "",
            "arquivos": {g: ([("a.pdf", "https://static.wixstatic.com/a.pdf")] if g in grupos else [])
                         for g in ("cartao_cnpj", "estatuto", "ata")}}


@pytest.mark.parametrize("rotulo, papel", [
    ("2. Informe o CNPJ da Entidade", "cnpj"),
    ("9. CARTÃO CNPJ", None),
    ("4. E-mail do responsável pelo preenchimento", "email"),
    ("3. Informe o nome completo da Entidade", "entidade"),
    ("Nome da Entidade", "entidade"),
    ("1. Nome completo do responsável pelo preenchimento", None),
    ("6. Informe qual é o seu cargo, função ou tipo de participação na entidade", None),
])
def test_papel_de_cada_campo_do_formulario_de_documentos(rotulo, papel):
    assert wix._papel_do_campo(rotulo) == papel


def test_cnpj_vem_antes_do_nome():
    envios = [_envio("Associação Esportiva Parecida da Silva", _id="errado"),
              _envio("Outro Nome Qualquer", cnpj="12345678000190", _id="certo")]
    achado, como = wix.localizar(envios, cnpj="12.345.678/0001-90",
                                 nome="Associação Esportiva Parecida da Silva")
    assert (achado["_id"], como) == ("certo", "CNPJ")


def test_nome_generico_nao_casa_com_entidade_qualquer():
    envios = [_envio("Associação")]
    achado, _ = wix.localizar(envios, nome="Associação Desportiva Meu Bairro Melhor")
    assert achado is None


def test_nome_completo_ainda_casa():
    envios = [_envio("Associação Desportiva Meu Bairro Melhor")]
    achado, como = wix.localizar(envios, nome="ASSOCIACAO DESPORTIVA MEU BAIRRO MELHOR - PONTA GROSSA")
    assert achado is not None and como == "nome"


def test_email_de_consultor_nao_liga_a_entidade_errada():
    envios = [_envio("Clube de Remo Ribeirinho do Norte", emails=["consultor@ex.com"])]
    achado, _ = wix.localizar(envios, emails=["consultor@ex.com"], nome="Instituto Bola Pra Frente do Sul")
    assert achado is None


def test_um_envio_vai_para_uma_entidade_so():
    envios = [_envio("Associação Esportiva Meu Bairro Melhor", _id="unico")]
    ligados = wix.ligar(envios, [
        {"chave": "a", "nome": "Associação Esportiva Meu Bairro Melhor"},
        {"chave": "b", "nome": "Associação Esportiva Meu Bairro Maior"},
        {"chave": "c", "nome": "Associação Esportiva Outro Lugar Qualquer"},
    ])
    assert list(ligados) == ["a"]


def test_anexos_do_nosso_site_no_wix_podem_ser_baixados(monkeypatch):
    monkeypatch.setattr(wix, "_cfg", lambda: {"site_id": "abc-123"})
    monkeypatch.setattr(wix.socket, "getaddrinfo", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    assert wix._url_segura("https://abc-123.usrfiles.com/ugd/estatuto.pdf")
    assert wix._url_segura("https://static.wixstatic.com/doc.pdf")
    assert not wix._url_segura("https://outro-site.usrfiles.com/ugd/estatuto.pdf")
    assert not wix._url_segura("http://abc-123.usrfiles.com/ugd/estatuto.pdf")
    assert not wix._url_segura("https://exemplo.com/estatuto.pdf")


def test_mais_recente_primeiro():
    envios = [_envio(cnpj="12345678000190", _id="novo"), _envio(cnpj="12345678000190", _id="velho")]
    assert wix.localizar(envios, cnpj="12345678000190")[0]["_id"] == "novo"


def _exemplos(sem=()):
    arq = {}
    for g, nome in (("cartao_cnpj", "cartao_cnpj_EXEMPLO.pdf"), ("estatuto", "estatuto_EXEMPLO.pdf"),
                    ("ata", "ata_EXEMPLO.pdf")):
        if g not in sem:
            with open(os.path.join(DOCS, nome), "rb") as fh:
                arq[g] = [(nome, fh.read())]
    return arq


def test_resumo_dos_documentos_de_exemplo():
    r = resumo.compacto(conferencia.analisar(_exemplos()))
    assert {r[d]["cor"] for d in ("cartao", "estatuto", "ata")} == {"verde"}
    assert r["estatuto"]["curto"].startswith("Art.")
    assert "finalidade" in r["estatuto"]["trecho"].lower()


def test_documento_que_nao_veio_fica_cinza_e_entra_no_pedido():
    r = resumo.compacto(conferencia.analisar(_exemplos(sem=("ata",))))
    assert r["ata"]["cor"] == "cinza"
    pedido = contato.modelo_pedir_documentos("Entidade Exemplo", resumo.pendencias(r))
    assert "Ata" in pedido
