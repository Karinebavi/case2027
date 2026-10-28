# -*- coding: utf-8 -*-
"""
Sincronização das inscrições direto do Wix (Wix Forms) — opcional.

Puxa as respostas do formulário de inscrição pela API REST do Wix e devolve
um DataFrame no MESMO formato de um CSV (colunas = perguntas), que entra no
pipeline de sempre (mapeamento -> normalização -> base). Assim o botão
"Sincronizar com o Wix" faz o que o upload do CSV faz, só que automático.

IMPORTANTE — documentos: no formulário final, os documentos (cartão, estatuto,
ata) são enviados por um LINK externo, não anexados no Wix. Portanto esta
sincronização traz só os DADOS da inscrição; os documentos continuam sendo
conferidos à parte, na aba Documental.

Configuração (Secrets, seção [wix]):

    [wix]
    api_key  = "..."                     # API Keys Manager do Wix
    site_id  = "..."                     # ID do site (Settings do site)
    # opcionais:
    form_id   = "..."                    # ID do formulário de inscrição
    form_nome = "Inscrição"              # ou identifique pelo nome
    namespace = "wix.form_app.form"      # padrão (Wix Forms)

Sem a seção [wix], o botão fica desligado e nada muda.

Fontes da API (dev.wix.com):
- Autenticação por API key: Authorization + wix-site-id.
- Query submissions: POST /form-submission-service/v4/submissions/namespace/query
- Get form (para mapear target->rótulo): GET /form-schema-service/v4/forms/{id}
"""
import ipaddress
import os
import re
import socket
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests

try:
    import streamlit as st
except Exception:  # fora do Streamlit (testes)
    st = None

_BASE = "https://www.wixapis.com"
NAMESPACE_PADRAO = "wix.form_app.form"
_TIMEOUT = 60


def _cfg():
    cfg = {}
    try:
        if st is not None and "wix" in st.secrets:
            cfg = dict(st.secrets["wix"])
    except Exception:
        cfg = {}
    g = lambda k: cfg.get(k) or os.environ.get("WIX_" + k.upper()) or ""
    return {
        "api_key": g("api_key"),
        "site_id": g("site_id"),
        "form_id": g("form_id"),
        "form_nome": g("form_nome"),
        "form_docs": g("form_docs"),          # formulário de ENVIO DE DOCUMENTOS
        "form_docs_nome": g("form_docs_nome"),
        "namespace": g("namespace") or NAMESPACE_PADRAO,
    }


def ativo():
    c = _cfg()
    return bool(c["api_key"] and c["site_id"])


def _headers(c):
    return {"Authorization": c["api_key"], "wix-site-id": c["site_id"],
            "Content-Type": "application/json"}


def _erro_http(r, acao):
    # Não expõe o corpo da resposta (pode conter dados) — só o código e uma dica.
    dica = {401: "confira a API key.", 403: "a chave não tem permissão ou falta o site_id.",
            404: "recurso não encontrado.", 428: "o app Wix Forms não está instalado no site."}
    return (f"Wix: falha em {acao} (HTTP {r.status_code}). "
            + dica.get(r.status_code, "veja o guia docs/ATIVAR-WIX.md."))


def listar_formularios(c=None):
    """[(id, nome)] dos formulários do namespace — para o usuário escolher."""
    c = c or _cfg()
    r = requests.get(f"{_BASE}/form-schema-service/v4/forms",
                     params={"namespace": c["namespace"], "fieldsets": "METADATA",
                             "paging.limit": 100},
                     headers=_headers(c), timeout=_TIMEOUT)
    if not r.ok:
        raise RuntimeError(_erro_http(r, "listar formulários"))
    return [(f.get("id"), f.get("name") or "(sem nome)") for f in r.json().get("forms", [])]


def _resolver_form_id(c):
    if c["form_id"]:
        return c["form_id"]
    forms = listar_formularios(c)
    if not forms:
        raise RuntimeError("Nenhum formulário encontrado no site (confira o app Wix Forms e o namespace).")
    if c["form_nome"]:
        alvo = c["form_nome"].strip().lower()
        for fid, nome in forms:
            if alvo in (nome or "").lower():
                return fid
    if len(forms) == 1:
        return forms[0][0]
    lista = "; ".join(f"{nome} = {fid}" for fid, nome in forms)
    raise RuntimeError("Há vários formulários — defina form_id (ou form_nome) no Secrets. "
                       f"Disponíveis: {lista}")


def _achar_rotulo(campo):
    """Procura o rótulo (label) dentro do campo do schema, em qualquer nível."""
    def anda(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "label" and isinstance(v, str) and v.strip():
                    return v.strip()
                achou = anda(v)
                if achou:
                    return achou
        elif isinstance(o, list):
            for item in o:
                achou = anda(item)
                if achou:
                    return achou
        return None
    return anda(campo.get("inputOptions", {})) or None


def _mapa_target_rotulo(c, form_id):
    """{target: rótulo} lendo o schema do formulário (Get Form)."""
    r = requests.get(f"{_BASE}/form-schema-service/v4/forms/{form_id}",
                     headers=_headers(c), timeout=_TIMEOUT)
    if not r.ok:
        raise RuntimeError(_erro_http(r, "ler o formulário"))
    form = r.json().get("form", {})
    mapa = {}
    for campo in form.get("formFields", []) or form.get("fields", []):
        alvo = (campo.get("inputOptions", {}) or {}).get("target") or campo.get("target")
        if alvo:
            mapa[alvo] = _achar_rotulo(campo) or alvo
    return mapa, form.get("name") or ""


def _valor_texto(v):
    """Converte o valor de uma resposta em texto plano (para virar coluna de CSV)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Sim" if v else "Não"
    if isinstance(v, list):
        return ", ".join(_valor_texto(x) for x in v)
    if isinstance(v, dict):
        # endereço u outro objeto: junta os campos de texto úteis
        ordem = ["addressLine", "addressLine2", "streetName", "streetNumber",
                 "city", "subdivision", "postalCode", "country"]
        partes = [str(v[k]) for k in ordem if v.get(k)]
        return ", ".join(partes) if partes else ", ".join(str(x) for x in v.values() if isinstance(x, (str, int, float)))
    return str(v)


def _buscar_submissoes(c, form_id):
    """Todas as submissões do formulário (seguindo a paginação por cursor)."""
    url = f"{_BASE}/form-submission-service/v4/submissions/namespace/query"
    linhas, cursor = [], None
    while True:
        query = {"filter": {"namespace": c["namespace"], "formId": form_id},
                 "sort": [{"fieldName": "createdDate", "order": "DESC"}],
                 "cursorPaging": {"limit": 100}}
        if cursor:
            query = {"cursorPaging": {"limit": 100, "cursor": cursor}}
        r = requests.post(url, json={"query": query}, headers=_headers(c), timeout=_TIMEOUT)
        if not r.ok:
            raise RuntimeError(_erro_http(r, "consultar inscrições"))
        dados = r.json()
        linhas.extend(dados.get("submissions", []))
        meta = dados.get("metadata") or dados.get("pagingMetadata") or {}
        if meta.get("hasNext") and (meta.get("cursors") or {}).get("next"):
            cursor = meta["cursors"]["next"]
        else:
            break
    return linhas


def sincronizar(form_id=None):
    """Puxa as inscrições do Wix e devolve (DataFrame, info_str).
    DataFrame: uma linha por inscrição, colunas = rótulos das perguntas.
    form_id: se informado, puxa DESSE formulário (ex.: o de 2026 para teste);
    senão usa o configurado no Secrets."""
    if not ativo():
        raise RuntimeError("Wix desligado — configure a seção [wix] no Secrets (api_key e site_id).")
    c = _cfg()
    form_id = form_id or _resolver_form_id(c)
    mapa, nome_form = _mapa_target_rotulo(c, form_id)
    subs = _buscar_submissoes(c, form_id)
    linhas = []
    for s in subs:
        respostas = s.get("submissions", {}) or {}
        # "Data de envio": o mapeamento reconhece sozinho; a base usa para manter
        # a inscrição mais recente quando o mesmo CNPJ se inscreve de novo.
        linha = {"_submission_id": s.get("id", ""), "Data de envio": s.get("createdDate", "")}
        for alvo, valor in respostas.items():
            coluna = mapa.get(alvo, alvo)
            linha[coluna] = _valor_texto(valor)
        linhas.append(linha)
    df = pd.DataFrame(linhas).fillna("")
    info = f"{len(df)} inscrição(ões) do formulário “{nome_form or form_id}”."
    return df, info


# ----------------------------------------------------------------- documentos

# Rótulo/target do campo de upload -> grupo que a conferência espera.
_GRUPO_POR_CHAVE = [
    ("cartao_cnpj", ["cnpj", "cartao", "cartão"]),
    ("estatuto", ["estatuto"]),
    ("ata", ["ata"]),
]


def _grupo_do_campo(rotulo, target):
    base = (str(rotulo) + " " + str(target)).lower()
    for grupo, chaves in _GRUPO_POR_CHAVE:
        if any(c in base for c in chaves):
            return grupo
    return None  # ex.: "Diretrizes" -> não entra na conferência


_MAX_DOWNLOAD = 40 * 1024 * 1024          # teto por arquivo (40 MB)
_HOSTS_WIX = ("wixstatic.com", "wixmp.com", "wix.com", "wixsite.com")


def _url_segura(url):
    """Só permite baixar de https nos domínios do Wix, e nunca de IP interno
    (evita SSRF — a URL vem da submissão, controlada pelo candidato)."""
    try:
        p = urlparse(url)
    except Exception:
        return False
    host = (p.hostname or "").lower()
    if p.scheme != "https" or not host:
        return False
    # Os anexos dos formulários ficam em <id-do-site>.usrfiles.com: libera SÓ o
    # do nosso site (o de outro site continua bloqueado).
    site = (_cfg().get("site_id") or "").strip().lower()
    do_nosso_site = bool(site) and host == f"{site}.usrfiles.com"
    if not do_nosso_site and not any(host == h or host.endswith("." + h) for h in _HOSTS_WIX):
        return False
    # Defesa em profundidade: se o host (já restrito aos domínios do Wix) resolver
    # para um IP interno, bloqueia. Se o DNS falhar, confia na allowlist de domínio.
    try:
        for *_r, sa in socket.getaddrinfo(host, 443):
            ip = ipaddress.ip_address(sa[0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return False
    except Exception:
        pass
    return True


def _baixar(url):
    # Redirecionamento seguido à mão: CADA endereço da cadeia passa pela checagem
    # (senão um link aprovado poderia redirecionar para um endereço interno).
    for _salto in range(5):
        if not _url_segura(url):
            raise RuntimeError("URL de documento não permitida (fora dos domínios do Wix).")
        r = requests.get(url, timeout=60, stream=True, allow_redirects=False)
        if r.is_redirect:
            url = urljoin(url, r.headers.get("Location", ""))
            r.close()
            continue
        total, pedacos = 0, []
        with r:
            r.raise_for_status()
            for chunk in r.iter_content(65536):
                total += len(chunk)
                if total > _MAX_DOWNLOAD:
                    raise RuntimeError("Documento excede o tamanho máximo permitido (40 MB).")
                pedacos.append(chunk)
        return b"".join(pedacos)
    raise RuntimeError("Redirecionamentos demais ao baixar o documento.")


def _resolver_form_docs(c):
    if c["form_docs"]:
        return c["form_docs"]
    forms = listar_formularios(c)
    alvo = (c["form_docs_nome"] or "documento").strip().lower()
    cand = [(fid, nome) for fid, nome in forms if alvo in (nome or "").lower()]
    if len(cand) == 1:
        return cand[0][0]
    if not cand:
        raise RuntimeError("Não achei o formulário de documentos — defina form_docs no Secrets.")
    lista = "; ".join(f"{nome} = {fid}" for fid, nome in cand)
    raise RuntimeError(f"Há vários formulários de documentos — defina form_docs. Candidatos: {lista}")


def _norm(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()


def _papel_do_campo(rotulo):
    """Que dado de identificação um campo de TEXTO do formulário de documentos
    traz: 'cnpj' | 'email' | 'entidade' | None. Cuidado com rótulos como
    "Nome completo do responsável" ou "seu cargo na entidade" — não são o nome
    da entidade."""
    r = _norm(rotulo)
    if "cnpj" in r and "cartao" not in r:
        return "cnpj"
    if "mail" in r:
        return "email"
    if "nome" in r and "entidade" in r and "responsavel" not in r and "presidente" not in r:
        return "entidade"
    return None


def buscar_documentos(form_docs_id=None, limite=None, baixar=True):
    """Puxa os envios do formulário de documentos do Wix (do mais novo ao mais
    antigo). Cada envio: {entidade, cnpj, emails, arquivos:{cartao_cnpj, estatuto,
    ata}, _id, _data}. Com baixar=False, arquivos = [(nome, url)] sem baixar."""
    if not ativo():
        raise RuntimeError("Wix desligado — configure a seção [wix] no Secrets.")
    c = _cfg()
    form_id = form_docs_id or _resolver_form_docs(c)
    mapa_rot, nome_form = _mapa_target_rotulo(c, form_id)
    subs = _buscar_submissoes(c, form_id)
    if limite:
        subs = subs[:limite]
    saida = []
    for s in subs:
        resp = s.get("submissions", {}) or {}
        ident = {"entidade": "", "cnpj": "", "emails": []}
        arquivos = {"cartao_cnpj": [], "estatuto": [], "ata": []}
        for alvo, valor in resp.items():
            rot = mapa_rot.get(alvo, alvo)
            eh_arquivo = (isinstance(valor, list) and valor and isinstance(valor[0], dict)
                          and valor[0].get("url"))
            if eh_arquivo:
                grupo = _grupo_do_campo(rot, alvo)
                if not grupo:
                    continue
                for f in valor:
                    url = f.get("url")
                    if not url:
                        continue
                    nome = f.get("displayName") or f"{alvo}.pdf"
                    if baixar:
                        try:
                            arquivos[grupo].append((nome, _baixar(url)))
                        except Exception:
                            pass
                    else:
                        arquivos[grupo].append((nome, url))
                continue
            papel = _papel_do_campo(rot)
            texto = _valor_texto(valor).strip()
            if papel == "cnpj":
                ident["cnpj"] = re.sub(r"\D", "", texto)
            elif papel == "email" and "@" in texto:
                ident["emails"].append(texto.lower())
            elif papel == "entidade" and texto:
                ident["entidade"] = texto
        saida.append({**ident, "arquivos": arquivos, "_id": s.get("id"), "_data": s.get("createdDate", "")})
    return saida, nome_form


# Atalho "um nome contém o outro" só para nome completo: "Associação" sozinho
# casaria com metade do pool (ressalva da revisão automática).
_NOME_MIN_PALAVRAS, _NOME_MIN_LETRAS = 3, 12


def _parecido(a, b):
    """Semelhança (0 a 1) entre dois nomes já normalizados por _norm."""
    import difflib
    if not (a and b):
        return 0.0
    r = difflib.SequenceMatcher(None, a, b).ratio()
    menor = min(a, b, key=len)
    if (a in b or b in a) and len(menor.split()) >= _NOME_MIN_PALAVRAS and len(menor) >= _NOME_MIN_LETRAS:
        r = max(r, 0.9)
    return r


# Por nome, só nome praticamente igual: "Associação Esportiva X" e "Associação
# Esportiva Y" passam de 0,6 de semelhança e ligavam documentos à entidade errada.
NOME_MINIMO = 0.85


def localizar(envios, cnpj=None, emails=(), nome=None, minimo=NOME_MINIMO):
    """Acha o envio de documentos de UMA entidade. Devolve (envio, como), com
    como = 'CNPJ' | 'e-mail' | 'nome', ou (None, None).
    Ordem: CNPJ exato → e-mail do responsável → nome completo parecido
    (minimo=None desliga a busca por nome).
    Os envios vêm do mais novo ao mais antigo: o primeiro que casa é o mais novo."""
    cnpj = re.sub(r"\D", "", str(cnpj or ""))
    if len(cnpj) == 14:
        for e in envios:
            if e.get("cnpj") == cnpj:
                return e, "CNPJ"
    alvo = _norm(nome or "")
    contatos = {str(x).strip().lower() for x in emails if x and "@" in str(x)}
    if contatos:
        for e in envios:
            # Um mesmo consultor pode preencher por várias entidades: o e-mail só
            # vale se o nome no envio não for claramente de outra entidade.
            nome_envio = _norm(e.get("entidade", ""))
            if contatos & set(e.get("emails", [])) and (not alvo or not nome_envio
                                                        or _parecido(alvo, nome_envio) >= 0.4):
                return e, "e-mail"
    if minimo is None:
        return None, None
    melhor, score = _mais_parecido(envios, alvo)
    if melhor and score >= minimo:
        return melhor, "nome"
    return None, None


def _mais_parecido(envios, alvo):
    melhor, score = None, 0.0
    for e in envios:
        r = _parecido(alvo, _norm(e.get("entidade", "")))
        if r > score:
            melhor, score = e, r
    return melhor, score


def ligar(envios, entidades, minimo=NOME_MINIMO):
    """Liga várias entidades aos seus envios de documentos de uma vez.
    entidades: [{chave, cnpj, emails, nome}]. Devolve {chave: (envio, como)}.
    CNPJ e e-mail valem direto. Por nome, cada envio fica com UMA entidade só —
    a de nome mais parecido — para o mesmo documento não aparecer em duas."""
    ligados, por_nome = {}, {}
    for ent in entidades:
        envio, como = localizar(envios, cnpj=ent.get("cnpj"), emails=ent.get("emails", ()),
                                nome=ent.get("nome"), minimo=None)
        if envio:
            ligados[ent["chave"]] = (envio, como)
            continue
        envio, score = _mais_parecido(envios, _norm(ent.get("nome", "")))
        if envio is not None and score >= minimo:
            atual = por_nome.get(id(envio))
            if atual is None or score > atual[1]:
                por_nome[id(envio)] = (ent["chave"], score, envio)
    usados = {id(e) for e, _ in ligados.values()}
    for chave, _score, envio in por_nome.values():
        if id(envio) not in usados:
            ligados[chave] = (envio, "nome")
    return ligados


def grupos_enviados(envio):
    """Quais documentos vieram no envio: subconjunto de cartao_cnpj/estatuto/ata."""
    return sorted(g for g, lst in (envio or {}).get("arquivos", {}).items() if lst)


def baixar_envio(envio):
    """Baixa os arquivos de um envio (só de domínios do Wix, até 40 MB cada).
    Devolve {cartao_cnpj:[(nome,bytes)], estatuto:[...], ata:[...]}."""
    arq = {"cartao_cnpj": [], "estatuto": [], "ata": []}
    for g, lst in (envio or {}).get("arquivos", {}).items():
        for nomearq, url in lst:
            try:
                arq[g].append((nomearq, _baixar(url)))
            except Exception as erro:
                print(f"[wix] não baixei um arquivo de {g}: {erro}")
    return arq
