# -*- coding: utf-8 -*-
"""
Conferência do CNPJ digitado na inscrição — e sugestão de correção.

Combinado com a Karine (06/11/2026): o sistema SUGERE, a equipe CONFIRMA com um
clique; a entidade não é procurada. Toda correção fica no histórico com o número
original.

Para cada inscrição:
  - dígito verificador: o número existe?
  - Receita (consulta pública, só o número sai daqui): o nome lá bate com o
    nome da inscrição? (pega o erro mais perigoso: CNPJ válido de OUTRA entidade)
  - campo "Confirme o CNPJ" do formulário (quando existir): os dois batem?
  - sugestões, da prova mais forte para a mais fraca:
      1. o CNPJ do cartão CNPJ que a entidade mandou (lido pela IA);
      2. o campo de confirmação, quando ele é válido;
      3. números a um dígito de distância (troca de um dígito, dois dígitos
         invertidos, dígito faltando) que existem E cujo nome na Receita bate;
      4. 28 dígitos = dois CNPJs colados: testa cada metade.
"""
import datetime as dt
import difflib
import json
import re
import unicodedata

from regras.memoria import so_digitos

CHAVE_DIAGNOSTICOS = "cnpj/diagnosticos"
LIMIAR_NOME = 0.55          # semelhança mínima para dizer "o nome bate"
MAX_CONSULTAS = 12          # consultas à Receita por inscrição (a API pública é limitada)

ST_OK = "ok"
ST_SEM_RECEITA = "sem_receita"        # número válido, mas a Receita não respondeu
ST_INVALIDO = "invalido"              # 14 dígitos com dígito verificador errado
ST_FORMATO = "formato"                # quantidade de dígitos errada
ST_OUTRA = "outra_entidade"           # número válido, mas na Receita é outra organização
ST_CONFIRMACAO = "confirmacao_diferente"
ST_MANTIDO = "mantido"                # a equipe conferiu e manteve como está
ST_CORRIGIDO = "corrigido"

ROTULO = {ST_OK: "Confere", ST_SEM_RECEITA: "Válido (Receita não respondeu)", ST_INVALIDO: "Número não existe",
          ST_FORMATO: "Quantidade de dígitos errada", ST_OUTRA: "Pode ser de outra entidade",
          ST_CONFIRMACAO: "Confirmação diferente", ST_MANTIDO: "Mantido pela equipe",
          ST_CORRIGIDO: "Corrigido"}
A_CONFERIR = {ST_INVALIDO, ST_FORMATO, ST_OUTRA, ST_CONFIRMACAO}

_PESOS1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS2 = [6] + _PESOS1


# ------------------------------------------------------------------ número

def _dv(numeros, pesos):
    s = sum(int(n) * p for n, p in zip(numeros, pesos)) % 11
    return "0" if s < 2 else str(11 - s)


def completar(base12):
    """Os 12 primeiros dígitos + os 2 verificadores."""
    d1 = _dv(base12, _PESOS1)
    return base12 + d1 + _dv(base12 + d1, _PESOS2)


def valido(cnpj):
    d = so_digitos(cnpj)
    return len(d) == 14 and len(set(d)) > 1 and completar(d[:12]) == d


def formatar(cnpj):
    d = so_digitos(cnpj)
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}" if len(d) == 14 else str(cnpj or "")


def candidatos(cnpj):
    """Números válidos 'perto' do digitado: [(cnpj, como)] — sem consultar nada."""
    d = so_digitos(cnpj)
    achados = {}

    def add(c, como):
        if valido(c) and c != d and c not in achados:
            achados[c] = como

    if len(d) == 14:
        for i in range(14):
            for x in "0123456789":
                if x != d[i]:
                    add(d[:i] + x + d[i + 1:], f"um dígito trocado (posição {i + 1})")
        for i in range(13):
            add(d[:i] + d[i + 1] + d[i] + d[i + 2:], "dois dígitos invertidos")
    elif len(d) == 13:
        for i in range(14):
            for x in "0123456789":
                add(d[:i] + x + d[i:], "um dígito faltando")
    elif len(d) == 12:
        add(completar(d), "faltavam os 2 dígitos finais")
    elif len(d) == 8:
        add(completar(d + "0001"), "só a raiz do CNPJ (matriz 0001)")
    elif len(d) >= 28:
        for k in range(0, len(d) - 13, 14):
            add(d[k:k + 14], "dois números colados (separado em partes)")
    return list(achados.items())


# ------------------------------------------------------------------ nome

_VAZIAS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "para", "ltda", "me", "the"}


def _tokens(nome):
    t = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode().lower()
    return [w for w in re.findall(r"[a-z0-9]+", t) if w not in _VAZIAS and len(w) > 1]


def semelhanca(a, b):
    """0 a 1: quanto o nome da inscrição (a) bate com o nome na Receita (b)."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    contido = len(set(ta) & set(tb)) / len(set(ta))
    seq = difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    return round(max(contido, seq), 2)


# ------------------------------------------------------------------ diagnóstico

def _consultar_padrao(cnpj):
    from leitura import cnpj_online
    return cnpj_online.consultar(cnpj)


def diagnosticar(cnpj, nome, confirmacao=None, cnpj_cartao=None, consultar=None):
    """Situação do CNPJ digitado + sugestões. Não muda nada; só olha."""
    consultar = consultar or _consultar_padrao
    d = so_digitos(cnpj)
    out = {"digitado": d, "status": ST_OK, "detalhe": "", "sugestoes": [],
           "quando": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    vistos = set()

    def sugerir(c, fonte, receita=None):
        if c in vistos or c == d:
            return
        vistos.add(c)
        r = receita if receita is not None else consultar(c)
        sim = semelhanca(nome, (r or {}).get("razao_social")) if r else None
        out["sugestoes"].append({"cnpj": c, "fonte": fonte, "razao_social": (r or {}).get("razao_social"),
                                 "municipio": "/".join(x for x in [(r or {}).get("municipio"), (r or {}).get("uf")]
                                                       if x) or None,
                                 "semelhanca": sim})

    cart = so_digitos(cnpj_cartao)
    if valido(cart) and cart != d:
        sugerir(cart, "cartão CNPJ enviado pela entidade")
    conf = so_digitos(confirmacao)

    if valido(d):
        r = consultar(d)
        if r is None:
            out.update(status=ST_SEM_RECEITA, detalhe="O número existe, mas a Receita não respondeu agora.")
        else:
            sim = semelhanca(nome, r.get("razao_social"))
            out["receita"] = {"razao_social": r.get("razao_social"), "semelhanca": sim,
                              "municipio": "/".join(x for x in [r.get("municipio"), r.get("uf")] if x) or None}
            if sim < LIMIAR_NOME:
                out.update(status=ST_OUTRA, detalhe=f"Na Receita, este CNPJ é de “{r.get('razao_social')}”.")
        if conf and conf != d:
            out.update(status=ST_CONFIRMACAO if out["status"] == ST_OK else out["status"],
                       detalhe=(out["detalhe"] + " " if out["detalhe"] else "")
                       + "O CNPJ digitado na confirmação é diferente.")
            if valido(conf):
                sugerir(conf, "campo de confirmação do formulário")
    else:
        out.update(status=ST_INVALIDO if len(d) == 14 else ST_FORMATO,
                   detalhe=("O número não existe (dígito verificador errado)." if len(d) == 14
                            else f"Tem {len(d)} dígitos; o CNPJ tem 14."))
        if valido(conf):
            sugerir(conf, "campo de confirmação do formulário")
        cands = candidatos(d)
        for c, como in cands[:MAX_CONSULTAS]:
            r = consultar(c)
            if r and semelhanca(nome, r.get("razao_social")) >= LIMIAR_NOME:
                sugerir(c, f"{como}; o nome na Receita bate", r)
        if not any(s["semelhanca"] for s in out["sugestoes"]) and len(cands) == 1:
            # Um só número válido por perto e a Receita não confirmou: sugere, avisando.
            sugerir(cands[0][0], f"{cands[0][1]} — único número válido por perto, mas NÃO achado na Receita; "
                                 "confira no cartão CNPJ", {})

    # Melhor sugestão primeiro: cartão > nome que bate mais > o resto
    out["sugestoes"].sort(key=lambda s: (s["fonte"].startswith("cartão"), s["semelhanca"] or 0), reverse=True)
    return out


# ------------------------------------------------------------------ guardar / corrigir

def _chave(linha):
    """Identifica a inscrição: o id do envio no Wix (ou o CNPJ digitado, sem id)."""
    return str(linha.get("id_envio") or "").strip() or "cnpj:" + so_digitos(linha.get("cnpj"))


def carregar_diagnosticos():
    from regras import nuvem
    if not nuvem.ativo():
        return {}
    try:
        txt = nuvem.ler(CHAVE_DIAGNOSTICOS)
        return json.loads(txt) if txt else {}
    except Exception:
        return {}


def salvar_diagnosticos(diags):
    from regras import nuvem
    if nuvem.ativo():
        nuvem.gravar({CHAVE_DIAGNOSTICOS: json.dumps(diags, ensure_ascii=False)})


def conferir_base(base, estado=None, so_novas=True, diags=None):
    """Diagnostica as inscrições da base (só as que ainda não têm diagnóstico, por
    padrão) e devolve o dicionário atualizado {chave: diagnóstico}."""
    diags = dict(diags if diags is not None else carregar_diagnosticos())
    estado = estado or {}
    for _, linha in base.iterrows():
        k = _chave(linha)
        atual = diags.get(k)
        if so_novas and atual and atual.get("digitado") == so_digitos(linha.get("cnpj")):
            continue
        if atual and atual.get("status") in (ST_MANTIDO, ST_CORRIGIDO) \
                and atual.get("digitado") == so_digitos(linha.get("cnpj")):
            continue
        dig = so_digitos(linha.get("cnpj"))
        lido = ((estado.get(dig) or {}).get("doc_leitura") or {}).get("leitura") or {}
        diags[k] = diagnosticar(linha.get("cnpj"), linha.get("nome_entidade"),
                                confirmacao=linha.get("cnpj_confirmacao"),
                                cnpj_cartao=(lido.get("cartao") or {}).get("cnpj"))
        diags[k]["nome"] = str(linha.get("nome_entidade") or "")
    return diags


def corrigir(chave, novo, quem):
    """Troca o CNPJ da inscrição na base (o original fica no histórico). Move junto
    a análise do processo, se havia alguma no número antigo. Devolve True se mudou."""
    from regras import base_dados, nuvem, processo
    novo = so_digitos(novo)
    if not valido(novo):
        raise ValueError("CNPJ inválido")
    base = base_dados.carregar()
    if chave.startswith("cnpj:"):
        alvo = base["cnpj"].map(so_digitos) == chave[5:]
    else:
        alvo = base.get("id_envio", base["cnpj"]).astype(str).str.strip() == chave
    if not alvo.any():
        return False
    antigo = so_digitos(base.loc[alvo, "cnpj"].iloc[0])
    base.loc[alvo, "cnpj"] = formatar(novo)
    base_dados.salvar(base)
    est = processo.carregar()
    if antigo in est and novo not in est:
        est[novo] = est.pop(antigo)
        processo.salvar(est, so_estes=[novo])
        if nuvem.ativo():
            nuvem.apagar(processo.PREFIXO_NUVEM + antigo)  # a análise agora mora no número certo
    diags = carregar_diagnosticos()
    d = diags.get(chave, {})
    d.update(status=ST_CORRIGIDO, digitado=novo, original=antigo, corrigido_por=quem,
             corrigido_em=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    diags[chave] = d
    salvar_diagnosticos(diags)
    nuvem.registrar("corrigir_cnpj", {"de": antigo, "para": novo, "inscricao": chave})
    return True


def manter(chave, quem):
    """A equipe conferiu e o número está certo: sai da lista."""
    from regras import nuvem
    diags = carregar_diagnosticos()
    d = diags.get(chave, {})
    d.update(status=ST_MANTIDO, mantido_por=quem)
    diags[chave] = d
    salvar_diagnosticos(diags)
    nuvem.registrar("manter_cnpj", {"inscricao": chave, "cnpj": d.get("digitado")})
