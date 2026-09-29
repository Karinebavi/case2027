# -*- coding: utf-8 -*-
"""
Estado do processo seletivo por organização (CNPJ).

Guarda, para cada entidade, o que acontece ao longo das fases:
  - interesse do patrocinador
  - análise documental (Fase 2): aprovada / excluída + motivo
  - entrevista (Fase 3): mentor, comparecimento, parecer, aprovada/excluída + motivo

Fica em dados_base/processo.json (fora do git — dado de trabalho interno).
Com o Supabase configurado, cada CNPJ vira uma linha "processo/<cnpj>" no
banco: assim dois mentores salvando organizações diferentes ao mesmo tempo
não sobrescrevem o trabalho um do outro.
A repescagem é automática: quem é excluída sai do grupo e a próxima do
ranking entra sozinha (ver regras/funil.py).
"""
import json
import os

from regras import nuvem

PREFIXO_NUVEM = "processo/"
PASTA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados_base")
ARQUIVO = os.path.join(PASTA, "processo.json")


def _padrao():
    return {
        "interesse": False,
        "doc_status": "pendente",      # pendente | aprovada | excluida
        "doc_motivo": "",
        "doc_obs": "",
        "doc_check": {},               # {criterio: bool} da conferência documental
        "entrevista_mentor": "",
        "entrevista_compareceu": None,  # True | False | None
        "entrevista_status": "pendente",  # pendente | aprovada | excluida
        "entrevista_motivo": "",
        "entrevista_parecer": {},
        "entrevista_relato": "",
    }


def carregar():
    if nuvem.ativo():
        try:
            linhas = nuvem.ler_prefixo(PREFIXO_NUVEM)
        except Exception as erro:
            nuvem.parar_com_erro(erro)
        return {k[len(PREFIXO_NUVEM):]: json.loads(v) for k, v in linhas.items()}
    if os.path.exists(ARQUIVO):
        try:
            with open(ARQUIVO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def serializar(reg):
    return json.dumps(reg, ensure_ascii=False, sort_keys=True)


def salvar(estado, so_estes=None):
    """Grava o estado. Na nuvem, grava só os CNPJs em 'so_estes' (os que
    mudaram); sem essa lista, grava todos."""
    if nuvem.ativo():
        digs = estado.keys() if so_estes is None else so_estes
        try:
            nuvem.gravar({PREFIXO_NUVEM + d: serializar(estado[d]) for d in digs if d in estado})
        except Exception as erro:
            nuvem.parar_com_erro(erro)
        return
    os.makedirs(PASTA, exist_ok=True)
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def registro(estado, dig):
    """Devolve (criando se preciso) o registro de um CNPJ (só dígitos)."""
    reg = estado.get(dig)
    if reg is None:
        reg = _padrao()
        estado[dig] = reg
    else:
        # completa chaves que possam faltar (evolução do formato)
        for k, v in _padrao().items():
            reg.setdefault(k, v)
    return reg


def limpar():
    if nuvem.ativo():
        try:
            nuvem.apagar_prefixo(PREFIXO_NUVEM)
        except Exception as erro:
            nuvem.parar_com_erro(erro)
        return
    if os.path.exists(ARQUIVO):
        os.remove(ARQUIVO)
