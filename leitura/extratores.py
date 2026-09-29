# -*- coding: utf-8 -*-
"""
Extração dos campos de cada peça do dossiê (Cartão CNPJ, Estatuto, Ata),
conforme o schema da "Especificação de conhecimento — Conferência Documental".

Cada campo vem acompanhado da evidência (arquivo, página, trecho) e, no
estatuto, do artigo onde está. Campo não encontrado fica None — as regras
decidem o que isso significa (nunca inventamos valor).
"""
import re
from difflib import SequenceMatcher

from leitura import datas as D
from leitura.campos import so_digitos, sem_acento
from leitura.documento import Evidencia

# ---------------------------------------------------------------- utilidades

def _linha_apos(doc, rotulo):
    """Linha do texto original logo abaixo do rótulo (Cartão CNPJ)."""
    m = doc.primeiro(rotulo)
    if not m:
        return None, None
    fim_linha = doc.texto.find("\n", m.end())
    if fim_linha < 0:
        return None, None
    prox = doc.texto.find("\n", fim_linha + 1)
    linha = doc.texto[fim_linha + 1: prox if prox > 0 else None].strip()
    return linha, fim_linha + 1


def _num_anos(txt):
    """'05(cinco)', '4 (quatro)', 'O5(cinco)', 'três' → int."""
    par = re.search(r"\(\s*([a-z]+)\s*\)", txt)
    if par:
        v, _ = D.numero_extenso([par.group(1)])
        if v:
            return v
    m = re.search(r"[o0]?(\d{1,2})", txt)
    if m:
        return int(m.group(1))
    v, _ = D.numero_extenso(re.findall(r"[a-z]+", txt)[:2])
    return v


def _num_dias(txt):
    return _num_anos(txt)


# ------------------------------------------------------------ registro/cartório

_FORTES = [
    ("registro", r"registrad[oa](?:\s*\(\s*[oa]\s*\))?\s+sob\s+o\s+n[o°º]?\.?\s*([\d.]{3,})"),
    ("registro", r"\bregistro\s+n[o°º]\.?\s*([\d.]{3,})"),
    ("registro_av", r"registro\s*:?\s*(\d{2,})\s*[-–]\s*av\.?\s*(\d+)"),
    ("averbacao", r"averbad[oa]\s+no\s+livro\s+([a-z0-9\-]+)\s+sob\s+a\s+matricula\s+n?[o°º]?\s*([\d.\-]{5,})"),
    ("protocolo", r"protocolad[oa]\s+sob\s+o\s+n[o°º]?\s*([\d.]+)\s+em\s+(\d{2}/\d{2}/\d{4})"),
    ("protocolo", r"\bprotocolo\s*(?:central\s+rcpj)?\s*:?\s*(\d{3,}[\d\-]*)"),
    ("digital", r"registrado e assinado digitalmente pelo registro civil das pessoas juridicas"
                r"[^\n]{0,60}?em\s+(\d{2}/\d{2}/\d{4})"),
    ("digital", r"\brcpj-?[a-z]{2}\s+(\d{2}/\d{2}/\d{4})"),
    ("selo", r"\bselo\s+(?:eletronico\s+)?n?[o°º]?\s*([a-z]{2,5}\s?\d{4,6})"),
]
# só marcas de CARIMBO/SELO (não o texto do estatuto, que fala em "registro em cartório").
# Regex tolerantes ao OCR: "BELO DE CORBULTA" = selo de consulta, "Escreventa" = escrevente.
_INDICIOS = [r"[sb]elo\s+de\s+co[nmr]\w*", r"selo\s+de\s+fiscaliza", r"selo\s+eletr", r"poder\s+judic",
             r"corregedori", r"\brtdpj\b", r"\brcpj\b", r"escrevent", r"oficial\s+de\s+registro",
             r"\bemol\b", r"emolumento", r"tabeli[aã]o", r"consulte?\s+a\s+validade", r"codigo\s+de\s+seguranca",
             r"registro\s+de\s+t[iíl]tulos"]


def registro(doc):
    """
    Marcas de registro em cartório, página a página.
    {"forte": [págs], "indicio": [págs], "dados": {...}, "ev": Evidencia|None,
     "ev_indicio": Evidencia|None, "fls": [(pág, x, y)], "averbacoes": [int]}
    """
    from leitura.documento import plano_1a1
    forte, indicio, dados = [], [], {}
    ev = ev_ind = None
    fls, avs = [], []
    for p in doc.paginas:
        bruto = p["texto"] + "\n" + p.get("extra", "")
        plano = plano_1a1(bruto)
        achou_forte = False
        for chave, rx in _FORTES:
            m = re.search(rx, plano)
            if not m:
                continue
            achou_forte = True
            if ev is None:
                ini = max(0, m.start() - 60)
                ev = Evidencia(doc.arquivo, p["pagina"], bruto[ini:m.end() + 140])
            if chave == "registro":
                dados.setdefault("registro_numero", m.group(1).strip("."))
            elif chave == "registro_av":
                dados.setdefault("registro_numero", m.group(1))
                dados.setdefault("averbacao", f"Av.{m.group(2)}")
            elif chave == "averbacao":
                dados.setdefault("livro", m.group(1).upper())
                dados.setdefault("matricula", m.group(2).strip(".-"))
            elif chave == "protocolo":
                dados.setdefault("protocolo", m.group(1))
                if m.lastindex and m.lastindex >= 2:
                    dados.setdefault("data_protocolo", m.group(2))
            elif chave == "digital":
                dados.setdefault("data_registro", m.group(1))
                dados.setdefault("registro_digital", True)
            elif chave == "selo":
                dados.setdefault("selo", m.group(1).upper().replace(" ", ""))
            # data do registro: 1ª data depois da marca
            if "data_registro" not in dados:
                d = D.achar_datas(bruto[m.start(): m.end() + 200])
                if d:
                    dados["data_registro"] = D.br(d[0][0])
        mliv = re.search(r"\blivro\s*:?\s*([a-z]{1,2}[\-\s]?\d{1,3}|[a-z])\b", plano)
        if mliv and achou_forte:
            dados.setdefault("livro", mliv.group(1).upper().replace(" ", ""))
        mcart = re.search(r"(registro civil das pessoas juridicas(?: de [a-z ]{3,30})?|"
                          r"\d\s*[o°º]?\s*(?:oficio|registro de titulos)[a-z ,]{0,60}|cartorio [a-z ]{3,40})",
                          plano)
        if mcart and "cartorio" not in dados:
            dados["cartorio"] = bruto[mcart.start():mcart.end()].strip()
        if achou_forte:
            forte.append(p["pagina"])
        else:
            mi = next((m for m in (re.search(k, plano) for k in _INDICIOS) if m), None)
            if mi:
                indicio.append(p["pagina"])
                if ev_ind is None:
                    ev_ind = Evidencia(doc.arquivo, p["pagina"], bruto[max(0, mi.start() - 40): mi.start() + 120])
        for mf in re.finditer(r"\bfl[s]?\.?\s*:?\s*(\d{1,3})\s*/\s*(\d{1,3})\b", plano):
            fls.append((p["pagina"], int(mf.group(1)), int(mf.group(2))))
        for ma in re.finditer(r"\bav\.?\s*(\d{1,2})\b", plano):
            avs.append(int(ma.group(1)))
    return {"forte": forte, "indicio": indicio, "dados": dados, "ev": ev, "ev_indicio": ev_ind,
            "fls": fls, "averbacoes": sorted(set(avs))}


# ------------------------------------------------------------------ cartão CNPJ

def cartao(doc):
    c = {"cnpj": None, "data_abertura": None, "razao_social": None, "nome_fantasia": None,
         "cnae_principal": None, "cnaes_secundarias": [], "natureza_juridica": None,
         "endereco": {}, "situacao": None, "data_situacao": None, "data_emissao": None, "ev": {}}
    t = doc.texto
    m = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\s+(\d{2}/\d{2}/\d{4})", t)
    if m:
        c["cnpj"] = so_digitos(m.group(1))
        c["data_abertura"] = D.fazer(*m.group(2).split("/"))
        c["ev"]["abertura"] = doc.ev(m.start(), 60, 60)
        c["ev"]["cnpj"] = c["ev"]["abertura"]
    elif doc.cnpjs():
        c["cnpj"] = doc.cnpjs()[0]

    linha, pos = _linha_apos(doc, r"nome empresarial")
    if linha:
        c["razao_social"] = linha
        c["ev"]["razao"] = doc.ev(pos, 20, 80)
    linha, _ = _linha_apos(doc, r"nome de fantasia\)?\s*porte")
    if linha:
        nome = re.sub(r"\s+(DEMAIS|ME|EPP|MICRO EMPRESA|EMPRESA DE PEQUENO PORTE)$", "", linha).strip()
        c["nome_fantasia"] = None if nome.startswith("*") else nome

    linha, pos = _linha_apos(doc, r"atividade economica principal")
    if linha:
        mm = re.search(r"(\d{2}\.\d{2}-\d-\d{2})\s*-\s*(.+)", linha)
        if mm:
            c["cnae_principal"] = (mm.group(1), mm.group(2).strip())
            c["ev"]["cnae"] = doc.ev(pos, 60, 120)
    ms = doc.primeiro(r"atividades economicas secundarias")
    mn = doc.primeiro(r"natureza juridica")
    if ms and mn and mn.start() > ms.start():
        bloco = t[ms.end():mn.start()]
        c["cnaes_secundarias"] = [(a, b.strip()) for a, b in
                                  re.findall(r"(\d{2}\.\d{2}-\d-\d{2})\s*-\s*([^\n]+)", bloco)]
    linha, pos = _linha_apos(doc, r"codigo e descricao da natureza juridica")
    if linha:
        mm = re.search(r"(\d{3}-\d)\s*-\s*(.+)", linha)
        if mm:
            c["natureza_juridica"] = (mm.group(1), mm.group(2).strip())
            c["ev"]["natureza"] = doc.ev(pos, 40, 80)

    linha, pos = _linha_apos(doc, r"logradouro\s+numero\s+complemento")
    if linha:
        toks = linha.split()
        i = next((k for k, tk in enumerate(toks) if re.fullmatch(r"\d+|S/?N", tk, re.I)), None)
        end = {"linha": linha}
        if i is not None:
            end["logradouro"] = " ".join(toks[:i])
            end["numero"] = toks[i].lstrip("0") or "0"
            end["complemento"] = " ".join(toks[i + 1:]).strip("* ")
        else:
            end["logradouro"] = linha
        c["endereco"] = end
        c["ev"]["endereco"] = doc.ev(pos, 30, 170)
    linha, _ = _linha_apos(doc, r"cep\s+bairro/distrito\s+municipio\s+uf")
    if linha:
        mm = re.search(r"(\d{2}\.?\d{3}-?\d{3})\s+(.*?)\s+([A-Z]{2})\s*$", linha)
        if mm:
            c["endereco"].update(cep=so_digitos(mm.group(1)), bairro_municipio=mm.group(2), uf=mm.group(3))

    linha, pos = _linha_apos(doc, r"situacao cadastral\s+data da situacao cadastral")
    if linha:
        mm = re.match(r"([A-ZÀ-Ú ]+?)\s+(\d{2}/\d{2}/\d{4})", linha)
        if mm:
            c["situacao"] = mm.group(1).strip()
            c["data_situacao"] = mm.group(2)
            c["ev"]["situacao"] = doc.ev(pos, 60, 40)
    m = doc.primeiro(r"emitido no dia\s+(\d{2}/\d{2}/\d{4})")
    if m:
        c["data_emissao"] = D.fazer(*m.group(1).split("/"))
        c["ev"]["emissao"] = doc.ev(m.start(), 10, 90)
    c["oficial"] = bool(doc.primeiro(r"comprovante de inscricao e de situacao")) and \
        bool(doc.primeiro(r"instrucao normativa rfb|receita federal|cadastro nacional da pessoa juridica"))
    return c


# ------------------------------------------------------------------- estatuto

_ESPORTE = r"esport|desport|atividades? fisicas?|educacao fisica|modalidades?"
_CARGOS = [
    ("Diretoria Executiva", r"^diretoria executiva$"),
    ("Presidente", r"\bpresidente\b(?!\s+do conselho fiscal)"),
    ("Vice-Presidente", r"vice[\s\-]?presidente"),
    ("Secretário", r"secretari[oa]s?"),
    ("Tesoureiro", r"tesoureir[oa]s?"),
    ("Diretor Executivo", r"diretor(?:a|es)? executiv[oa]"),
    ("Diretor Financeiro", r"diretor[a]?(?:\s*\(a\))?\s+financeir[oa]"),
    ("Diretor Administrativo", r"diretor(?:a|es)? administrativ[oa]"),
    ("Diretor de Desenvolvimento Social", r"diretor[a]? de desenvolvimento social"),
    ("Diretor Social", r"diretor[a]?(?:\s*\(a\))?\s+social"),
    ("Diretor de Patrimônio", r"diretor[a]?(?:\s*\(a\))?\s+de patrimonio"),
    ("Conselho Fiscal", r"conselh(?:o|eir[oa]s?) fiscal"),
]


def _orgao(txt):
    """Órgão a que um trecho se refere (para o mandato)."""
    for nome, rx in [("Conselho Fiscal", r"conselho fiscal"),
                     ("Conselho de Administração", r"conselho de administracao"),
                     ("Conselho Diretor", r"conselho diret"),
                     ("Diretoria", r"diretoria"),
                     ("Presidente", r"presidente")]:
        if re.search(rx, txt):
            return nome
    return None


def estatuto(doc):
    e = {"denominacao": doc.denominacao(), "cnpjs": doc.cnpjs(), "artigos": doc.artigos(),
         "data_fundacao": None, "sede": {}, "finalidade": [], "restrita_associados": None,
         "representacao": [], "mandatos": [], "vitalicio": None, "prorrogacao": None,
         "convocacao_dias": None, "segunda_convocacao_min": None, "elege_diretoria": None,
         "composicao": None, "registro": registro(doc), "reforma": None, "ev": {}}

    m = doc.primeiro(r"fundad[ao]\s+(?:em\s+)?(?:assembleia\s+realizada\s+em\s+)?")
    if m:
        ds = D.achar_datas(doc.texto[m.end(): m.end() + 70])
        if ds:
            e["data_fundacao"] = ds[0][0]
            e["ev"]["fundacao"] = doc.ev(m.start(), 20, 90)

    # sede: artigo que fala em "sede"
    for mm in doc.buscar(r"\bsede\b"):
        janela = doc.plano[mm.start(): mm.start() + 260]
        mrua = re.search(r"((?:rua|r\.|avenida|av\.|estrada|travessa|alameda|praca|rodovia)\s+[^,\n]{3,60})", janela)
        if not mrua:
            continue
        ini = mm.start() + mrua.start()
        resto = doc.texto[ini: ini + 200]
        mnum = re.search(r"(?:n[º°o]\.?\s*|,\s*)(\d{1,5})\b", resto)
        mcep = re.search(r"\b(\d{2}\.?\d{3}\s*-\s*\d{3})\b", doc.texto[mm.start(): mm.start() + 300])
        e["sede"] = {"logradouro": doc.texto[ini: ini + len(mrua.group(1))].strip(),
                     "numero": mnum.group(1) if mnum else None,
                     "cep": so_digitos(mcep.group(1)) if mcep else None}
        e["ev"]["sede"] = doc.ev(mm.start(), 20, 220)
        e["ev"]["sede_art"] = doc.rotulo_artigo(mm.start())
        break

    # finalidade esportiva (onde aparece e se é no artigo dos fins)
    for mm in doc.buscar(_ESPORTE):
        art = doc.artigo_em(mm.start())
        fins = bool(art and re.search(r"finalidade|objetivo|\bfins\b|objeto|missao|atuacao", art["plano"][:600]))
        e["finalidade"].append({"artigo": doc.rotulo_artigo(mm.start()), "em_fins": fins,
                                "ev": doc.ev(mm.start(), 140, 120)})
    ma = doc.primeiro(r"entre (?:os )?seus associados")
    if ma:
        e["restrita_associados"] = {"artigo": doc.rotulo_artigo(ma.start()), "ev": doc.ev(ma.start(), 100, 80)}

    # quem representa a entidade
    for mm in doc.buscar(r"representa(?:r|cao)?[^.;]{0,80}?(ativa e passivamente|judicial|em juizo|extrajudicial)"):
        art = doc.artigo_em(mm.start())
        base = doc.plano[art["pos"]: mm.start()] if art else doc.plano[max(0, mm.start() - 300): mm.start()]
        cargo = None
        mc = list(re.finditer(r"compete (?:ao|a)\s+([a-z\- ]{4,40}?)(?:[:;,]|\s+as seguintes|$)", base))
        suj = re.match(r"[^a-z]*art\w*[\.,]?\s*\d+[^a-z]*(?:(?:o|a)\s+)?(presidente|vice[\s\-]?presidente|"
                       r"diretor[a]? executiv[oa]|diretoria executiva|diretor[a]? [a-z]+|diretoria|conselho diret\w+)",
                       base)
        if mc:
            cargo = mc[-1].group(1).strip()
        elif suj:
            cargo = suj.group(1)
        else:
            mc = list(re.finditer(r"(presidente|vice[\s\-]?presidente|diretoria executiva|diretor executivo|"
                                  r"conselho diret\w+|diretoria)", doc.plano[max(0, mm.start() - 250): mm.start()]))
            if mc:
                cargo = mc[-1].group(1)
        janela = doc.plano[max(0, mm.start() - 150): mm.end() + 250]
        conj = re.search(r"em conjunto|conjuntamente|juntamente com", janela)
        e["representacao"].append({"cargo": (cargo or "").strip(), "artigo": doc.rotulo_artigo(mm.start()),
                                   "conjunto": bool(conj), "ev": doc.ev(mm.start(), 120, 140)})

    # mandatos (por órgão)
    for mm in doc.buscar(r"mandato[^.;]{0,120}?([o0]?\d{1,2}\s*\(\s*[a-z]+\s*\)|[o0]?\d{1,2}|um|dois|tres|quatro|cinco)\s*(?:\([^)]{0,12}\)\s*)?anos"):
        antes = doc.plano[max(0, mm.start() - 120): mm.start() + 60]
        e["mandatos"].append({"orgao": _orgao(antes) or "—", "anos": _num_anos(mm.group(1)),
                              "artigo": doc.rotulo_artigo(mm.start()), "ev": doc.ev(mm.start(), 80, 160)})
    # "Diretoria eleita pelo período de 4 (quatro) anos" (sem a palavra mandato)
    for mm in doc.buscar(r"(?:eleit[oa]s?|nomead[oa]s?|mandato)[^.;]{0,60}?(?:pelo\s+|por\s+)?(?:periodo|prazo)\s+de\s+"
                         r"([o0]?\d{1,2}\s*\(\s*[a-z]+\s*\)|[o0]?\d{1,2}|um|dois|tres|quatro|cinco)\s*(?:\([^)]{0,12}\)\s*)?anos"):
        antes = doc.plano[max(0, mm.start() - 120): mm.start() + 20]
        rot = doc.rotulo_artigo(mm.start())
        if not any(m["artigo"] == rot for m in e["mandatos"]):
            e["mandatos"].append({"orgao": _orgao(antes) or "—", "anos": _num_anos(mm.group(1)),
                                  "artigo": rot, "ev": doc.ev(mm.start(), 80, 160)})
    mv = doc.primeiro(r"vitalici")
    if mv:
        e["vitalicio"] = {"artigo": doc.rotulo_artigo(mv.start()), "ev": doc.ev(mv.start(), 120, 120)}
    mp = doc.primeiro(r"mandato[^.]{0,200}prorrog|prorrog[^.]{0,120}mandato")
    if mp:
        e["prorrogacao"] = {"artigo": doc.rotulo_artigo(mp.start()), "ev": doc.ev(mp.start(), 60, 200)}

    # convocação da assembleia: antecedência e 2ª convocação
    rx_ante = (r"anteceden\w*\s*(?:minima\s*)?(?:de\s*)?(?:,\s*no\s*minimo,?\s*)?(\d{1,3}|[a-z]+)\s*(\([a-z ]+\))?\s*dias"
               r"|(\d{1,3})\s*(\([a-z ]+\))?\s*dias\s+(?:uteis\s+)?de\s+anteceden")
    for mm in doc.buscar(rx_ante):
        art = doc.artigo_em(mm.start())
        ctx = (art["plano"][:400] if art else "") + doc.plano[max(0, mm.start() - 250): mm.start()]
        if "assembl" in ctx and "convoca" in ctx:
            num = mm.group(1) or mm.group(3)
            par = mm.group(2) or mm.group(4) or ""
            e["convocacao_dias"] = {"dias": _num_dias(num + par),
                                    "artigo": doc.rotulo_artigo(mm.start()), "ev": doc.ev(mm.start(), 160, 80)}
            break
    ms = doc.primeiro(r"segunda convocacao[^.;]{0,160}?(meia hora|trinta minutos|30 minutos|uma hora|1 hora|"
                      r"(\d{1,3})\s*min)")
    if ms:
        g = ms.group(1)
        minutos = 30 if ("meia" in g or "trinta" in g or g.startswith("30")) else 60 if "hora" in g else int(ms.group(2))
        e["segunda_convocacao_min"] = {"min": minutos, "artigo": doc.rotulo_artigo(ms.start()),
                                       "ev": doc.ev(ms.start(), 60, 160)}

    # quem elege a diretoria
    me = doc.primeiro(r"(?:eleger|eleitos? pela|elegera|eleicao d[aoe]s?)[^.;]{0,80}?(?:diretoria|conselho diret\w*|membros)"
                      r"|(?:diretoria|conselho diret\w*)[^.;]{0,80}?eleit[oa]s? pel[ao]\s+assembleia")
    if me:
        e["elege_diretoria"] = {"artigo": doc.rotulo_artigo(me.start()), "ev": doc.ev(me.start(), 120, 140),
                                "assembleia": "assembleia" in doc.plano[max(0, me.start() - 300): me.end() + 120]}

    # composição da diretoria: 1º artigo que lista ao menos 2 cargos da diretoria
    for mcomp in doc.buscar(r"(?:diretoria(?: executiva)?|conselho diret\w*)[^.;]{0,220}?(?:sera|e)?\s*"
                            r"(?:constituid|compost|formad)[oa]"):
        art = doc.artigo_em(mcomp.start())
        trecho = doc.plano[mcomp.start(): mcomp.start() + 900]
        if art:
            trecho = doc.plano[mcomp.start(): art["pos"] + len(art["plano"])][:900]
        cargos = [nome for nome, rx in _CARGOS if re.search(rx, trecho) and nome != "Diretoria Executiva"]
        if len([c for c in cargos if c != "Conselho Fiscal"]) >= 2:
            e["composicao"] = {"cargos": cargos, "artigo": doc.rotulo_artigo(mcomp.start()),
                               "ev": doc.ev(mcomp.start(), 20, 300)}
            break

    mr = doc.primeiro(r"(\d{1,2})\s*[ºªo°]?\s*(?:alteracao|reforma)\s+(?:do\s+|de\s+)?estatuto"
                      r"|(primeira|segunda|terceira|quarta|quinta)\s+(?:alteracao|reforma)")
    if mr:
        e["reforma"] = {"texto": doc.texto[mr.start(): mr.end()], "ev": doc.ev(mr.start(), 10, 80)}
    return e


# ------------------------------------------------------------------------ ata

_NAO_NOME = r"(?!(?:Conselho|Conselheir[oa]|Diretor|Diretora|Diretoria|Vice|Presidente|Secret|Tesoureir|Efetivo|Suplente|Membro)\b)"
_RX_CARGO = re.compile(
    r"(?i)(vice[\s\-]?presidente|presidente|presente|(?:\d\s*[ºª°o]\s*)?diretor(?:\(a\)|a)?"
    r"(?:\s+(?:e\s+|de\s+|da\s+|do\s+)*[a-zà-ú]+){0,4}?|(?:\d\s*[ºª°o]\s*)?secret[aá]ri[oa](?:\(a\))?"
    r"|(?:\d\s*[ºª°o]\s*)?tesoureir[oa](?:\(a\))?|conselheir[oa]\s+fiscal(?:\s*\d)?(?:\s*\([^)]*\))?"
    r"|conselho de administra[cç][aã]o|conselho fiscal|diretoria executiva"
    r"|efetivo|(?:\d\s*[ºª°o]\s*)?suplente)\s*:\s*"
    r"(?:(?:sr\(?a?\)?|sr[ºª2?]|sra\.?|srta\.?|bisp[oa]|dr[a]?\.?)\s+)*"
    r"(" + _NAO_NOME + r"[A-ZÀ-Ú][a-zà-úA-ZÀ-Ú'´]+(?:\s+(?:de|da|do|dos|das|e|d')?\s*" + _NAO_NOME +
    r"[A-ZÀ-Ú][a-zà-úA-ZÀ-Ú'´]+){1,8})")


def cargo_canonico(c):
    """'Diretora Financeira' / '1º Diretor(a) Financeiro(a)' → 'Diretor Financeiro'."""
    plano = sem_acento(c)
    for nome, rx in _CARGOS:
        if re.search(rx, plano):
            if nome == "Presidente" and re.search(r"vice", plano):
                return "Vice-Presidente"
            return nome
    if re.search(r"suplente|efetivo", plano):
        return "Conselho Fiscal"
    if re.search(r"conselho de administra", plano):
        return "Conselho de Administração"
    if re.fullmatch(r"\s*(?:a\s+)?diretoria\s*", plano):
        return "Diretoria (colegiado)"
    return c.strip()


def _limpa_cargo(c):
    c = re.sub(r"\s+", " ", c).strip()
    if c.lower() == "presente":   # OCR comum de "Presidente"
        return "Presidente"
    return c[:1].upper() + c[1:]


def eleitos(doc):
    """Membros eleitos com cargo e qualificação (quando a ata traz)."""
    t = doc.texto
    linhas = t.split("\n")
    so_cargo = [bool(_RX_CARGO_SO.match(ln)) for ln in linhas]

    def _em_tabela(pos):
        """Cargo sozinho na linha, com vizinho também só-cargo = tabela em colunas."""
        n = t.count("\n", 0, pos)
        return so_cargo[n] and ((n > 0 and so_cargo[n - 1]) or (n + 1 < len(linhas) and so_cargo[n + 1]))
    ms = [m for m in _RX_CARGO.finditer(t) if not _em_tabela(m.start())]
    saida = []
    for i, m in enumerate(ms):
        fim = ms[i + 1].start() if i + 1 < len(ms) else min(len(t), m.end() + 900)
        bloco = t[m.end(): fim]
        nome = re.sub(r"\s+", " ", m.group(2)).strip()
        if re.match(r"(?i)(da|do)\s", nome) or len(nome.split()) < 2:
            continue
        rg = re.search(r"(?i)identidade[^\d]{0,30}([\d][\d.\-/xX ]{3,14}\d)", bloco)
        cpf = re.search(r"(?i)cpf[^\d]{0,20}([\d][\d.\-/, ]{9,16}\d)", bloco)
        fil = re.search(r"(?i)filia[cç][aã]o\s+(.+?)(?:\s*,?\s*residente|,\s*email|;|\.\s)", bloco, re.S)
        civ = re.search(r"(?i)(solteir[oa]|casad[oa]|divorciad[oa]|vi[uú]v[oa]|separad[oa]|uni[aã]o est[aá]vel)", bloco)
        end = re.search(r"(?i)(?:\bna|\bà)\s+((?:rua|av\.?|avenida|estrada|est\.)[^,;]+(?:,\s*[^,;]+)?)", bloco)
        pais = []
        if fil:
            pais = [re.sub(r"\s+", " ", x).strip(" ,.") for x in re.split(r"\s+e\s+", fil.group(1)) if x.strip()]
        # a mesma pessoa listada de novo (ex.: ata de eleição + termo de posse)
        chave = " ".join(sem_acento(nome).split()[:3])
        cargo = _limpa_cargo(m.group(1))
        if any(SequenceMatcher(None, " ".join(sem_acento(x["nome"]).split()[:3]), chave).ratio() > 0.85
               and cargo_canonico(x["cargo"]) == cargo_canonico(cargo) for x in saida):
            continue
        saida.append({"cargo": _limpa_cargo(m.group(1)), "nome": nome,
                      "rg": re.sub(r"\s", "", rg.group(1)) if rg else None,
                      "cpf": so_digitos(cpf.group(1)) if cpf else None,
                      "filiacao": pais, "estado_civil": civ.group(1).lower() if civ else None,
                      "endereco": re.sub(r"\s+", " ", end.group(1)).strip() if end else None,
                      "ev": doc.ev(m.start(), 0, 200)})
    return saida + _eleitos_em_colunas(doc, saida)


_RX_CARGO_SO = re.compile(r"(?i)^\s*((?:\d\s*[ºª°o]\s*)?(?:vice[\s\-]?presidente|presidente|secret[aá]ri[oa]|"
                          r"tesoureir[oa]|diretor[a]?(?:\s+[a-zà-ú]+){0,3}|conselheir[oa]\s+fiscal(?:\s*\d)?))\s*:\s*$")
_RX_NOME_QUALIF = re.compile(r"^\s*([A-ZÀ-Ú][a-zà-ú'´]+(?:\s+(?:de|da|do|dos|das|e)?\s*[A-ZÀ-Ú][a-zà-ú'´]+){1,8})\s*,\s*"
                             r"(?=[^\n]{0,40}(?:brasileir|casad|solteir|divorciad|vi[uú]v))")


def _eleitos_em_colunas(doc, ja):
    """Tabela lida pelo OCR coluna a coluna: primeiro os cargos ('Presidente:',
    '1º Secretária:'...) e depois os nomes com a qualificação, na mesma ordem."""
    linhas = doc.texto.split("\n")
    pos, acum = [], 0
    for ln in linhas:
        pos.append(acum)
        acum += len(ln) + 1
    saida, i = [], 0
    nomes_ja = {sem_acento(x["nome"]) for x in ja}
    while i < len(linhas):
        cargos = []
        while i < len(linhas) and _RX_CARGO_SO.match(linhas[i]):
            cargos.append((_RX_CARGO_SO.match(linhas[i]).group(1), i))
            i += 1
        if len(cargos) < 2:
            i += 1
            continue
        nomes, j = [], i
        while j < len(linhas) and len(nomes) < len(cargos) and j - i < 80:
            mn = _RX_NOME_QUALIF.match(linhas[j])
            if mn:
                nomes.append((mn.group(1), j))
            j += 1
        for (cargo, _), (nome, jn) in zip(cargos, nomes):
            if sem_acento(nome) in nomes_ja:
                continue
            bloco = "\n".join(linhas[jn: jn + 6])
            rg = re.search(r"(?i)\bRG\b[^\d]{0,12}([\d][\d.\-/xX]{4,14}\d)", bloco)
            cpf = re.search(r"(?i)cpf[^\d]{0,20}([\d][\d.\-/ ]{9,16}\d)", bloco)
            civ = re.search(r"(?i)(solteir[oa]|casad[oa]|divorciad[oa]|vi[uú]v[oa])", bloco)
            saida.append({"cargo": _limpa_cargo(cargo), "nome": nome, "rg": rg.group(1) if rg else None,
                          "cpf": so_digitos(cpf.group(1)) if cpf else None, "filiacao": [],
                          "estado_civil": civ.group(1).lower() if civ else None, "endereco": None,
                          "ev": doc.ev(pos[jn], 0, 200)})
        i = j
    return saida


def ata(doc):
    a = {"denominacao": doc.denominacao(), "cnpjs": doc.cnpjs(), "tipo": None, "eleicao": False,
         "alteracao_estatuto": False, "data_assembleia": None, "data_edital": None,
         "horarios": None, "mandatos": [], "eleitos": [], "registro": registro(doc),
         "anexo_estatuto": None, "paginas_declaradas": None, "citacoes": [], "ev": {}}
    pl = doc.plano
    a["eleicao"] = bool(re.search(r"eleicao d[ao]s?\s+(?:nova\s+)?(?:diretoria|conselho|membros)|"
                                  r"eleger e empossar|foram eleit[oa]s|foi eleit[oa]|eleit[oa]s? por aclamacao|"
                                  r"empossad[oa]s?\s+(?:no|nos|para)|ata de posse|chapa unica",
                                  pl))
    md = doc.primeiro(r"destituicao d[oa]s?\s+(?:atual\s+)?(?:presidente|diretor|diretoria)|"
                      r"destituid[oa]\s+d[oa]\s+cargo")
    a["destituicao"] = doc.ev(md.start(), 60, 260) if md else None
    mv = doc.primeiro(r"(?:cargos?|posicoes)[^.]{0,120}?(?:vag[oa]s|vacantes?)|vacancia d[oa] cargo")
    a["vacancia"] = doc.ev(mv.start(), 40, 240) if mv else None
    a["alteracao_estatuto"] = bool(re.search(r"alteracao d[oa] (?:artigo|estatuto)|reforma d[oa] estatuto|"
                                            r"atualizacao do (?:novo )?estatuto", pl))
    if re.search(r"ata de posse|cerimonia de posse", pl):
        a["tipo"] = "posse"
    elif a["eleicao"]:
        a["tipo"] = "eleicao"
    elif a["alteracao_estatuto"]:
        a["tipo"] = "alteracao_estatutaria"
    elif re.search(r"fundacao|constituicao da associacao", pl):
        a["tipo"] = "fundacao"
    else:
        a["tipo"] = "outra"

    # data da assembleia: "No dia 17 do mês de dezembro…" / "Aos treze dias…" (a 1ª do texto)
    for rx, janela in ((r"\b(?:no dia|aos|au[s5])\b\s*\(?\d{0,2}", 120),
                       (r"\b(?:aos|as|au[s5])\b[^.]{0,70}?(?:dias?\b|horas?\b)", 220)):
        for mm in doc.buscar(rx):
            ds = D.achar_datas(doc.texto[mm.start(): mm.start() + janela])
            if ds and ds[0][1] < 40:
                a["data_assembleia"] = ds[0][0]
                a["ev"]["data"] = doc.ev(mm.start(), 0, 200)
                break
        if a["data_assembleia"]:
            break
    me = doc.primeiro(r"edital(?: de convocacao)?[^.;]{0,30}?(?:datado de|publicado (?:no dia|em)|de)\s*")
    if me:
        ds = D.achar_datas(doc.texto[me.end() - 3: me.end() + 60])
        if ds and ds[0][1] < 12:
            a["data_edital"] = ds[0][0]
            a["ev"]["edital"] = doc.ev(me.start(), 20, 90)
    mh1 = doc.primeiro(r"primeira (?:convocacao|chamada)[^.;]{0,40}?(\d{1,2})\s*h\s*(\d{2})?")
    mh2 = doc.primeiro(r"(\d{1,2})\s*h\s*(\d{2})?\s*(?:horas?)?,?\s*em segunda (?:convocacao|chamada)"
                       r"|segunda (?:convocacao|chamada)[^.;]{0,40}?(\d{1,2})\s*h\s*(\d{2})?")
    if mh1 and mh2:
        h1 = int(mh1.group(1)) * 60 + int(mh1.group(2) or 0)
        g = [x for x in mh2.groups() if x is not None]
        h2 = int(g[0]) * 60 + int(g[1] if len(g) > 1 else 0)
        a["horarios"] = {"intervalo_min": h2 - h1, "ev": doc.ev(mh1.start(), 20, 200)}

    for c in D.periodo_mandato(doc.texto):
        c["ev"] = doc.ev(c["pos"], 60, 140)
        a["mandatos"].append(c)
    if a["eleicao"] or a["tipo"] == "posse":
        a["eleitos"] = eleitos(doc)

    manexo = doc.primeiro(r"anexo\s+(?:i|1|01)\b[^\n]{0,40}?estatuto|estatuto social,?\s+anexo")
    if manexo:
        a["anexo_estatuto"] = {"incluso": len(doc.artigos()) >= 8, "ev": doc.ev(manexo.start(), 60, 100)}
    tot = [int(x) for x in re.findall(r"pagina\s+\d+\s+de\s+(\d+)", pl)]
    if tot:
        mpg = doc.primeiro(r"pagina\s+\d+\s+de\s+\d+")
        a["paginas_declaradas"] = {"total": max(tot), "ev": doc.ev(mpg.start(), 40, 40)}
    for mc in doc.buscar(r"(?:art\.?|artigo)\s*(\d{1,3})\s*[º°o]?[^.;]{0,30}?do\s+(?:presente\s+)?estatuto"):
        a["citacoes"].append({"artigo": int(mc.group(1)), "contexto": doc.plano[max(0, mc.start() - 200): mc.start()],
                              "ev": doc.ev(mc.start(), 160, 60)})
    return a
