# -*- coding: utf-8 -*-
"""
Resumo compacto da conferência documental de UMA entidade.

É o que fica SALVO no processo e alimenta o quadro do pool (os "quadradinhos"
da tela Documental) — assim a análise não precisa ser refeita. Para cada
documento: uma cor (verde/amarelo/vermelho/cinza), um rótulo curto para o
quadro e duas linhas em linguagem simples para o cartão de detalhe.

A cor de cada linha vem SEMPRE das regras do parecer (leitura/parecer.py); aqui
só se escreve o texto. Sem dado pessoal: guarda datas, o artigo e um trecho
curto do estatuto (documento público da entidade) — nunca nomes da diretoria.
"""
import datetime as dt

from leitura import parecer as P

_PESO = {"cinza": 0, "verde": 1, "amarelo": 2, "vermelho": 3}


def _pior(*cores):
    return max(cores, key=lambda c: _PESO.get(c, 2))


def _idade(desde, ref):
    dias = (ref - desde).days
    if dias < 365:
        meses = max(dias // 30, 0)
        return f"{meses} {'mês' if meses == 1 else 'meses'}"
    anos = dias // 365
    return f"{anos} {'ano' if anos == 1 else 'anos'}"


def _curto(texto, n=110):
    texto = " ".join(str(texto or "").split())
    return texto if len(texto) <= n else texto[:n].rstrip() + "…"


def _cartao(sug, cart, ref):
    if not cart:
        return {"cor": "cinza", "curto": "falta", "linhas": [["cinza", "Cartão CNPJ não recebido"]]}
    ano = sug.get("cnpj_1ano") or {}
    c1 = ano.get("cor") or "amarelo"
    ab = cart.get("data_abertura")
    quando = f"aberto em {ab:%d/%m/%Y}" if ab else "data de abertura não lida"
    if c1 == "verde":
        l1 = ["verde", f"Mais de 1 ano: {quando}"]
    elif c1 == "vermelho":
        l1 = ["vermelho", f"Menos de 1 ano: {quando}" if ab and (ref - ab).days < 365
              else _curto(ano.get("detalhe") or "Tempo de funcionamento não atende")]
    else:
        l1 = ["amarelo", f"Tempo de funcionamento: confira ({quando})"]

    em = cart.get("data_emissao")
    if not cart.get("oficial"):
        l2 = ["amarelo", "Não parece o comprovante oficial da Receita — confira"]
    elif em:
        dias = (ref - em).days
        l2 = (["verde", f"Emitido pela Receita há {dias} dias"] if dias <= 30
              else ["amarelo", f"Emitido há {dias} dias — peça um atualizado"])
    else:
        l2 = ["verde", "Comprovante oficial da Receita"]
    curto = _idade(ab, ref) if ab else ("ok" if c1 == "verde" else "conferir")
    return {"cor": _pior(l1[0], l2[0]), "curto": curto, "linhas": [l1, l2]}


def _estatuto(sug, est, doc_est, recebidos):
    if not (doc_est and est):
        alheio = any(d.get("doc_type") == "estatuto" and d.get("status") == "outra_entidade" for d in recebidos)
        if alheio:
            return {"cor": "vermelho", "curto": "de outra entidade",
                    "linhas": [["vermelho", "O estatuto enviado é de outra entidade"]]}
        return {"cor": "cinza", "curto": "falta", "linhas": [["cinza", "Estatuto não recebido"]]}

    f = sug.get("est_finalidade") or {}
    fins = [x for x in est.get("finalidade", []) if x.get("em_fins")]
    artigo = fins[0]["artigo"] if fins else None
    incompleto = P._doc_incompleto(doc_est)
    if f.get("sugestao") is True:
        l1, curto = ["verde", f"Esporte na finalidade: {artigo}" if artigo else "Esporte na finalidade"], artigo or "ok"
    elif incompleto:
        l1, curto = ["amarelo", "Documento incompleto (foto ou poucas páginas): a finalidade não veio"], "incompleto"
    elif f.get("cor") == "vermelho":
        l1, curto = ["vermelho", "O esporte não aparece nas finalidades"], "sem esporte"
    else:
        l1, curto = ["amarelo", _curto(f.get("detalhe") or "Finalidade esportiva: confira")], "conferir"

    r = sug.get("est_cartorio") or {}
    c2 = r.get("cor") or "amarelo"
    l2 = {"verde": ["verde", "Registrado em cartório"],
          "vermelho": ["vermelho", "Sem registro em cartório"]}.get(
        c2, ["amarelo", "Registro em cartório não confirmado" + (" (documento incompleto)" if incompleto
                                                                    else " — confira")])
    saida = {"cor": _pior(l1[0], l2[0]), "curto": curto, "linhas": [l1, l2]}
    if f.get("evidencia"):
        saida.update(trecho=_curto(f["evidencia"], 220), arquivo=f.get("arquivo"), pagina=f.get("pagina"))
    return saida


def _ata(sug, ata, doc_ata, ref):
    if not (doc_ata and ata):
        return {"cor": "cinza", "curto": "falta", "linhas": [["cinza", "Ata da diretoria não recebida"]]}
    fim = max((m["fim"] for m in ata.get("mandatos", []) if m.get("fim")), default=None)
    c1 = (sug.get("ata_vigencia") or {}).get("cor") or "amarelo"
    if c1 == "verde":
        l1, curto = ["verde", f"Diretoria vigente até {fim:%m/%Y}" if fim else "Diretoria vigente"], "vigente"
    elif c1 == "vermelho":
        l1 = ["vermelho", f"Mandato vencido em {fim:%m/%Y}" if fim and fim < ref
              else "Mandato da diretoria não está vigente"]
        curto = "vencida"
    else:
        l1, curto = ["amarelo", "Vigência da diretoria: confira" + (f" (até {fim:%m/%Y})" if fim else "")], "conferir"

    c2 = (sug.get("ata_cartorio") or {}).get("cor") or "amarelo"
    l2 = {"verde": ["verde", "Registrada em cartório"],
          "vermelho": ["vermelho", "Sem registro em cartório"]}.get(c2, ["amarelo", "Registro em cartório: confira"])
    return {"cor": _pior(l1[0], l2[0]), "curto": curto, "linhas": [l1, l2]}


def compacto(parecer, ref=None):
    """{resultado, cartao, estatuto, ata} — cada documento com cor, curto e linhas."""
    ref = ref or dt.date.today()
    sug = P.sugestoes_criterios(parecer)
    pc = parecer["_pecas"]
    return {
        "resultado": parecer["resultado"],
        "cartao": _cartao(sug, pc["cartao"], ref),
        "estatuto": _estatuto(sug, pc["estatuto"], pc["doc_est"], parecer.get("documentos_recebidos", [])),
        "ata": _ata(sug, pc["ata"], pc["doc_ata"], ref),
    }


def pendencias(resumo):
    """Frases do que falta/confere, para o e-mail de pedido de documentos."""
    nomes = {"cartao": "Cartão CNPJ", "estatuto": "Estatuto social", "ata": "Ata de eleição/posse da diretoria"}
    saida = []
    for chave, rotulo in nomes.items():
        doc = resumo.get(chave) or {}
        for cor, texto in doc.get("linhas", []):
            if cor != "verde":
                saida.append(f"{rotulo}: {texto}")
    return saida
