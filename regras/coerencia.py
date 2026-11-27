# -*- coding: utf-8 -*-
"""
Respostas que não combinam entre si (pedido da Karine, 27/11/2026).

Pergunta 21 (projetos que já escreveu) ou 22 (projetos que já executou) marcando a
Lei de Incentivo ao Esporte, e a 23 (situação na LIE) dizendo "Ainda não tenho
projeto na LIE": não combina — quem escreveu/executou projeto na LIE tem pelo menos
cadastro, projeto submetido ou executado. Não muda a nota: vira um aviso na coluna
Problemas do Ranking e a equipe pode mandar e-mail pedindo confirmação.
"""
LINK_FORMULARIO = "https://www.case.org.br/inscricoes2027"


def _marcou_lie(texto):
    return "incentivo ao esporte" in str(texto or "").lower()


def _sem_projeto_lie(texto):
    t = str(texto or "").strip().lower()
    return t.startswith("ainda não") or t.startswith("ainda nao")


def checar(linha):
    """Lista de incoerências da inscrição (vazia se está tudo certo). `linha` é um dict
    ou uma linha do DataFrame com as chaves p18 (21), p19 (22) e p20_lie (23)."""
    g = linha.get
    if not _sem_projeto_lie(g("p20_lie")):
        return []
    perguntas = [n for n, k in (("21", "p18"), ("22", "p19")) if _marcou_lie(g(k))]
    if not perguntas:
        return []
    return [f"{' e '.join(perguntas)} marca(m) a LIE, mas a 23 diz “Ainda não tenho projeto na LIE”"]


def perguntas_marcadas(linha):
    """Quais perguntas (21/22) marcaram a Lei de Incentivo ao Esporte."""
    return [n for n, k in (("21", "p18"), ("22", "p19")) if _marcou_lie(linha.get(k))]
