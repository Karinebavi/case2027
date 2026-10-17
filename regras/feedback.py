# -*- coding: utf-8 -*-
"""
Feedback da equipe — os mentores apontam, usando o sistema, o que confundiu ou
pode melhorar. Fica guardado junto com o resto: na nuvem (Supabase) quando
configurada, ou nesta máquina. Depois a coordenação vê tudo no Dashboard.
"""
import json
import os
from datetime import datetime

from regras import nuvem

PASTA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados_base")
ARQUIVO = os.path.join(PASTA, "feedback.jsonl")


def registrar(texto, tela=""):
    texto = (texto or "").strip()
    if not texto:
        return False
    if nuvem.ativo():
        try:
            nuvem.registrar("feedback", {"tela": tela, "texto": texto})
            return True
        except Exception:
            pass  # cai para o arquivo local
    item = {"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "tela": tela, "texto": texto}
    os.makedirs(PASTA, exist_ok=True)
    with open(ARQUIVO, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return True


def listar(limite=100):
    if nuvem.ativo():
        try:
            itens = []
            for h in nuvem.historico(limite * 3):
                if h.get("acao") == "feedback":
                    d = h.get("detalhe") or {}
                    itens.append({
                        "data": str(h.get("quando", ""))[:16].replace("T", " "),
                        "autor": h.get("quem", ""),
                        "tela": d.get("tela", ""),
                        "texto": d.get("texto", ""),
                    })
            return itens[:limite]
        except Exception:
            pass
    itens = []
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, encoding="utf-8") as f:
            for linha in f:
                try:
                    itens.append(json.loads(linha))
                except Exception:
                    pass
    return list(reversed(itens))[:limite]
