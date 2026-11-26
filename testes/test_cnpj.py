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


def test_nome_antigo_cnpj_valido_continua_existindo():
    # regras/validacao.py (pendências da tela Ranking) usa cnpj_valido — não pode sumir
    from regras import validacao  # noqa: F401
    assert cnpj.cnpj_valido(CERTO) is True and cnpj.cnpj_valido("123") is False


def test_pendencias_da_base_funcionam():
    import pandas as pd

    from regras import validacao
    dados = pd.DataFrame({"cnpj": [cnpj.formatar(CERTO), "123"], "nome_entidade": ["A", "B"]})
    mapa = {"cnpj": "cnpj", "nome_entidade": "nome_entidade"}
    v = validacao.validar(dados, mapa)
    assert v["invalido"] == 1


def test_data_de_abertura_do_formulario_2027_e_reconhecida():
    mapa = mapeamento.auto_map(["Nome da entidade", "CNPJ", "6. Data de Abertura da Entidade"])
    assert mapa["data_fundacao"] == "6. Data de Abertura da Entidade"


def test_pendencia_diz_qual_campo_esta_em_branco():
    import pandas as pd

    from regras import validacao
    dados = pd.DataFrame({"cnpj": [cnpj.formatar(CERTO)], "nome_entidade": ["A"], "data_fundacao": [""]})
    v = validacao.validar(dados, {"cnpj": "cnpj", "nome_entidade": "nome_entidade",
                                   "data_fundacao": "data_fundacao"})
    assert v["pendencias"].iloc[0]["Problema"] == "em branco: Data de abertura da entidade"


def test_robo_aceita_chaves_coladas_com_aspas(monkeypatch):
    import types

    from regras import nuvem, wix
    # Como no robô: sem secrets.toml (só as variáveis de ambiente do GitHub)
    monkeypatch.setattr(nuvem, "st", types.SimpleNamespace(secrets={}))
    monkeypatch.setattr(wix, "st", None)
    monkeypatch.setenv("SUPABASE_URL", ' "https://exemplo.supabase.co/rest/v1" ')
    monkeypatch.setenv("SUPABASE_KEY", '"chave-de-teste"')
    monkeypatch.setenv("WIX_SITE_ID", "'site-de-teste'")
    assert nuvem._config() == ("https://exemplo.supabase.co", "chave-de-teste")
    assert wix._cfg()["site_id"] == "site-de-teste"


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


def test_formulario_oficial_achado_pelo_nome_sem_form_id():
    from regras import wix
    forms = [("a", "CASE 2027 – Inscrição, Etapa 1 – Nova versão"), ("b", "Cópia de inscrições 2027"),
             ("c", "Formulário de Inscrição Case 2026"), ("d", "Envio de Documentos v3"),
             ("e", "Pesquisa de Satisfação CASE 2026")]
    assert wix.form_pelo_nome(forms) == "a"
    assert wix.form_pelo_nome(forms + [("f", "Inscrição 2027 (outra)")]) is None  # dois candidatos: não chuta


def test_email_de_cnpj_pronto_sem_citar_outra_instituicao():
    from regras import contato
    corpo = contato.modelo_cnpj("Associação Esportiva Exemplo", "11.222.333/0001-81", cnpj.ST_OUTRA,
                                "Maria Exemplo")
    assert corpo.startswith("Olá, Maria!") and "11.222.333/0001-81" in corpo
    assert "outra instituição" in corpo and "Cartão CNPJ" in corpo
    link = contato.link_email(["a@exemplo.org"], contato.ASSUNTO_CNPJ, corpo)
    assert link.startswith("mailto:a@exemplo.org?subject=") and "body=" in link


def test_link_do_outlook_ja_vem_preenchido():
    from regras import contato
    link = contato.link_outlook(["a@exemplo.org", "b@exemplo.org"], "Assunto teste", "Linha 1\nLinha 2")
    assert link.startswith("https://outlook.office.com/mail/deeplink/compose?to=a%40exemplo.org%2Cb%40exemplo.org")
    assert "subject=Assunto%20teste" in link and "body=Linha%201%0ALinha%202" in link
    assert contato.link_outlook(["sem-arroba"]) == ""


def test_conferir_de_novo_nao_apaga_o_aviso(monkeypatch):
    import pandas as pd
    errado = _troca(CERTO, 9)
    base = pd.DataFrame({"id_envio": ["x1"], "cnpj": [errado], "nome_entidade": [NOME]})
    monkeypatch.setattr(cnpj, "_consultar_padrao", lambda c: None)
    diags = {"x1": {"digitado": errado, "status": cnpj.ST_INVALIDO, "avisada_em": "26/11/2026 10:00",
                    "avisada_por": "equipe", "espera": "nova_inscricao"}}
    novo = cnpj.conferir_base(base, so_novas=False, diags=diags)
    assert novo["x1"]["espera"] == "nova_inscricao" and novo["x1"]["avisada_em"] == "26/11/2026 10:00"
