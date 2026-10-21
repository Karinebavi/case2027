# -*- coding: utf-8 -*-
"""
Leitura dos documentos por IA — APOIO opcional à conferência documental.

A IA lê o texto JÁ EXTRAÍDO pelo OCR e devolve uma leitura estruturada
(finalidade esportiva + artigo + trecho, mandato, registro em cartório,
resumo e pontos de atenção). As regras determinísticas continuam valendo —
a IA é um apoio; o mentor confirma. Nada trava o app: sem configuração ou
em caso de erro, devolve None.

Provedor configurável no Secrets (seção [ia]) — escolha UM:

    [ia]
    provedor = "claude"                 # "claude" (nuvem) | "ollama" (local) | "off"
    modelo   = "claude-haiku-5-5"        # claude: barato e bom; ~centavos por ciclo
    anthropic_api_key = "sk-ant-..."     # só para o provedor claude

    # Para rodar LOCAL e de graça (nada sai do computador):
    # provedor = "ollama"
    # modelo   = "qwen2.5:7b"            # precisa do Ollama instalado e rodando

LGPD: o provedor "ollama" roda na sua máquina (nada sai). O "claude" usa a
API da Anthropic (não treina com dados da API; dá para ativar zero-retenção).
"""
import json
import os
import re

try:
    import streamlit as st
except Exception:  # fora do Streamlit (testes)
    st = None

from leitura import texto as _texto

MODELO_CLAUDE_PADRAO = "claude-haiku-5-5"
MODELO_OLLAMA_PADRAO = "qwen2.5:7b"
MAX_CHARS_DOC = 24000  # corta documentos muito longos (latência/custo)

_ROTULO = {"cartao_cnpj": "CARTÃO CNPJ", "estatuto": "ESTATUTO", "ata": "ATA"}

_SISTEMA = (
    "Você é um analista do Instituto Imaginação conferindo os documentos de uma "
    "organização esportiva (OSC) inscrita no programa CASE 2027. Você recebe o "
    "texto dos documentos já extraído por OCR (pode ter erros de digitalização). "
    "Responda SEMPRE em português e SOMENTE com um objeto JSON válido, sem texto "
    "fora do JSON e sem blocos de código."
)

_FORMATO = """Responda com este JSON (use null quando não encontrar; cite o artigo e um trecho curto e LITERAL do documento ao afirmar algo):
{
  "finalidade_esportiva": {"tem": true|false|null, "artigo": "Art. N", "trecho": "trecho curto", "observacao": "..."},
  "mandato": {"vigente": true|false|null, "inicio": "dd/mm/aaaa", "fim": "dd/mm/aaaa", "trecho": "trecho curto", "observacao": "..."},
  "registro_cartorio": {"estatuto": true|false|null, "ata": true|false|null, "observacao": "..."},
  "resumo": "2 a 3 frases sobre a aptidão documental da entidade",
  "pontos_atencao": ["ponto 1", "ponto 2"]
}
Regras: baseie-se SÓ nos textos fornecidos; não invente. 'finalidade_esportiva.tem' é true apenas se o ESPORTE aparecer entre as finalidades/objetivos do estatuto (não basta citar esporte de passagem)."""


def _cfg():
    cfg = {}
    try:
        if st is not None and "ia" in st.secrets:
            cfg = dict(st.secrets["ia"])
    except Exception:
        cfg = {}
    prov = str(cfg.get("provedor") or os.environ.get("IA_PROVEDOR") or "off").strip().lower()
    modelo = cfg.get("modelo") or os.environ.get("IA_MODELO") or (
        MODELO_CLAUDE_PADRAO if prov == "claude" else MODELO_OLLAMA_PADRAO)
    return {
        "provedor": prov,
        "modelo": modelo,
        "anthropic_api_key": cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or "",
        "ollama_url": str(cfg.get("ollama_url") or os.environ.get("OLLAMA_URL") or "http://localhost:11434").rstrip("/"),
    }


def provedor_ativo():
    """Nome do provedor pronto para uso ('claude'/'ollama') ou '' se desligado."""
    c = _cfg()
    if c["provedor"] == "claude" and c["anthropic_api_key"]:
        return "claude"
    if c["provedor"] == "ollama":
        return "ollama"
    return ""


def disponivel():
    return provedor_ativo() != ""


def _texto_dos_arquivos(arquivos):
    """Extrai (com cache) o texto de cada documento e monta um bloco rotulado."""
    partes = []
    for grupo in ("cartao_cnpj", "estatuto", "ata"):
        for nome, dados in arquivos.get(grupo, []) or []:
            pags = _texto.extrair_paginas(dados)
            txt = "\n".join((p.get("texto") or "") for p in pags).strip()
            if not txt:
                continue
            if len(txt) > MAX_CHARS_DOC:
                txt = txt[:MAX_CHARS_DOC] + "\n[...documento cortado...]"
            partes.append(f"===== {_ROTULO.get(grupo, grupo.upper())} ({nome}) =====\n{txt}")
    return "\n\n".join(partes)


def _extrair_json(s):
    """Pega o primeiro objeto JSON do texto (tolera cercas de código e sobras)."""
    if not s:
        return None
    s = s.strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.MULTILINE).strip()
    ini = s.find("{")
    fim = s.rfind("}")
    if ini == -1 or fim == -1 or fim <= ini:
        return None
    try:
        return json.loads(s[ini:fim + 1])
    except Exception:
        return None


def _chamar_claude(cfg, prompt):
    try:
        from anthropic import Anthropic
    except Exception:
        return None, ("O pacote 'anthropic' não está instalado. Rode: pip install anthropic "
                      "(e adicione 'anthropic' ao requirements.txt).")
    try:
        cliente = Anthropic(api_key=cfg["anthropic_api_key"])
        # max_tokens folgado: nos modelos atuais o "pensar" (adaptive) consome parte
        # do orçamento; 1500 cortava o JSON. 4000 dá espaço para o raciocínio + o JSON.
        msg = cliente.messages.create(
            model=cfg["modelo"], max_tokens=4000, system=_SISTEMA,
            messages=[{"role": "user", "content": prompt}],
        )
        txt = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")
        return txt, None
    except Exception as e:
        return None, f"Falha ao chamar a IA (Claude): {type(e).__name__}: {e}"


def _chamar_ollama(cfg, prompt):
    import requests
    try:
        r = requests.post(
            f"{cfg['ollama_url']}/api/chat",
            json={"model": cfg["modelo"], "stream": False, "format": "json",
                  "options": {"temperature": 0},
                  "messages": [{"role": "system", "content": _SISTEMA},
                               {"role": "user", "content": prompt}]},
            timeout=600,
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", ""), None
    except Exception as e:
        return None, (f"Falha ao chamar a IA local (Ollama): {type(e).__name__}: {e}. "
                      "Confira se o Ollama está instalado e rodando, e se o modelo foi baixado.")


def analisar(arquivos, nome_entidade=None):
    """Lê os documentos por IA. Devolve (resultado_dict, erro_str).
    resultado None quando a IA não está configurada ou falhou."""
    prov = provedor_ativo()
    if not prov:
        return None, "IA desligada (configure a seção [ia] no Secrets)."
    corpo = _texto_dos_arquivos(arquivos)
    if not corpo.strip():
        return None, "Nenhum texto legível nos documentos para a IA analisar."
    cfg = _cfg()
    prompt = (f"Entidade: {nome_entidade or '(não informado)'}\n\n{_FORMATO}\n\n"
              f"TEXTO DOS DOCUMENTOS:\n{corpo}")
    bruto, erro = (_chamar_claude(cfg, prompt) if prov == "claude" else _chamar_ollama(cfg, prompt))
    if erro:
        return None, erro
    dados = _extrair_json(bruto)
    if dados is None:
        return None, "A IA respondeu num formato inesperado (não consegui ler o JSON)."
    dados["_provedor"] = prov
    dados["_modelo"] = cfg["modelo"]
    return dados, None
