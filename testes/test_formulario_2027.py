# -*- coding: utf-8 -*-
"""
O formulário de inscrição de 2027 (Wix) pontua certo? Inscrições FICTÍCIAS,
escritas como o Wix entrega: rótulos das perguntas e opções com os espaços
sobrando que vêm do formulário.
"""
import pandas as pd

from regras import mapeamento, normalizacao, pontuacao

ROTULOS = {
    "nome": "7. Nome Completo da Entidade",
    "cnpj": "5. CNPJ da Entidade - favor inserir no formato (00.000.000/0000-00)",
    "fundacao": "6. Data de Fundação da Entidade",
    "uf": "11. Estado",
    "cidade": "10. Cidade",
    "resp": "1. Nome completo do responsável pelo preenchimento",
    "email": "2. E-mail do responsável pelo preenchimento",
    "estatuto": "14. No estatuto social da entidade, o esporte aparece escrito entre as finalidades?",
    "computador": "17.  A entidade tem um computador ou notebook funcionando, com câmera e microfone?",
    "internet": "18.  A entidade tem acesso à internet para acompanhar as reuniões online?",
    "disp": "19. Alguém da entidade tem 2h semanais disponíveis, durante 10 meses?",
    "p18": "20. A entidade já apresentou algum projeto para captar recursos?",
    "p19": "21. A entidade já executou algum projeto com recursos aprovados?",
    "lie": "22.  Qual é a situação da entidade em relação aos projetos na Lei de Incentivo ao Esporte (LIE)?",
    "p21": "23. Quantas pessoas atuam no dia a dia da entidade hoje?",
    "p22": "24. Qual foi a receita bruta TOTAL da entidade no último ano fiscal?",
    "p23": "25. A entidade tem espaço físico para a sua gestão e administração?",
    "p24": "26. A entidade tem local para a execução das atividades esportivas e projetos sociais?",
    "canais": "27. Quais canais digitais a entidade tem hoje?",
    "links": "Cole o link (se tiver) — site, Instagram, Facebook, outra rede — campos opcionais",
    "benef": "29. Quantas pessoas a entidade atende hoje, aproximadamente?",
    "envio": "Data de envio",
}


def _inscricao(cnpj, canais, links=""):
    return {
        ROTULOS["nome"]: "Associação Fictícia de Teste", ROTULOS["cnpj"]: cnpj,
        ROTULOS["fundacao"]: "2015-03-15", ROTULOS["uf"]: "SP", ROTULOS["cidade"]: "Campinas",
        ROTULOS["resp"]: "Pessoa Fictícia", ROTULOS["email"]: "teste@exemplo.org",
        ROTULOS["estatuto"]: " Sim — o estatuto já inclui o esporte entre as finalidades ou objetivos da entidade. ",
        ROTULOS["computador"]: "Sim", ROTULOS["internet"]: "Sim", ROTULOS["disp"]: "Sim",
        ROTULOS["p18"]: "Leis de Incentivo ao Esporte , Emenda Parlamentar",
        ROTULOS["p19"]: " Leis de Incentivo ao Esporte ",
        ROTULOS["lie"]: " Ainda não tenho projeto na LIE ",
        ROTULOS["p21"]: " 3 a 5 ",
        ROTULOS["p22"]: "De R$ 51 mil a R$ 150 mil ",
        ROTULOS["p23"]: "Utiliza espaço cedido por parceiros ou instituições ",
        ROTULOS["p24"]: " Utiliza instalações públicas ou cedidas por parceiros (praças, escolas, ginásios, etc.) ",
        ROTULOS["canais"]: canais, ROTULOS["links"]: links,
        ROTULOS["benef"]: "120", ROTULOS["envio"]: "2027-02-10T13:00:00Z",
    }


def _notas(*inscricoes):
    df = pd.DataFrame(list(inscricoes))
    mapa = mapeamento.auto_map(list(df.columns))
    norm = normalizacao.normalizar(df, mapa)
    return mapa, pontuacao.calcular(norm, normalizacao.mapa_identidade())


def test_perguntas_de_2027_sao_reconhecidas():
    mapa, _ = _notas(_inscricao("11222333000181", "  Instagram"))
    assert mapa["canais"] == ROTULOS["canais"]
    assert mapa["beneficiarios"] == ROTULOS["benef"]
    assert mapa["data_envio"] == ROTULOS["envio"]
    for chave in ("p18", "p19", "p21", "p22", "p23", "p24", "computador", "internet", "disponibilidade"):
        assert mapa[chave], chave


def test_inscricao_de_2027_pontua_todos_os_blocos():
    _, nota = _notas(_inscricao("11222333000181", "  Instagram,  Facebook "))
    linha = nota.iloc[0]
    # 2 mecanismos (3) + 1 executado (10) + equipe 3-5 (10) + receita 51-150 mil (10)
    # + espaço cedido (10) + instalações públicas (10) + só redes sociais (10)
    assert [linha[b] for b in ("b1", "b2", "b3", "b4", "b5", "b6", "b7")] == [3, 10, 10, 10, 10, 10, 10]
    assert linha["Nota"] == 63


def test_canais_vem_da_pergunta_de_marcar_e_nao_do_campo_de_links():
    _, nota = _notas(
        _inscricao("11222333000181", "Site próprio ", links="instagram.com/ficticia"),
        _inscricao("44555666000172", "Não temos canais digitais \n", links="instagram.com/ficticia"),
        _inscricao("77888999000163", "Site próprio ,  Instagram"),
    )
    assert list(nota["b7"]) == [8, 4, 6]
