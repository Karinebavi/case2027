# -*- coding: utf-8 -*-
"""Triagem dos arquivos antes da leitura pela IA — com PDFs INVENTADOS (sem dados reais)."""
from leitura import conferencia, triagem
from testes.test_documental import _pdf_de_texto

CARTAO = _pdf_de_texto("REPUBLICA FEDERATIVA DO BRASIL CADASTRO NACIONAL DA PESSOA JURIDICA "
                       "COMPROVANTE DE INSCRICAO E DE SITUACAO CADASTRAL Nome empresarial ASSOCIACAO EXEMPLO "
                       "Natureza juridica 399-9 Associacao Privada Situacao cadastral ATIVA")
ESTATUTO = _pdf_de_texto("ESTATUTO SOCIAL DA ASSOCIACAO EXEMPLO. CAPITULO I - DA DENOMINACAO, SEDE E FINS. "
                         "Art. 1o A Associacao Exemplo e uma associacao civil sem fins economicos. "
                         "Art. 2o Tem por finalidade promover a pratica esportiva.")
CONVITE = _pdf_de_texto("Prezada equipe, temos a satisfacao de convida-la para o workshop de boas-vindas do "
                        "programa, que acontecera no auditorio principal, com palestras, coffee break e "
                        "apresentacao das proximas etapas. Contamos com a sua presenca. Confirme a participacao "
                        "pelo telefone ou e-mail informados neste convite. Atenciosamente, a coordenacao. " * 2)
ESCANEADO = _pdf_de_texto("")  # sem texto (como um PDF escaneado)
WORD = b"PK\x03\x04" + b"conteudo de um arquivo do Word" * 20


def _tri(arquivos):
    return {(t["grupo"], t["nome"]): t for t in triagem.triar(arquivos, api_key=None)[0]}


def test_documento_certo_passa_pelo_texto_sem_custo():
    t = _tri({"cartao_cnpj": [("c.pdf", CARTAO)], "estatuto": [("e.pdf", ESTATUTO)]})
    assert t[("cartao_cnpj", "c.pdf")]["passa"] and t[("cartao_cnpj", "c.pdf")]["tipo"] == "cartao_cnpj"
    assert t[("estatuto", "e.pdf")]["passa"] and t[("estatuto", "e.pdf")]["tipo"] == "estatuto"


def test_texto_sem_nenhuma_marca_fica_fora():
    t = _tri({"estatuto": [("convite.pdf", CONVITE)]})[("estatuto", "convite.pdf")]
    assert not t["passa"] and t["como"] == "texto"
    assert "Prezada" not in t["motivo"]  # não copia o texto (pode ter nome de pessoa)


def test_word_e_excel_ficam_fora_pelo_formato():
    t = _tri({"ata": [("timbrado.docx", WORD)]})[("ata", "timbrado.docx")]
    assert not t["passa"] and t["como"] == "formato"


def test_escaneado_sem_ia_na_duvida_passa():
    t = _tri({"ata": [("ata.pdf", ESCANEADO)]})[("ata", "ata.pdf")]
    assert t["passa"]


def test_so_os_que_passam():
    arq = {"cartao_cnpj": [("c.pdf", CARTAO)], "estatuto": [("convite.pdf", CONVITE)], "ata": [("t.docx", WORD)]}
    tri, _ = triagem.triar(arq, api_key=None)
    assert triagem.so_os_que_passam(arq, tri) == {"cartao_cnpj": [("c.pdf", CARTAO)], "estatuto": [], "ata": []}


def test_nenhum_arquivo_certo_nem_chama_a_leitura_paga(monkeypatch):
    from leitura import ia, leitor_ia
    monkeypatch.setattr(conferencia, "ia_ligada", lambda: True)
    monkeypatch.setattr(ia, "_cfg", lambda: {"anthropic_api_key": "", "modelo_documentos": ""})

    def nao_pode(*a, **k):
        raise AssertionError("a leitura completa não deveria ser chamada")
    monkeypatch.setattr(leitor_ia, "ler", nao_pode)
    r, salvar, info = conferencia.analisar_ia({"cartao_cnpj": [("convite.pdf", CONVITE)],
                                              "estatuto": [("convite.pdf", CONVITE)], "ata": [("t.docx", WORD)]})
    assert info["so_triagem"] and r["resultado"] == "NAO_APTO"
    assert any("fora do padrão" in linha[1] for linha in r["cartao"]["linhas"])
