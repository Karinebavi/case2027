# -*- coding: utf-8 -*-
"""
Regras da conferência documental aplicadas à leitura da IA (leitura/leitor_ia.py).

A IA só LÊ; aqui o sistema DECIDE, sempre do mesmo jeito. Cada item sai com:
status (OK / Atenção / Confira visualmente / Pendência / Não apto), o motivo em
uma linha e a evidência (arquivo, página, artigo, trecho).

Regras combinadas com a Karine (06/11/2026):
- Cartão: situação diferente de ATIVA, natureza de empresa (2xx, Ltda, MEI,
  empresário) ou abertura depois de 01/03/2026 = NÃO APTO. Emissão em data
  diferente da inscrição = Atenção. O resto é atenção, nunca exclusão.
- Finalidade: esporte no artigo de finalidades (inclui "Das Atividades") = OK;
  em outro lugar (meios, prerrogativas, caráter) = Atenção; nenhum = Pendência.
  Falha na numeração dos artigos = Atenção.
- Mandato: qualquer ata que eleja/empossa (inclusive a de fundação) serve se o
  mandato estiver vigente na data da INSCRIÇÃO. Ordem: período escrito na ata;
  senão data da assembleia + duração (ata ou estatuto). Vencido = Pendência
  (Atenção se houver prorrogação prevista). Ata x estatuto divergentes = Atenção.
- Cartório: só vale registro/averbação em Registro Civil de Pessoas Jurídicas.
  "Só protocolado" ou sem registro = Pendência. Carimbo que existe mas não dá
  para ler = Confira visualmente (nunca Pendência). Cidade do cartório diferente
  da sede = Atenção.
"""
import datetime as dt
import re
import unicodedata

OK, ATENCAO, CONFIRA, PENDENCIA, NAO_APTO = "OK", "ATENCAO", "CONFIRA", "PENDENCIA", "NAO_APTO"
ROTULO = {OK: "OK", ATENCAO: "Atenção", CONFIRA: "Confira visualmente",
          PENDENCIA: "Pendência", NAO_APTO: "Não apto"}
_PESO = {OK: 0, ATENCAO: 1, CONFIRA: 2, PENDENCIA: 3, NAO_APTO: 4}
CORTE_ABERTURA = dt.date(2026, 3, 1)
BLOCOS = ("documentos", "cartao", "finalidade", "mandato", "cartorio")


# ------------------------------------------------------------------ apoio

def _sem_acento(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()


def _digitos(t):
    return re.sub(r"\D", "", str(t or ""))


def data(txt, fim_do_mes=False):
    """'dd/mm/aaaa' ou 'mm/aaaa' -> date. mm/aaaa vira dia 1 (ou o último dia)."""
    s = str(txt or "")
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try:
            return dt.date(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            return None
    m = re.search(r"(?<!\d)(\d{1,2})/(\d{4})", s)
    if m:
        a, mes = int(m[2]), int(m[1])
        if not 1 <= mes <= 12:
            return None
        if not fim_do_mes:
            return dt.date(a, mes, 1)
        prox = dt.date(a + (mes == 12), mes % 12 + 1, 1)
        return prox - dt.timedelta(days=1)
    return None


def _somar_anos(d, anos):
    meses = int(round(float(anos) * 12))
    a, m = divmod(d.month - 1 + meses, 12)
    ano, mes = d.year + a, m + 1
    try:
        alvo = dt.date(ano, mes, d.day)
    except ValueError:
        alvo = dt.date(ano, mes, 28)
    return alvo - dt.timedelta(days=1)


def _br(d):
    return d.strftime("%d/%m/%Y") if d else "?"


def _ev(arquivo=None, pagina=None, artigo=None, trecho=None):
    return {"arquivo": arquivo, "pagina": pagina, "artigo": artigo, "trecho": trecho}


def _item(bloco, item, status, motivo, ev=None):
    return {"bloco": bloco, "item": item, "status": status, "rotulo": ROTULO[status],
            "motivo": motivo, "evidencia": ev or _ev()}


def _cidade(t):
    """Só o nome da cidade, sem UF/acento ('Serra/ES' -> 'serra')."""
    s = _sem_acento(t)
    s = re.split(r"[/\-,(]| - ", s)[0]
    return s.strip()


# ------------------------------------------------------------------ blocos

def _documentos(L, insc):
    itens = []
    ent = L.get("entidade") or {}
    cart = L.get("cartao") or {}
    cnpj_doc = _digitos(cart.get("cnpj") or ent.get("cnpj"))
    cnpj_insc = _digitos(insc.get("cnpj"))
    if cnpj_doc and len(cnpj_insc) == 14 and cnpj_doc != cnpj_insc:
        itens.append(_item("documentos", "Entidade dos documentos", PENDENCIA,
                           "Os documentos são de outro CNPJ — não são da entidade inscrita.",
                           _ev(cart.get("arquivo"), cart.get("pagina"), trecho=cart.get("nome_empresarial"))))
    elif ent.get("todos_os_documentos_sao_da_mesma_entidade") is False:
        itens.append(_item("documentos", "Entidade dos documentos", ATENCAO,
                           "Nem todos os documentos parecem ser da mesma entidade. "
                           + (ent.get("observacao") or "")))
    campo = {"cartao_cnpj": "Cartão CNPJ", "estatuto": "Estatuto", "ata": "Ata"}
    for t in L.get("_triagem") or []:
        if not t.get("passa"):
            itens.append(_item("documentos", f"Arquivo fora do padrão ({campo.get(t.get('grupo'), t.get('grupo'))})",
                               PENDENCIA, f"{t.get('nome')}: {t.get('motivo')}. Não foi lido — peça o documento "
                               "certo.", _ev(t.get("nome"), 1)))
    if L.get("_fora"):
        itens.append(_item("documentos", "Arquivos que não abriram", PENDENCIA,
                           "Não foi possível ler: " + ", ".join(L["_fora"])
                           + " (formato não aceito, como Word ou Excel, ou arquivo corrompido) — peça em PDF."))
    return itens


def _cartao(L, insc):
    c = L.get("cartao")
    if not c:
        return [_item("cartao", "Cartão CNPJ", PENDENCIA, "Cartão CNPJ não encontrado entre os documentos.")]
    ev = _ev(c.get("arquivo"), c.get("pagina"))
    itens = []
    sit = _sem_acento(c.get("situacao_cadastral"))
    if not sit:
        itens.append(_item("cartao", "Situação cadastral", CONFIRA, "Não deu para ler a situação cadastral.", ev))
    elif sit.startswith("ativa"):
        itens.append(_item("cartao", "Situação cadastral", OK, "ATIVA.", ev))
    else:
        itens.append(_item("cartao", "Situação cadastral", NAO_APTO,
                           f"Situação {c.get('situacao_cadastral')} — só ATIVA pode participar.", ev))

    cod = _digitos(c.get("natureza_codigo"))
    nome = _sem_acento(c.get("nome_empresarial"))
    desc = _sem_acento(c.get("natureza_descricao"))
    empresa = (cod.startswith("2") or re.search(r"\bltda\b|\beireli\b|\bmei\b", nome)
               or re.search(r"empresari|microempreendedor|sociedade empresaria|limitada", desc))
    nat = f"{c.get('natureza_codigo') or ''} {c.get('natureza_descricao') or ''}".strip()
    if empresa:
        itens.append(_item("cartao", "Natureza jurídica", NAO_APTO,
                           f"Natureza de empresa ({nat or 'Ltda/MEI'}) — só OSC pode participar.", ev))
    elif cod.startswith("3"):
        itens.append(_item("cartao", "Natureza jurídica", OK, f"{nat} (sem fins lucrativos).", ev))
    elif cod:
        itens.append(_item("cartao", "Natureza jurídica", ATENCAO, f"{nat} — confira se pode participar.", ev))
    else:
        itens.append(_item("cartao", "Natureza jurídica", CONFIRA, "Não deu para ler a natureza jurídica.", ev))

    ab = data(c.get("data_abertura"))
    if not ab:
        itens.append(_item("cartao", "Data de abertura", CONFIRA, "Não deu para ler a data de abertura.", ev))
    elif ab > CORTE_ABERTURA:
        itens.append(_item("cartao", "Data de abertura", NAO_APTO,
                           f"Aberta em {_br(ab)}, depois de {_br(CORTE_ABERTURA)} — não terá 1 ano de "
                           "funcionamento.", ev))
    else:
        itens.append(_item("cartao", "Data de abertura", OK, f"Aberta em {_br(ab)}.", ev))

    em = data(c.get("data_emissao"))
    di = insc.get("data_inscricao")
    if em and di:
        st = OK if em == di else ATENCAO
        itens.append(_item("cartao", "Data de emissão", st,
                           f"Emitido em {_br(em)}" + ("" if st == OK else
                                                      f", inscrição em {_br(di)} — peça o cartão do dia.")
                           + ("." if st == OK else ""), ev))
    elif not em:
        itens.append(_item("cartao", "Data de emissão", CONFIRA, "Não deu para ler a data de emissão.", ev))

    cnpj_doc, cnpj_insc = _digitos(c.get("cnpj")), _digitos(insc.get("cnpj"))
    if cnpj_doc and cnpj_insc and len(cnpj_insc) != 14:
        itens.append(_item("cartao", "CNPJ da inscrição", ATENCAO,
                           "O CNPJ foi digitado errado na inscrição; vale o do cartão.", ev))
    return itens


def _finalidade(L):
    e = L.get("estatuto")
    if not e:
        return [_item("finalidade", "Estatuto", PENDENCIA, "Estatuto não encontrado entre os documentos.")]
    f = e.get("finalidade") or {}
    ev = _ev(e.get("arquivo"), f.get("pagina"), f.get("artigo"), f.get("trecho"))
    local = f.get("local")
    onde = " · ".join(x for x in [f.get("artigo"), f.get("titulo_secao")] if x)
    if local == "artigo_de_finalidades":
        itens = [_item("finalidade", "Finalidade esportiva", OK, f"Esporte no artigo de finalidades ({onde}).", ev)]
    elif local in ("outro_artigo", "meios_ou_atividades", "prerrogativas", "natureza_ou_carater"):
        lugar = {"outro_artigo": "em outro artigo", "meios_ou_atividades": "só entre os meios/atividades",
                 "prerrogativas": "só entre as prerrogativas", "natureza_ou_carater": "só no caráter/nome"}[local]
        itens = [_item("finalidade", "Finalidade esportiva", ATENCAO,
                       f"Esporte aparece {lugar} ({onde}), fora do artigo de finalidades.", ev)]
    else:
        itens = [_item("finalidade", "Finalidade esportiva", PENDENCIA,
                       "Não há finalidade esportiva no estatuto.", ev)]
    num = e.get("numeracao_artigos") or {}
    falhas = num.get("falhas") or []
    if num.get("sequencia_ok") is False:
        txt = "; ".join(f"{x.get('descricao')} (p.{x.get('pagina')})" for x in falhas[:4]) or "falha na numeração"
        itens.append(_item("finalidade", "Numeração dos artigos", ATENCAO, txt,
                           _ev(e.get("arquivo"), (falhas[0].get("pagina") if falhas else None))))
    return itens


def _ata_da_diretoria(L):
    """A ata mais recente que elege/empossa a diretoria (inclui fundação)."""
    atas = [a for a in (L.get("atas") or []) if a.get("elege_ou_empossa_diretoria")
            or a.get("tipo") in ("eleicao_e_posse", "eleicao", "posse", "fundacao")]
    return max(atas, key=lambda a: data(a.get("data_assembleia")) or dt.date(1900, 1, 1)) if atas else None


def _mandato(L, insc):
    ref = insc.get("data_inscricao") or dt.date.today()
    a = _ata_da_diretoria(L)
    e = L.get("estatuto") or {}
    me = e.get("mandato_diretoria") or {}
    if not a:
        return [_item("mandato", "Ata da diretoria", PENDENCIA,
                      "Nenhuma ata que eleja ou empossa a diretoria foi encontrada.")]
    ev = _ev(a.get("arquivo"), a.get("pagina_periodo"), trecho=a.get("periodo_trecho"))
    assembleia = data(a.get("data_assembleia"))
    inicio = data(a.get("inicio_mandato")) or assembleia
    fim = data(a.get("fim_mandato"), fim_do_mes=True)
    como = "período escrito na ata"
    dur = a.get("duracao_anos") or me.get("duracao_anos")
    if not fim and inicio and dur:
        fim = _somar_anos(inicio, dur)
        como = ("início + duração escrita na ata" if a.get("duracao_anos")
                else f"início + duração do estatuto ({me.get('artigo') or 'estatuto'})")
    itens = []
    if not fim:
        itens.append(_item("mandato", "Mandato vigente", ATENCAO,
                           "Não foi possível saber até quando vai o mandato — confira a ata e o estatuto.", ev))
    elif fim >= ref:
        itens.append(_item("mandato", "Mandato vigente", OK,
                           f"Vigente: {_br(inicio)} a {_br(fim)} ({como}).", ev))
    elif a.get("prorrogacao_trecho") or me.get("prorrogacao_trecho"):
        itens.append(_item("mandato", "Mandato vigente", ATENCAO,
                           f"Mandato terminou em {_br(fim)}; há prorrogação prevista — confira se há ata "
                           "registrada que prorrogue.", ev))
    else:
        itens.append(_item("mandato", "Mandato vigente", PENDENCIA,
                           f"Mandato vencido em {_br(fim)} — peça a ata da diretoria atual.", ev))
    if a.get("duracao_anos") and me.get("duracao_anos") and \
            abs(float(a["duracao_anos"]) - float(me["duracao_anos"])) > 0.01:
        itens.append(_item("mandato", "Ata x estatuto", ATENCAO,
                           f"A ata fala em {a['duracao_anos']:g} anos e o estatuto em "
                           f"{me['duracao_anos']:g} anos ({me.get('artigo') or ''}).",
                           _ev(e.get("arquivo"), me.get("pagina"), me.get("artigo"), me.get("trecho"))))
    if a.get("tipo") == "fundacao":
        itens.append(_item("mandato", "Tipo de ata", OK, "Ata de fundação vale porque o mandato está vigente."
                           if fim and fim >= ref else "Ata de fundação.", ev))
    return itens


def _registro(peca, reg, sede, bloco="cartorio"):
    reg = reg or {}
    de = {"estatuto": "do estatuto", "ata": "da ata"}.get(peca, f"do {peca}")
    sit = reg.get("situacao")
    ev = _ev(reg.get("arquivo"), reg.get("pagina"), trecho=reg.get("trecho"))
    dados = ", ".join(x for x in [
        reg.get("cartorio_nome"), (f"registro {reg['numero_registro']}" if reg.get("numero_registro") else None),
        reg.get("averbacao"), (f"livro {reg['livro']}" if reg.get("livro") else None),
        (f"fls. {reg['folha']}" if reg.get("folha") else None), reg.get("data_registro")] if x)
    itens = []
    if sit == "registrado":
        if reg.get("e_registro_civil_pessoas_juridicas") is False:
            itens.append(_item(bloco, f"Registro {de}", ATENCAO,
                               f"Registrado, mas não em Pessoas Jurídicas ({reg.get('cartorio_nome') or '?'}).", ev))
        else:
            itens.append(_item(bloco, f"Registro {de}", OK, f"Registrado: {dados}.", ev))
        if reg.get("incertezas"):
            itens.append(_item(bloco, f"Números do registro {de}", CONFIRA,
                               f"Confira no carimbo ({reg.get('posicao_na_pagina') or 'página indicada'}): "
                               f"{reg['incertezas']}", ev))
    elif sit == "ilegivel":
        itens.append(_item(bloco, f"Registro {de}", CONFIRA,
                           f"Há carimbo de cartório, mas não dá para ler "
                           f"({reg.get('posicao_na_pagina') or 'página indicada'}).", ev))
    elif sit == "so_protocolado":
        itens.append(_item(bloco, f"Registro {de}", PENDENCIA,
                           "Só protocolado no cartório, sem registro — peça o registrado.", ev))
    else:
        itens.append(_item(bloco, f"Registro {de}", PENDENCIA,
                           f"Sem registro em cartório ({peca} enviado).", ev))
    cid = _cidade(reg.get("cidade_cartorio"))
    if sit == "registrado" and cid and sede and cid != _cidade(sede):
        itens.append(_item(bloco, f"Cidade do cartório ({peca})", ATENCAO,
                           f"Cartório em {reg.get('cidade_cartorio')}, sede em {sede}.", ev))
    return itens


def _cartorio(L, insc):
    sede = insc.get("cidade_uf") or (L.get("cartao") or {}).get("municipio_uf") \
        or (L.get("entidade") or {}).get("cidade_uf_sede")
    itens = []
    if L.get("estatuto"):
        itens += _registro("estatuto", L["estatuto"].get("registro"), sede)
    a = _ata_da_diretoria(L)
    if a:
        itens += _registro("ata", a.get("registro"), sede)
    return itens


# ------------------------------------------------------------------ entrada

def avaliar(leitura, cnpj=None, data_inscricao=None, cidade_uf=None):
    """leitura: o dict do leitor_ia. Devolve {itens, blocos, resultado}."""
    insc = {"cnpj": cnpj, "data_inscricao": data_inscricao if isinstance(data_inscricao, dt.date)
            else data(data_inscricao), "cidade_uf": cidade_uf}
    itens = (_documentos(leitura, insc) + _cartao(leitura, insc) + _finalidade(leitura)
             + _mandato(leitura, insc) + _cartorio(leitura, insc))
    blocos = {}
    for b in BLOCOS:
        sts = [i["status"] for i in itens if i["bloco"] == b]
        if sts:
            blocos[b] = max(sts, key=_PESO.get)
    pior = max((i["status"] for i in itens), key=_PESO.get, default=OK)
    # Sem cartão, sem estatuto ou sem ata da diretoria não há como aprovar: o resultado
    # é Não apto até a entidade mandar o documento (cada item continua como Pendência).
    faltam = [nome for nome, falta in (("cartão CNPJ", not leitura.get("cartao")),
                                       ("estatuto", not leitura.get("estatuto")),
                                       ("ata da diretoria", not _ata_da_diretoria(leitura))) if falta]
    if pior == NAO_APTO or faltam:
        resultado = "NAO_APTO"
    else:
        resultado = "APTO" if pior == OK else "APTO_COM_AJUSTES"
    return {"itens": itens, "blocos": blocos, "resultado": resultado, "faltam": faltam}
