# -*- coding: utf-8 -*-
"""
Conferência assistida dos documentos da Fase 2 — ponto de entrada da tela.

Recebe os PDFs que o mentor subiu (Cartão CNPJ, Estatuto(s), Ata(s)), lê
(texto digital ou OCR), consulta a situação pública do CNPJ e monta o
PARECER no formato da especificação (leitura/parecer.py). Também devolve a
pré-marcação dos 8 itens da tela — o mentor confirma; a palavra final é dele.
"""
import hashlib

from leitura import cnpj_online as _cnpj
from leitura import parecer as _parecer
from leitura import texto as _texto
from leitura.campos import so_digitos
from leitura.documento import Documento

try:
    import streamlit as st
    _cache = st.cache_data(max_entries=60, ttl=60 * 60 * 24, show_spinner=False)
except Exception:  # fora do Streamlit (testes)
    def _cache(fn):
        return fn


@_cache
def _ler(dados, _progresso=None):
    """Páginas do PDF (cache pelo conteúdo: subir de novo não relê)."""
    return _texto.extrair_paginas(dados, progresso=_progresso)


def assinatura(arquivos):
    """Identifica o conjunto de arquivos (para saber se o parecer está atualizado)."""
    h = hashlib.md5()
    for grupo, lst in sorted(arquivos.items()):
        for _nome, dados in lst:
            h.update(grupo.encode())
            h.update(hashlib.md5(dados).digest())
    return h.hexdigest()


def analisar(arquivos, cnpj_inscricao=None, nome_inscricao=None, progresso=None, data_ref=None):
    """
    arquivos: {"cartao_cnpj": [(nome, bytes)], "estatuto": [...], "ata": [...]}
    progresso(texto, fração 0..1) — opcional, para a barra da tela.
    Devolve o parecer (dict) — ver leitura/parecer.py.
    """
    todos = [(g, n, b) for g, lst in arquivos.items() for n, b in lst]
    docs = []
    for i, (grupo, nome, dados) in enumerate(todos):
        def _p(feitas, total, i=i, nome=nome):
            if progresso and total:
                progresso(f"Lendo {nome} (OCR {feitas}/{total} pág.)", (i + feitas / total) / len(todos))
        if progresso:
            progresso(f"Lendo {nome}…", i / max(len(todos), 1))
        paginas = _ler(dados, _progresso=_p)
        d = Documento(nome, paginas, grupo)
        d.origem = _texto.origem_geral(paginas)
        d.hash = hashlib.md5(dados).hexdigest()
        docs.append(d)
    if progresso:
        progresso("Consultando o CNPJ e conferindo as regras…", 0.97)
    cnpj = so_digitos(cnpj_inscricao) or None
    api = _cnpj.consultar(cnpj) if cnpj else None
    p = _parecer.montar(docs, cnpj, nome_inscricao, data_ref=data_ref, api=api)
    p["ocr_disponivel"] = _texto.ocr_disponivel()
    p["sem_texto"] = [d.arquivo for d in docs if d.sem_texto]
    return p


def criterios(parecer):
    return _parecer.sugestoes_criterios(parecer)


def resumo_para_salvar(parecer):
    """Versão compacta para guardar no processo (sem trechos/dados pessoais)."""
    return {"resultado": parecer["resultado"], "data": parecer["data_referencia"],
            "arquivos": [d["arquivo"] for d in parecer["documentos_recebidos"]],
            "faltantes": parecer["documentos_faltantes"],
            "achados": [[a["regra_id"], a["status"], a["item"]] for a in parecer["achados"]]}
