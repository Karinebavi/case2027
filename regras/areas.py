# -*- coding: utf-8 -*-
"""
Áreas de atuação da Vale (pedido da Karine, 27/11/2026): as organizações dessas
cidades ganham destaque no Ranking e na planilha, para acompanhar a classificação
delas. Não muda nota nem posição.

A lista fica no banco ("config/areas_vale" -> [{"cidade", "uf", "codigo_ibge"}]),
com os nomes oficiais do IBGE, e pode ser ampliada pela tela Inscrições.
A cidade da inscrição já vem padronizada (regras/localidade.py), então "BH",
"Sta Luzia/MG" etc. também batem.
"""
import json
import re
import time

from regras import localidade

CHAVE = "config/areas_vale"
_cache = {"em": 0.0, "lista": None}


def carregar(forcar=False):
    if not forcar and _cache["lista"] is not None and time.time() - _cache["em"] < 60:
        return _cache["lista"]
    lista = []
    try:
        from regras import nuvem
        if nuvem.ativo():
            txt = nuvem.ler(CHAVE)
            lista = json.loads(txt) if txt else []
    except Exception:
        lista = _cache["lista"] or []
    _cache.update(em=time.time(), lista=lista)
    return lista


def salvar(lista, detalhe=None):
    from regras import nuvem
    nuvem.gravar({CHAVE: json.dumps(lista, ensure_ascii=False)})
    nuvem.registrar("areas_vale", {"total": len(lista), **(detalhe or {})})
    _cache.update(em=time.time(), lista=lista)


def _conjunto(lista):
    return {(localidade.chave(x.get("cidade")), x.get("uf")) for x in lista}


def e_area(cidade, uf, lista=None):
    """A cidade (já padronizada) está nas áreas da Vale?"""
    lista = carregar() if lista is None else lista
    return bool(cidade) and (localidade.chave(cidade), uf) in _conjunto(lista)


def ler_colado(texto):
    """Linhas "Cidade/UF", "Cidade - UF" ou blocos com a UF numa linha sozinha
    ("MA (Maranhão)" e, embaixo, as cidades). Devolve (itens, não reconhecidas)."""
    itens, nao, uf = [], [], ""
    for linha in str(texto or "").splitlines():
        s = linha.split("\t")[0].strip().rstrip("*").strip()
        if not s:
            continue
        m = re.match(r"^([A-Z]{2})(\s*\(.*\))?$", s)
        if m:
            uf = m.group(1)
            continue
        r = localidade.local(s, uf)
        if r["status"] in (localidade.CONFERE, localidade.CORRIGIDA) and r["uf"]:
            itens.append({"cidade": r["cidade"], "uf": r["uf"], "codigo_ibge": r["codigo_ibge"]})
        else:
            nao.append(s)
    return itens, nao


def juntar(lista, novos):
    vistos = _conjunto(lista)
    lista = list(lista)
    for n in novos:
        k = (localidade.chave(n["cidade"]), n["uf"])
        if k not in vistos:
            vistos.add(k)
            lista.append(n)
    return lista
