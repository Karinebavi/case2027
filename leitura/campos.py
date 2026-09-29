# -*- coding: utf-8 -*-
"""
Achados no texto: CNPJ, datas, tipo de documento e termos por rótulo.

Filosofia (do relatório): buscar por rótulo/evidência, não confiar em regex
solta; ter achado não é garantia — por isso cada retorno traz um trecho do
próprio documento para o mentor conferir.
"""
import re
import unicodedata

try:
    from validate_docbr import CNPJ as _CNPJ
    _valida_cnpj = _CNPJ().validate
except Exception:
    def _valida_cnpj(_num):  # sem a lib, não valida dígito — trata como incerto
        return None

RE_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
RE_DATA = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")


def sem_acento(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", str(texto or ""))
        if unicodedata.category(c) != "Mn"
    ).lower()


def so_digitos(v):
    return re.sub(r"\D", "", str(v or ""))


def achar_cnpj(texto):
    """
    Primeiro CNPJ válido do texto. Devolve (14 dígitos ou None, lista de todos
    os candidatos encontrados).
    """
    candidatos = []
    for m in RE_CNPJ.finditer(texto or ""):
        num = so_digitos(m.group())
        if len(num) == 14:
            candidatos.append(num)
    for num in candidatos:
        if _valida_cnpj(num) is not False:  # True ou None (lib ausente) serve
            return num, candidatos
    return (candidatos[0] if candidatos else None), candidatos


def trecho(texto, pos, antes=60, depois=90):
    ini = max(0, pos - antes)
    fim = min(len(texto), pos + depois)
    return texto[ini:fim].strip().replace("\n", " ")


def achar_termo(texto, termos):
    """Procura qualquer termo (sem acento). Devolve (achou, trecho de evidência)."""
    plano = sem_acento(texto)
    for termo in termos:
        alvo = sem_acento(termo)
        i = plano.find(alvo)
        if i >= 0:
            return True, trecho(texto, i)
    return False, ""


def datas(texto):
    """Todas as datas dd/mm/aaaa encontradas, na ordem."""
    return ["/".join(g) for g in RE_DATA.findall(texto or "")]


def data_apos_rotulo(texto, rotulos):
    """
    Data logo após um rótulo (ex.: 'Válida até', 'Data de abertura').
    Devolve (data ou None, cor). Verde se veio de rótulo; amarelo se só achou
    datas soltas; vermelho se nenhuma.
    """
    for r in rotulos:
        m = re.search(re.escape(r) + r".{0,40}?(\d{2}/\d{2}/\d{4})", texto or "",
                      re.I | re.S)
        if m:
            return m.group(1), "verde"
    ds = datas(texto)
    if ds:
        return ds[-1], "amarelo"
    return None, "vermelho"


# ---- classificação do tipo de documento por palavras-chave ----

_TIPOS = {
    "cartao_cnpj": (
        ["comprovante de inscricao e de situacao cadastral"],
        ["natureza juridica", "situacao cadastral", "receita federal"],
    ),
    "estatuto": (
        ["estatuto social", "estatuto"],
        ["capitulo i", "dos associados", "art. 1", "assembleia geral", "finalidade"],
    ),
    "ata": (
        ["ata da assembleia", "ata de assembleia", "eleicao da diretoria"],
        ["aos", "dias do mes", "presentes", "mandato", "posse"],
    ),
}


def classificar_tipo(texto):
    """Devolve (tipo, confianca 'verde'/'amarelo'/'vermelho'). Soma de pesos."""
    plano = sem_acento(texto)
    pont = {}
    for tipo, (fortes, apoio) in _TIPOS.items():
        s = sum(3 for t in fortes if sem_acento(t) in plano)
        s += sum(1 for t in apoio if sem_acento(t) in plano)
        pont[tipo] = s
    if not any(pont.values()):
        return None, "vermelho"
    ordenado = sorted(pont.items(), key=lambda kv: kv[1], reverse=True)
    (tipo, top), (_, segundo) = ordenado[0], ordenado[1]
    if top >= 3 and top >= 2 * max(segundo, 1):
        return tipo, "verde"
    return tipo, "amarelo"
