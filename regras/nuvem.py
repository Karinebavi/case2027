# -*- coding: utf-8 -*-
"""
Memória permanente na nuvem (Supabase) + trilha de auditoria.

Se os Secrets tiverem supabase_url e supabase_key, a base de inscrições e o
estado do processo são guardados no banco do Supabase (não somem quando o
app hiberna). Sem essas chaves, o sistema continua usando os arquivos locais
em dados_base/ — do jeito que já funcionava no computador.

Tabelas (criadas por supabase/criar_tabelas.sql):
  armazenamento (chave, conteudo, atualizado_em, atualizado_por)
  auditoria     (id, quando, quem, acao, detalhe)

Fala com o Supabase pela API REST (só usa 'requests', sem biblioteca extra).
A chave usada é a SECRETA (fica só no servidor, nos Secrets do Streamlit).
"""
import json

import requests
import streamlit as st

TIMEOUT = 20


class NuvemErro(Exception):
    """Falha ao falar com o banco. Nunca engolimos: perder dado é pior."""


def _config():
    try:
        url = str(st.secrets.get("supabase_url", "")).strip().rstrip("/")
        chave = str(st.secrets.get("supabase_key", "")).strip()
    except Exception:
        return None
    if url and chave:
        return url, chave
    return None


def ativo() -> bool:
    return _config() is not None


def _headers(extra=None):
    _url, chave = _config()
    h = {"apikey": chave, "Content-Type": "application/json"}
    # chaves antigas (JWT "eyJ...") também vão no Authorization;
    # as novas (sb_secret_...) só no apikey.
    if chave.startswith("eyJ"):
        h["Authorization"] = f"Bearer {chave}"
    if extra:
        h.update(extra)
    return h


def _rest(tabela):
    return f"{_config()[0]}/rest/v1/{tabela}"


def _checar(resp, oque):
    if resp.status_code >= 300:
        raise NuvemErro(f"{oque}: HTTP {resp.status_code} — {resp.text[:300]}")
    return resp


def quem() -> str:
    """E-mail de quem está usando (quando o app é privado/login Google)."""
    for nome in ("user", "experimental_user"):
        try:
            u = getattr(st, nome)
            email = u.get("email") if hasattr(u, "get") else getattr(u, "email", None)
            if email and "@" in str(email):
                return str(email)
        except Exception:
            continue
    return "equipe (senha compartilhada)"


# ---------- armazenamento chave → texto ----------

def ler(chave):
    """Devolve o texto guardado em 'chave' ou None se não existir."""
    r = requests.get(_rest("armazenamento"), headers=_headers(),
                     params={"chave": f"eq.{chave}", "select": "conteudo"}, timeout=TIMEOUT)
    linhas = _checar(r, f"ler {chave}").json()
    return linhas[0]["conteudo"] if linhas else None


def ler_prefixo(prefixo):
    """{chave: conteudo} de todas as chaves que começam com 'prefixo'."""
    saida, inicio, passo = {}, 0, 1000
    while True:
        r = requests.get(
            _rest("armazenamento"),
            headers=_headers({"Range": f"{inicio}-{inicio + passo - 1}"}),
            params={"chave": f"like.{prefixo}*", "select": "chave,conteudo", "order": "chave"},
            timeout=TIMEOUT)
        linhas = _checar(r, f"ler {prefixo}*").json()
        for ln in linhas:
            saida[ln["chave"]] = ln["conteudo"]
        if len(linhas) < passo:
            return saida
        inicio += passo


def gravar(itens):
    """Grava (insere ou substitui) {chave: conteudo}."""
    if not itens:
        return
    autor = quem()
    # atualizado_em é preenchido pelo próprio banco (gatilho no SQL)
    corpo = [{"chave": k, "conteudo": v, "atualizado_por": autor} for k, v in itens.items()]
    r = requests.post(
        _rest("armazenamento"),
        headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
        params={"on_conflict": "chave"}, data=json.dumps(corpo), timeout=TIMEOUT)
    _checar(r, "gravar")


def apagar(chave):
    r = requests.delete(_rest("armazenamento"), headers=_headers(),
                        params={"chave": f"eq.{chave}"}, timeout=TIMEOUT)
    _checar(r, f"apagar {chave}")


def apagar_prefixo(prefixo):
    r = requests.delete(_rest("armazenamento"), headers=_headers(),
                        params={"chave": f"like.{prefixo}*"}, timeout=TIMEOUT)
    _checar(r, f"apagar {prefixo}*")


# ---------- auditoria ----------

def registrar(acao, detalhe=None):
    """Anota na trilha de auditoria. Não interrompe o trabalho se falhar."""
    if not ativo():
        return
    try:
        corpo = {"quem": quem(), "acao": acao, "detalhe": detalhe or {}}
        r = requests.post(_rest("auditoria"),
                          headers=_headers({"Prefer": "return=minimal"}),
                          data=json.dumps(corpo, ensure_ascii=False, default=str),
                          timeout=TIMEOUT)
        _checar(r, "auditoria")
    except Exception as erro:  # auditoria não pode derrubar a tela
        st.toast(f"Aviso: não consegui registrar no histórico ({erro})")


def historico(limite=200):
    """Últimos registros da auditoria (mais recentes primeiro)."""
    r = requests.get(_rest("auditoria"), headers=_headers(),
                     params={"select": "quando,quem,acao,detalhe", "order": "quando.desc",
                             "limit": str(limite)}, timeout=TIMEOUT)
    return _checar(r, "histórico").json()


def parar_com_erro(erro):
    """Mostra o problema e interrompe a tela (para nunca sobrescrever dado bom)."""
    st.error(
        "Não consegui acessar o banco de dados na nuvem, então parei para não "
        "perder nada. Tente recarregar a página em 1 minuto. Se o Supabase ficou "
        "uma semana sem uso ele pausa: entre em supabase.com e clique em 'Restore'.\n\n"
        f"Detalhe técnico: {erro}")
    st.stop()
