# -*- coding: utf-8 -*-
"""
Resumo compacto (o que fica SALVO e alimenta o quadro da tela Documental) a partir
da leitura da IA + regras (leitura/regras_ia.py). Mesmo formato de leitura/resumo.py:
{resultado, cartao, estatuto, ata}, cada documento com cor, curto e linhas.

Cada linha = [cor, texto, rótulo] — o rótulo é o status nas palavras da
conferência (OK, Atenção, Confira visualmente, Pendência, Não apto) e o texto
traz o motivo + a evidência (arquivo, página, artigo). Sem nomes de pessoas.
"""
import datetime as dt

from leitura import regras_ia as R

COR = {R.OK: "verde", R.ATENCAO: "amarelo", R.CONFIRA: "amarelo", R.PENDENCIA: "vermelho",
       R.NAO_APTO: "vermelho"}
_PESO = {"cinza": 0, "verde": 1, "amarelo": 2, "vermelho": 3}


def _curto(texto, n=220):
    texto = " ".join(str(texto or "").split())
    return texto if len(texto) <= n else texto[:n].rstrip() + "…"


def _onde(ev):
    partes = []
    if ev.get("arquivo"):
        partes.append(str(ev["arquivo"]))
    if ev.get("pagina"):
        partes.append(f"p. {ev['pagina']}")
    return f" ({', '.join(partes)})" if partes else ""


def _linhas(itens):
    return [[COR[i["status"]], f"{i['item']}: {i['motivo']}{_onde(i['evidencia'])}", i["rotulo"]] for i in itens]


def _cartao_doc(itens, leitura, ref):
    linhas = _linhas(itens)
    if not linhas:
        return {"cor": "cinza", "curto": "falta", "linhas": [["cinza", "Cartão CNPJ não recebido", "Pendência"]]}
    cor = max((l[0] for l in linhas), key=_PESO.get)
    ab = R.data((leitura.get("cartao") or {}).get("data_abertura"))
    if any(i["status"] == R.NAO_APTO for i in itens):
        curto = "não apto"
    elif ab:
        anos = (ref - ab).days // 365
        curto = f"{anos} {'ano' if anos == 1 else 'anos'}" if anos else f"{max((ref - ab).days // 30, 0)} meses"
    else:
        curto = "conferir"
    c = leitura.get("cartao") or {}
    return {"cor": cor, "curto": curto, "linhas": linhas, "arquivo": c.get("arquivo"), "pagina": c.get("pagina")}


def _estatuto_doc(itens, leitura):
    e = leitura.get("estatuto")
    linhas = _linhas(itens)
    if not e:
        return {"cor": "vermelho", "curto": "falta", "linhas": linhas}
    f = e.get("finalidade") or {}
    cor = max((l[0] for l in linhas), key=_PESO.get)
    fin = next((i for i in itens if i["item"] == "Finalidade esportiva"), None)
    curto = (f.get("artigo") or "ok") if fin and fin["status"] == R.OK else (fin["rotulo"].lower() if fin else "conferir")
    saida = {"cor": cor, "curto": _curto(curto, 30), "linhas": linhas}
    if f.get("trecho"):
        saida.update(trecho=_curto(f["trecho"]), arquivo=e.get("arquivo"), pagina=f.get("pagina"))
    return saida


def _ata_doc(itens, leitura):
    linhas = _linhas(itens)
    a = R._ata_da_diretoria(leitura)
    if not a:
        return {"cor": "vermelho", "curto": "falta", "linhas": linhas}
    cor = max((l[0] for l in linhas), key=_PESO.get)
    vig = next((i for i in itens if i["item"] == "Mandato vigente"), None)
    curto = {R.OK: "vigente", R.PENDENCIA: "vencida"}.get(vig["status"], "conferir") if vig else "conferir"
    saida = {"cor": cor, "curto": curto, "linhas": linhas}
    if a.get("periodo_trecho"):
        saida.update(trecho=_curto(a["periodo_trecho"]), arquivo=a.get("arquivo"), pagina=a.get("pagina_periodo"))
    return saida


def compacto(avaliacao, leitura, info=None, ref=None):
    ref = ref or dt.date.today()
    itens = avaliacao["itens"]

    def de(*blocos, peca=None):
        return [i for i in itens if i["bloco"] in blocos and (peca is None or peca in i["item"])]

    estatuto_itens = de("finalidade") + de("cartorio", peca="estatuto")
    ata_itens = de("mandato") + de("cartorio", peca="ata")
    info = info or {}
    return {
        "resultado": avaliacao["resultado"],
        "cartao": _cartao_doc(de("documentos", "cartao"), leitura, ref),
        "estatuto": _estatuto_doc(estatuto_itens, leitura),
        "ata": _ata_doc(ata_itens, leitura),
        "leitura": "ia", "modelo": info.get("modelo"), "custo_usd": info.get("custo_usd"),
        "observacoes": [_curto(o, 200) for o in (leitura.get("observacoes") or [])[:6]],
    }


def para_salvar(avaliacao, info=None):
    """Versão para o processo (sem trechos): resultado + itens com status."""
    info = info or {}
    return {"resultado": avaliacao["resultado"], "leitura": "ia", "modelo": info.get("modelo"),
            "achados": [[i["bloco"], i["status"], i["item"]] for i in avaliacao["itens"]]}
