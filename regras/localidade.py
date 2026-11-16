# -*- coding: utf-8 -*-
"""
Inteligência de localidade: padroniza o Estado (UF) e a Cidade que vêm em texto
livre do formulário, para que relatórios, mapa e ranking não contem a mesma cidade
duas vezes ("Belo Horizonte", "belo horizonte", "BH", "Belo Horizonte - MG", "Belo
Horisonte" -> uma só: Belo Horizonte/MG).

Fonte das cidades: lista oficial de municípios do IBGE (base/municipios.csv, 5.571
municípios, baixada da API pública servicodados.ibge.gov.br em 16/11/2026).

Como decide (do mais seguro para o menos seguro):
  1. igual à lista oficial, sem acento/maiúscula/pontuação  -> "confere"
  2. apelido conhecido (BH, POA, Sampa, Floripa...)          -> "corrigida"
  3. erro de digitação dentro do estado informado            -> "corrigida"
     (parecido >= 85% com um município daquele estado)
  4. cidade existe, mas em OUTRO estado, ou há homônimos,
     ou a semelhança é baixa                                 -> "a conferir" (com sugestão)
  5. nada parecido                                           -> "não reconhecida"
O valor ORIGINAL nunca é apagado da base: a correção vale para relatórios e telas.
"""
import csv
import difflib
import os
import re
import unicodedata
from functools import lru_cache

from regras.regiao import NOMES, REGIAO, UF_VALIDAS

_ARQ = os.path.join(os.path.dirname(os.path.dirname(__file__)), "base", "municipios.csv")

CONFERE, CORRIGIDA, A_CONFERIR, NAO_RECONHECIDA, VAZIA = (
    "confere", "corrigida", "a conferir", "não reconhecida", "vazia")

# Apelidos e abreviações comuns -> (município, UF). Só os sem ambiguidade.
APELIDOS_CIDADE = {
    "BH": ("Belo Horizonte", "MG"), "BELZONTE": ("Belo Horizonte", "MG"),
    "SAMPA": ("São Paulo", "SP"), "SP CAPITAL": ("São Paulo", "SP"), "SAO PAULO CAPITAL": ("São Paulo", "SP"),
    "RIO": ("Rio de Janeiro", "RJ"), "RJ CAPITAL": ("Rio de Janeiro", "RJ"),
    "POA": ("Porto Alegre", "RS"), "FLORIPA": ("Florianópolis", "SC"),
    "BSB": ("Brasília", "DF"), "BRASILIA DF": ("Brasília", "DF"), "PLANO PILOTO": ("Brasília", "DF"),
    "SSA": ("Salvador", "BA"), "SJC": ("São José dos Campos", "SP"),
    "SJRP": ("São José do Rio Preto", "SP"), "RIB PRETO": ("Ribeirão Preto", "SP"),
    "BV": ("Boa Vista", "RR"), "CWB": ("Curitiba", "PR"), "REC": ("Recife", "PE"),
    "FORTAL": ("Fortaleza", "CE"), "JAMPA": ("João Pessoa", "PB"), "SAMPA SP": ("São Paulo", "SP"),
}
# Regiões administrativas do DF (o formulário pede a cidade; o município é Brasília)
_RA_DF = {"TAGUATINGA", "CEILANDIA", "SAMAMBAIA", "GAMA", "SOBRADINHO", "PLANALTINA", "GUARA",
          "AGUAS CLARAS", "RECANTO DAS EMAS", "SANTA MARIA", "SAO SEBASTIAO", "PARANOA",
          "RIACHO FUNDO", "BRAZLANDIA", "ESTRUTURAL", "ITAPOA", "VICENTE PIRES", "CRUZEIRO",
          "LAGO SUL", "LAGO NORTE", "NUCLEO BANDEIRANTE", "SUDOESTE", "SOL NASCENTE"}

# Apelidos/erros comuns de Estado
APELIDOS_UF = {
    "MINAS": "MG", "GERAIS": "MG", "ESPIRITO SANTOS": "ES", "ESPIRITU SANTO": "ES",
    "MATO GROSSO SUL": "MS", "MATOGROSSO": "MT", "MATOGROSSO DO SUL": "MS",
    "RIO GRANDE SUL": "RS", "RIO GRANDE NORTE": "RN", "BRASILIA": "DF", "D F": "DF",
    "SAMPA": "SP", "SAO PAULO CAPITAL": "SP", "PARA PA": "PA",
}

# Abreviações dentro do nome da cidade
_EXPANDE = [(r"\bS\b", "SAO"), (r"\bSTA\b", "SANTA"), (r"\bSTO\b", "SANTO"), (r"\bN SRA\b", "NOSSA SENHORA"),
            (r"\bNSA SRA\b", "NOSSA SENHORA"), (r"\bSRA\b", "SENHORA"), (r"\bCEL\b", "CORONEL"),
            (r"\bGAL\b", "GENERAL"), (r"\bGOV\b", "GOVERNADOR"), (r"\bPRES\b", "PRESIDENTE"),
            (r"\bMAL\b", "MARECHAL"), (r"\bDR\b", "DOUTOR"), (r"\bPTO\b", "PORTO")]
_PREFIXOS = re.compile(r"^(MUNICIPIO|CIDADE|PREFEITURA( MUNICIPAL)?|DISTRITO)( DE| DO| DA)? ")


def chave(texto):
    """Forma de comparar: sem acento, maiúscula, sem pontuação, espaços simples."""
    s = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().upper()
    s = s.replace("'", "").replace("`", "").replace("´", "")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------------ estado (UF)

_NOMES_UF = {chave(k): v for k, v in NOMES.items()}


@lru_cache(maxsize=4096)
def uf(valor):
    """{'uf', 'status', 'original'} — reconhece sigla, nome, nome com erro e 'MG - Minas Gerais'."""
    original = str(valor or "").strip()
    k = chave(original)
    if not k or k in ("NAN", "NONE"):
        return {"uf": "", "status": VAZIA, "original": original}
    compacta = k.replace(" ", "")
    if compacta in UF_VALIDAS and len(k) <= 3:          # "SP", "S P", "s.p."
        return {"uf": compacta, "status": CONFERE, "original": original}
    if k in _NOMES_UF:
        return {"uf": _NOMES_UF[k], "status": CONFERE, "original": original}
    if k in APELIDOS_UF:
        return {"uf": APELIDOS_UF[k], "status": CORRIGIDA, "original": original}
    # "MG - Minas Gerais", "Minas Gerais (MG)", "Estado de São Paulo"
    for nome in sorted(_NOMES_UF, key=len, reverse=True):
        if re.search(rf"\b{nome}\b", k):
            return {"uf": _NOMES_UF[nome], "status": CONFERE, "original": original}
    tokens = k.split()
    siglas = {t for t in tokens if t in UF_VALIDAS}
    if len(siglas) == 1 and len(tokens) <= 4:
        return {"uf": siglas.pop(), "status": CONFERE, "original": original}
    # erro de digitação no nome ("Pernanbuco", "Paraiba do Sul" não; "Sta Catarina")
    perto = difflib.get_close_matches(k, list(_NOMES_UF) + list(APELIDOS_UF), n=1, cutoff=0.78)
    if perto:
        alvo = _NOMES_UF.get(perto[0]) or APELIDOS_UF[perto[0]]
        return {"uf": alvo, "status": CORRIGIDA, "original": original}
    return {"uf": "", "status": NAO_RECONHECIDA, "original": original}


def regiao(sigla):
    return REGIAO.get(sigla or "", "")


# ------------------------------------------------------------------ cidades

@lru_cache(maxsize=1)
def _municipios():
    """(por_chave: chave -> [(nome, uf, código)], por_uf: uf -> {chave: (nome, código)})."""
    por_chave, por_uf = {}, {}
    if not os.path.exists(_ARQ):
        return por_chave, por_uf
    with open(_ARQ, encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            k = chave(linha["municipio"])
            por_chave.setdefault(k, []).append((linha["municipio"], linha["uf"], linha["codigo_ibge"]))
            por_uf.setdefault(linha["uf"], {})[k] = (linha["municipio"], linha["codigo_ibge"])
    return por_chave, por_uf


def _expandir(k):
    for padrao, troca in _EXPANDE:
        k = re.sub(padrao, troca, k)
    return _PREFIXOS.sub("", k).strip()


def _separar_uf(k):
    """'BELO HORIZONTE MG' -> ('BELO HORIZONTE', 'MG'); 'NATAL RIO GRANDE DO NORTE' -> ('NATAL', 'RN')."""
    tokens = k.split()
    if len(tokens) > 1 and tokens[-1] in UF_VALIDAS:
        return " ".join(tokens[:-1]), tokens[-1]
    for nome in sorted(_NOMES_UF, key=len, reverse=True):
        if k.endswith(" " + nome) and len(k) > len(nome) + 2:
            return k[: -len(nome) - 1].strip(), _NOMES_UF[nome]
    return k, ""


def _resultado(nome, sigla, codigo, status, original, sugestao=""):
    return {"cidade": nome, "uf": sigla, "codigo_ibge": codigo, "status": status,
            "original": original, "sugestao": sugestao}


def _titulo(texto):
    pequenas = {"de", "da", "do", "das", "dos", "e"}
    partes = str(texto).strip().lower().split()
    return " ".join(p if (i and p in pequenas) else p.capitalize() for i, p in enumerate(partes))


@lru_cache(maxsize=8192)
def cidade(valor, uf_informada=""):
    """Padroniza a cidade. `uf_informada`: sigla já padronizada (ou "")."""
    original = str(valor or "").strip()
    por_chave, por_uf = _municipios()
    k = chave(original)
    if not k or k in ("NAN", "NONE"):
        return _resultado("", uf_informada, "", VAZIA, original)
    k, uf_no_texto = _separar_uf(k)
    sigla = uf_informada or uf_no_texto
    k = _expandir(k)

    # apelidos
    if k in APELIDOS_CIDADE:
        nome, s = APELIDOS_CIDADE[k]
        status = CORRIGIDA if not sigla or sigla == s else A_CONFERIR
        sug = "" if status == CORRIGIDA else f"{nome}/{s} (o estado informado foi {sigla})"
        return _resultado(nome, s if status == CORRIGIDA else sigla, por_uf.get(s, {}).get(chave(nome), ("", ""))[1],
                          status, original, sug)
    if k in _RA_DF and sigla in ("", "DF"):
        return _resultado("Brasília", "DF", "5300108", CORRIGIDA, original,
                          f"{_titulo(k)} é região administrativa de Brasília")

    # 1) igual à lista oficial
    if sigla and k in por_uf.get(sigla, {}):
        nome, cod = por_uf[sigla][k]
        return _resultado(nome, sigla, cod, CONFERE, original)
    candidatos = por_chave.get(k, [])
    if not sigla and len(candidatos) == 1:
        nome, s, cod = candidatos[0]
        return _resultado(nome, s, cod, CONFERE, original)

    # 2) erro de digitação dentro do estado informado
    if sigla and por_uf.get(sigla):
        perto = difflib.get_close_matches(k, list(por_uf[sigla]), n=2, cutoff=0.85)
        if perto:
            nome, cod = por_uf[sigla][perto[0]]
            # dois muito parecidos no mesmo estado: não adivinhar
            if len(perto) == 2 and difflib.SequenceMatcher(None, k, perto[1]).ratio() >= 0.95:
                return _resultado(_titulo(original), sigla, "", A_CONFERIR, original,
                                  " ou ".join(por_uf[sigla][p][0] for p in perto))
            return _resultado(nome, sigla, cod, CORRIGIDA, original)
        # nome pela metade ("Ourilandia" -> Ourilândia do Norte; "Mogi" -> várias)
        if len(k) >= 4:
            inicio = [p for p in por_uf[sigla] if p.startswith(k + " ")]
            if len(inicio) == 1:
                nome, cod = por_uf[sigla][inicio[0]]
                return _resultado(nome, sigla, cod, CORRIGIDA, original)
            if len(inicio) > 1:
                return _resultado(_titulo(original), sigla, "", A_CONFERIR, original,
                                  "pode ser " + " ou ".join(por_uf[sigla][p][0] for p in inicio[:4]))

    # 3) existe, mas em outro estado / homônimos
    if candidatos:
        lista = ", ".join(f"{n}/{s}" for n, s, _ in candidatos[:5])
        if sigla:
            return _resultado(_titulo(original), sigla, "", A_CONFERIR, original,
                              f"não existe em {sigla}; existe em {lista}")
        return _resultado(candidatos[0][0], "", "", A_CONFERIR, original,
                          f"há {len(candidatos)} municípios com esse nome: {lista}")

    # 4) parecido em qualquer estado (sem estado informado, ou nada no estado)
    perto = difflib.get_close_matches(k, list(por_chave), n=1, cutoff=0.88)
    if perto:
        cands = por_chave[perto[0]]
        lista = ", ".join(f"{n}/{s}" for n, s, _ in cands[:5])
        if not sigla and len(cands) == 1 and difflib.SequenceMatcher(None, k, perto[0]).ratio() >= 0.92:
            nome, s, cod = cands[0]
            return _resultado(nome, s, cod, CORRIGIDA, original)
        return _resultado(_titulo(original), sigla, "", A_CONFERIR, original, f"parecido com {lista}")
    return _resultado(_titulo(original), sigla, "", NAO_RECONHECIDA, original)


def local(cidade_txt, uf_txt):
    """Estado + cidade juntos, um ajudando o outro. Devolve o resultado da cidade com
    'uf', 'regiao', 'status_uf' e 'status' (o pior dos dois, para a conferência)."""
    ru = uf(uf_txt)
    rc = cidade(cidade_txt, ru["uf"])
    sigla = rc["uf"] or ru["uf"]
    status_uf = ru["status"]
    # estado em branco/ilegível, mas a cidade resolveu sozinha: o estado vem da cidade
    if not ru["uf"] and rc["uf"] and rc["status"] in (CONFERE, CORRIGIDA):
        status_uf = CORRIGIDA if ru["status"] != VAZIA else "pela cidade"
    out = dict(rc, uf=sigla, regiao=regiao(sigla), status_uf=status_uf, uf_original=ru["original"])
    return out
