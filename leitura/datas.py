# -*- coding: utf-8 -*-
"""
Datas em documentos: numéricas (15/05/2025), por extenso ("Aos treze dias
do mês de agosto de dois mil e vinte e cinco") e períodos de mandato
("período de 01/01/2023 a 31/12/2025", "triênio 2023/2025").

Tolerante a OCR: aceita "mile" (mil e), "é" no lugar de "e", parênteses
com o número repetido ("dois (dois) dias") e descarta datas impossíveis
(ex.: "31/17/2025") em vez de adivinhar.
"""
import datetime as dt
import re

from leitura.campos import sem_acento

MESES = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
         "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
         "dezembro": 12}

_UNID = {"um": 1, "uma": 1, "primeiro": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
         "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11,
         "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14, "quinze": 15,
         "dezesseis": 16, "dezasseis": 16, "dezessete": 17, "dezoito": 18,
         "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
         "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90,
         "cem": 100, "cento": 100, "novecentos": 900, "oitocentos": 800}

RE_NUM = re.compile(r"\b(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4}|\d{2})\b")
_MESES_RE = "|".join(MESES)


def fazer(d, m, a):
    """date ou None (valida de verdade — 31/02 não passa)."""
    try:
        a = int(a)
        if a < 100:
            a += 2000 if a < 70 else 1900
        return dt.date(a, int(m), int(d))
    except Exception:
        return None


def br(data):
    return data.strftime("%d/%m/%Y") if data else "—"


def numero_extenso(palavras):
    """Soma números por extenso: ['dois','mil','e','vinte','e','cinco'] → 2025.
    Devolve (valor, quantas palavras consumiu)."""
    total, atual, usadas = 0, 0, 0
    for i, p in enumerate(palavras):
        if p in ("e", "é"):
            usadas = i + 1
            continue
        if p in ("mil", "mile"):
            total += (atual or 1) * 1000
            atual = 0
        elif p in _UNID:
            atual += _UNID[p]
        elif p.isdigit() and len(p) <= 4 and not total and not atual:
            return int(p), i + 1
        else:
            break
        usadas = i + 1
    valor = total + atual
    return (valor if valor else None), usadas


def _extenso_em(plano, ini):
    palavras = re.findall(r"[a-z]+|\d+", plano[ini:ini + 80])
    return numero_extenso(palavras)


RE_EXTENSO = re.compile(
    r"(\d{1,2}|[a-z]+(?:\s+e\s+[a-z]+)?)\s*(?:\([^)]{0,20}\))?\s*(?:dias?\s+)?(?:do\s+mes\s+)?"
    r"de\s+(" + _MESES_RE + r")\s*(?:do\s+ano\s+)?(?:de\s+)?(\d{4}|[a-z])")


# "23 (vinte e trêsb de novembro de 2023" — parêntese aberto pelo OCR
RE_NUM_MES = re.compile(r"\b(\d{1,2})\b[^\d\n]{0,25}?\bde\s+(" + _MESES_RE + r")\s+de\s+(\d{4})\b")


def achar_datas(texto):
    """Todas as datas do texto, na ordem: [(date, posição, trecho_original)]."""
    plano = sem_acento(texto)
    achadas = []
    for m in RE_NUM_MES.finditer(plano):
        d = fazer(m.group(1), MESES[m.group(2)], m.group(3))
        if d:
            achadas.append((d, m.start(), texto[m.start():m.end()].replace("\n", " ")))
    for m in RE_NUM.finditer(texto):
        d = fazer(*m.groups())
        if d:
            achadas.append((d, m.start(), m.group(0)))
    for m in RE_EXTENSO.finditer(plano):
        dia_txt, mes, ano_ini = m.group(1), MESES[m.group(2)], m.start(3)
        if dia_txt.isdigit():
            dia = int(dia_txt)
        else:
            dia, _ = numero_extenso(dia_txt.split())
        if m.group(3).isdigit():
            ano = int(m.group(3))
        else:
            ano, _ = _extenso_em(plano, ano_ini)
        d = fazer(dia, mes, ano) if dia and ano else None
        if d:
            achadas.append((d, m.start(), texto[m.start():m.end() + 25].replace("\n", " ")))
    achadas.sort(key=lambda x: x[1])
    unicas = []
    for a in achadas:  # a mesma data achada por dois padrões na mesma posição
        if not any(abs(a[1] - u[1]) < 12 and a[0] == u[0] for u in unicas):
            unicas.append(a)
    return unicas


def primeira_data(texto):
    ds = achar_datas(texto)
    return ds[0][0] if ds else None


RE_PERIODO = re.compile(
    r"(?:periodo|mandato|gestao|vigencia)[^.;\n]{0,40}?(?:de\s+)?(\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{4})"
    r"\s*(?:a|ate|à|-|4)\s*(\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{4})")
RE_ENIO = re.compile(r"\b[a-z]*(?:bi|tri|quadri|quinqu)?[eé]nio\s+(\d{4})\s*[/\-a]\s*(\d{4})")
RE_GESTAO = re.compile(r"\b(?:gestao|mandato)\s+(\d{4})\s*[/\-]\s*(\d{4})")
RE_A_PARTIR = re.compile(r"a\s+partir\s+(?:de\s+|do\s+dia\s+)?(\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{4})")
RE_POSSE_EM = re.compile(r"posse[^.;]{0,50}?(\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{4})")


def _d(txt):
    m = RE_NUM.search(txt)
    return fazer(*m.groups()) if m else None


def periodo_mandato(texto):
    """
    Procura o período de mandato no texto. Devolve lista de candidatos:
    {"inicio", "fim", "fonte": "explicito|anos|inicio", "pos", "trecho"}.
    """
    plano = sem_acento(texto)
    saida = []
    for m in RE_PERIODO.finditer(plano):
        ini, fim = _d(m.group(1)), _d(m.group(2))
        if ini and fim and fim > ini:
            saida.append({"inicio": ini, "fim": fim, "fonte": "explicito", "pos": m.start(),
                          "trecho": texto[m.start():m.end()].replace("\n", " ")})
    for rx in (RE_ENIO, RE_GESTAO):
        for m in rx.finditer(plano):
            a1, a2 = int(m.group(1)), int(m.group(2))
            if 1950 < a1 <= a2 < 2100:
                saida.append({"inicio": dt.date(a1, 1, 1), "fim": dt.date(a2, 12, 31),
                              "fonte": "anos", "pos": m.start(),
                              "trecho": texto[m.start():m.end()].replace("\n", " ")})
    for rx in (RE_A_PARTIR, RE_POSSE_EM):
        for m in rx.finditer(plano):
            ini = _d(m.group(1))
            if ini:
                saida.append({"inicio": ini, "fim": None, "fonte": "inicio", "pos": m.start(),
                              "trecho": texto[max(0, m.start() - 40):m.end()].replace("\n", " ")})
    return saida


def somar_anos(data, anos):
    """Fim do mandato: início + N anos − 1 dia (01/01/2023 + 3 → 31/12/2025)."""
    try:
        alvo = data.replace(year=data.year + anos)
    except ValueError:  # 29/02
        alvo = data.replace(year=data.year + anos, day=28)
    return alvo - dt.timedelta(days=1)


def dias_entre(a, b):
    return (b - a).days
