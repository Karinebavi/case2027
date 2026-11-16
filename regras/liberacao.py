# -*- coding: utf-8 -*-
"""
Trava da leitura dos documentos (combinado com a Karine em 16/11/2026).

A leitura dos documentos — pela IA (paga) ou pela leitura antiga — fica BLOQUEADA
até a Karine liberar, depois do fim das inscrições. Enquanto isso, o sistema só
acompanha quem enviou documentos. A liberação (e um novo bloqueio) fica guardada
na nuvem e no histórico, com quem fez e quando.
"""
import datetime as dt
import json

from regras import nuvem

CHAVE = "config/leitura_documentos"


def estado():
    """{liberada: bool, por: str, quando: iso} — bloqueada se nunca foi liberada."""
    if not nuvem.ativo():
        return {"liberada": False}
    try:
        txt = nuvem.ler(CHAVE)
        return json.loads(txt) if txt else {"liberada": False}
    except Exception:
        return {"liberada": False}  # na dúvida, bloqueada


def liberada():
    return bool(estado().get("liberada"))


def definir(liberar, quem):
    dados = {"liberada": bool(liberar), "por": quem,
             "quando": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    nuvem.gravar({CHAVE: json.dumps(dados, ensure_ascii=False)})
    nuvem.registrar("liberar_leitura" if liberar else "bloquear_leitura", {"liberada": bool(liberar)})
    return dados
