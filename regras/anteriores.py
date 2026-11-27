# -*- coding: utf-8 -*-
"""
Organizações que JÁ PARTICIPARAM do CASE em anos anteriores — não podem ser
classificadas de novo (decisão da Karine em 27/11/2026): viram "Eliminada" na Etapa 1.

A lista NÃO fica no código (o repositório é público): fica no banco, na chave
"config/participantes_anteriores" -> [{"cnpj", "nome", "fontes"}], e pode ser
ampliada pela tela Inscrições (colando "Nome<TAB>CNPJ").

Reconhece por CNPJ igual (só os dígitos) ou, quando o nome é praticamente o mesmo
(para quem está na lista sem CNPJ ou com o CNPJ digitado errado).
"""
import difflib
import json
import re
import time
import unicodedata

CHAVE = "config/participantes_anteriores"
LIMIAR_NOME = 0.9
_PALAVRAS_VAZIAS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "para", "ltda", "me"}
_cache = {"em": 0.0, "lista": None}


def _dig(v):
    return re.sub(r"\D", "", str(v or ""))


def _tokens(nome):
    t = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\(.*?\)", " ", t)  # tira observações entre parênteses: "(EFVM repescagem)"
    return [w for w in re.findall(r"[a-z0-9]+", t) if w not in _PALAVRAS_VAZIAS and len(w) > 1]


def mesmo_nome(a, b):
    """0 a 1, simétrico: quanto os dois nomes são a mesma organização."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    jaccard = len(set(ta) & set(tb)) / len(set(ta) | set(tb))
    seq = difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    return round(max(jaccard, seq), 2)


def carregar(forcar=False):
    """Lista do banco (guardada 60 s na memória). Sem banco: lista vazia."""
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


def salvar(lista, quem="", detalhe=None):
    from regras import nuvem
    nuvem.gravar({CHAVE: json.dumps(lista, ensure_ascii=False)})
    nuvem.registrar("participantes_anteriores", {"total": len(lista), **(detalhe or {})})
    _cache.update(em=time.time(), lista=lista)


def ler_colado(texto, fonte="anos anteriores"):
    """Linhas "Nome<TAB>CNPJ" (ou "Nome ... 00.000.000/0000-00") -> itens da lista."""
    itens = []
    for linha in str(texto or "").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        m = re.search(r"([\d./\-\s]{11,})\s*$", linha)
        cnpj = _dig(m.group(1)) if m else ""
        nome = (linha[: m.start()] if m else linha).strip(" \t-–")
        nome = re.sub(r"^\d+\s*[ºo°]\s*", "", nome).strip()  # "5º ESPORTE CLUBE..." (posição antiga)
        if nome or cnpj:
            itens.append({"cnpj": cnpj, "nome": nome, "fontes": [fonte]})
    return itens


def juntar(lista, novos):
    """Soma sem duplicar (mesmo CNPJ ou, sem CNPJ, mesmo nome)."""
    lista = [dict(x) for x in lista]
    for n in novos:
        alvo = next((x for x in lista if (n["cnpj"] and x.get("cnpj") == n["cnpj"])
                     or (not n["cnpj"] and mesmo_nome(x.get("nome"), n["nome"]) >= LIMIAR_NOME)), None)
        if alvo:
            alvo["fontes"] = sorted(set(alvo.get("fontes") or []) | set(n.get("fontes") or []))
            alvo["nome"] = alvo.get("nome") or n["nome"]
            alvo["cnpj"] = alvo.get("cnpj") or n["cnpj"]
        else:
            lista.append(dict(n))
    return lista


def conferir(cnpj, nome, lista=None):
    """Motivo de eliminação ("Já participou do CASE — ...") ou "" se não participou."""
    lista = carregar() if lista is None else lista
    d = _dig(cnpj)
    for x in lista:
        if d and len(d) >= 14 and x.get("cnpj") == d:
            return f"Já participou do CASE ({', '.join(x.get('fontes') or ['ano anterior'])})"
    for x in lista:
        if mesmo_nome(nome, x.get("nome")) >= LIMIAR_NOME:
            return (f"Já participou do CASE ({', '.join(x.get('fontes') or ['ano anterior'])}) — "
                    "reconhecida pelo nome")
    return ""
