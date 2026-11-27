# -*- coding: utf-8 -*-
"""
Avisos mandados às entidades (fora o do CNPJ, que fica junto do diagnóstico em
regras/cnpj.py). Um dicionário por tipo no banco: chave "avisos/<tipo>" ->
{inscrição: {avisada_em, avisada_por, espera}}. Sem banco, nada é guardado.
"""
import json

from regras import nuvem


def _chave(tipo):
    return f"avisos/{tipo}"


def carregar(tipo):
    if not nuvem.ativo():
        return {}
    try:
        txt = nuvem.ler(_chave(tipo))
        return json.loads(txt) if txt else {}
    except Exception:
        return {}


def marcar(tipo, inscricao, dados):
    """Anota o aviso de uma inscrição (e registra no histórico)."""
    todos = carregar(tipo)
    todos[inscricao] = dados
    if nuvem.ativo():
        nuvem.gravar({_chave(tipo): json.dumps(todos, ensure_ascii=False)})
        nuvem.registrar(f"avisar_{tipo}", {"inscricao": inscricao, "espera": dados.get("espera")})
    return todos
