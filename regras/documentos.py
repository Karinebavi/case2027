# -*- coding: utf-8 -*-
"""
Leitura e conferência dos documentos da Fase 2 — sem tela aqui.

Extrai o texto de PDFs digitais e faz conferências por palavra-chave.
Se o PDF for escaneado (sem texto), devolve '' para a tela avisar que
precisa de conferência manual. Nada é enviado para fora: tudo é lido no
próprio app.
"""
import unicodedata

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

TERMOS_ESPORTE = [
    "esporte", "esportiv", "pratica esportiva", "praticas esportivas",
    "modalidade esportiva", "atividade fisica", "atividades fisicas", "desporto",
]
TERMOS_REGISTRO = ["cartorio", "tabelionato", "registro civil", "registrado", "registro"]


def _sem_acento(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    )


def extrair_texto(arquivo):
    """Extrai o texto de um PDF. Devolve '' se não conseguir (provável escaneado)."""
    if PdfReader is None or arquivo is None:
        return ""
    try:
        arquivo.seek(0)
        leitor = PdfReader(arquivo)
        partes = [(pagina.extract_text() or "") for pagina in leitor.pages]
        return "\n".join(partes).strip()
    except Exception:
        return ""


def _achar(texto, termos):
    """Procura os termos no texto. Devolve (achou, trecho ao redor)."""
    plano = _sem_acento(texto).lower()
    for termo in termos:
        i = plano.find(termo)
        if i >= 0:
            ini = max(0, i - 60)
            fim = min(len(texto), i + 90)
            trecho = texto[ini:fim].strip().replace("\n", " ")
            return True, trecho
    return False, ""


def conferir_finalidade_esportiva(texto_estatuto):
    return _achar(texto_estatuto, TERMOS_ESPORTE)


def conferir_registro(texto):
    return _achar(texto, TERMOS_REGISTRO)
