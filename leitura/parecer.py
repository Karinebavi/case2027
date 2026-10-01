# -*- coding: utf-8 -*-
"""
Monta o PARECER da conferência documental no formato da especificação
(seção 7): resultado APTO / APTO COM AJUSTES / NÃO APTO, tabelas por bloco
(Item | Constatação | Status), documentos recebidos e faltantes, ajustes por
prioridade e pontos a confirmar no edital. Saída em dict (JSON) e Markdown.

Entrada: lista de Documento já lidos + dados da inscrição (CNPJ, nome).
"""
import datetime as dt
import hashlib
import re

from leitura import datas as D
from leitura import extratores as X
from leitura import regras_lie as R
from leitura.documento import TIPOS_LEGIVEIS, classificar, nome_confere

OBRIGATORIAS = [("cartao_cnpj", "Cartão CNPJ"), ("estatuto", "Estatuto social registrado"),
                ("ata", "Ata de eleição/posse da diretoria vigente, registrada")]
NAO_SOLICITADAS = ["Documento de identidade do representante (REP-01/02/03)",
                   "Declarações e modelos (Bloco 4: DEC-01 a DEC-13)",
                   "Edital de convocação e lista de presença (REG-10/11/18, quando não constam da ata)",
                   "Certidão de inteiro teor / breve relato (REG-14/15)"]
CONFIRMAR_EDITAL = ["tempo mínimo de funcionamento (padrão: mais de 1 ano)",
                    "recência do cartão CNPJ e das certidões (padrão: 30 dias para o cartão)",
                    "requisitos de governança (alternância de mandato, parentesco)",
                    "lista de CNAEs esportivas aceitas"]
VISUAL = ["Rasuras em documentos registrados (REG-19)",
          "Rubrica/carimbo do cartório nas folhas escaneadas (REG-03)",
          "Assinaturas manuscritas e legibilidade das cópias"]
BLOCOS = [("documentos", "Documentos recebidos"), ("habilitacao", "Habilitação da entidade"),
          ("registro", "Registro e diretoria"), ("representante", "Representante legal")]
STATUS_DOC = {"usado": "usado", "superado": "superado", "duplicado": "duplicado",
              "outra_entidade": "outra entidade", "irrelevante": "irrelevante", "apoio": "apoio"}


def _identidade(doc, cnpj_esp, nomes_esp):
    """'confirmada' | 'outra' | 'nao_confirmada' | 'sem_dados' + motivo."""
    cnpjs = doc.cnpjs()
    if cnpj_esp and cnpj_esp in cnpjs:
        return "confirmada", f"CNPJ {cnpj_esp} no documento"
    notas = [n for n in (nome_confere(nm, doc) for nm in nomes_esp if nm) if n is not None]
    melhor = max(notas) if notas else None
    if cnpj_esp and cnpjs and (melhor is None or melhor < 0.5):
        return "outra", f"CNPJ {cnpjs[0]} no documento"
    if melhor is not None and melhor >= 0.6:
        return "confirmada", "nome da entidade no documento"
    if melhor is not None and melhor < 0.34 and doc.denominacao():
        return "outra", f"nome no documento: {doc.denominacao()}"
    if melhor is None:
        return "sem_dados", ""
    return "nao_confirmada", f"nome no documento: {doc.denominacao() or '—'}"


def _ev_cnpj(d):
    """Evidência no ponto onde aparece o CNPJ (ou o nome) do documento."""
    m = re.search(r"\d{2}\.?\d{3}\.?\d{3}\s*/?\s*\d{4}\s*-?\s*\d{2}", d.texto)
    if m:
        return d.ev(m.start(), 120, 60)
    nome = d.denominacao()
    i = d.texto.find(nome) if nome else -1
    return d.ev(max(i, 0), 20, 200)


def _fmt_cnpj(c):
    c = str(c or "")
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else c


def montar(documentos, cnpj_inscricao=None, nome_inscricao=None, data_ref=None, api=None, config=None,
           projeto=""):
    ref = data_ref or dt.date.today()
    cfg = {**R.CONFIG_PADRAO, **(config or {})}
    achados, recebidos = [], []

    # 1) tipo e duplicados
    vistos = {}
    for d in documentos:
        tipo, _ = classificar(d) if not d.sem_texto else (d.grupo or None, None)
        # Resgate: se a classificação por conteúdo não reconheceu o tipo
        # ('irrelevante', comum em escaneado com OCR ruim), respeitar o campo
        # onde o mentor subiu o PDF. Não atrapalha a separação de arquivos
        # misturados, que depende da classificação quando ela acerta um tipo real.
        d.tipo = tipo if tipo and tipo != "irrelevante" else (d.grupo or tipo)
        d.hash = d.hash or hashlib.md5(d.texto.encode("utf-8")).hexdigest()
        if d.hash in vistos and not d.sem_texto:
            d.status = "duplicado"
        vistos.setdefault(d.hash, d)

    # 2) identidade da entidade
    cartoes = [d for d in documentos if d.tipo == "cartao_cnpj" and d.status == "usado"]
    carts = {id(d): X.cartao(d) for d in cartoes}
    cnpj_esp = cnpj_inscricao or (carts[id(cartoes[0])]["cnpj"] if cartoes else None)
    nomes_esp = [nome_inscricao]
    for d in cartoes:
        c = carts[id(d)]
        if not cnpj_esp or c["cnpj"] == cnpj_esp:
            nomes_esp += [c["razao_social"], c["nome_fantasia"]]
    if api and api.get("razao_social"):
        nomes_esp.append(api["razao_social"])
    nome_ref = next((n for n in nomes_esp if n), "") or ""

    for d in documentos:
        if d.status != "usado":
            continue
        if d.tipo == "irrelevante":
            d.status = "irrelevante"
            continue
        if d.tipo == "cartao_cnpj":
            c = carts[id(d)]
            if cnpj_esp and c["cnpj"] and c["cnpj"] != cnpj_esp:
                d.status = "outra_entidade"
                achados.append(R.achado("DOC-01", "documentos", "Peça de outra entidade", R.PENDENCIA,
                                        f"{d.arquivo} é o cartão CNPJ de {c['razao_social']} ({_fmt_cnpj(c['cnpj'])}), "
                                        f"não da entidade analisada ({_fmt_cnpj(cnpj_esp)}). Não foi usado.",
                                        c["ev"].get("cnpj"), "Enviar o cartão CNPJ da própria entidade."))
            continue
        ident, motivo = _identidade(d, cnpj_esp, nomes_esp)
        d.identidade = ident
        if ident == "outra":
            d.status = "outra_entidade"
            achados.append(R.achado("DOC-01", "documentos", "Peça de outra entidade", R.PENDENCIA,
                                    f"{d.arquivo} ({TIPOS_LEGIVEIS.get(d.tipo)}) parece ser de outra entidade "
                                    f"({motivo}), não de {nome_ref or _fmt_cnpj(cnpj_esp)}. Não foi usado na análise.",
                                    _ev_cnpj(d), f"Enviar {'a' if d.tipo == 'ata' else 'o'} "
                                    f"{TIPOS_LEGIVEIS.get(d.tipo, 'documento').lower()} da própria entidade."))
        elif ident == "nao_confirmada":
            achados.append(R.achado("DOC-01", "documentos", "Entidade não confirmada no documento", R.ATENCAO,
                                    f"{d.arquivo}: não encontrei o CNPJ nem o nome completo da entidade ({motivo}).",
                                    d.ev(0, 0, 260), "Confirmar visualmente que o documento é da entidade."))
        if d.grupo and d.tipo and d.grupo != d.tipo and d.tipo in ("estatuto", "ata", "cartao_cnpj"):
            achados.append(R.achado("DOC-02", "documentos", "Peça enviada no campo errado", R.INFO,
                                    f"{d.arquivo} foi enviado como {TIPOS_LEGIVEIS.get(d.grupo)}, mas é "
                                    f"{TIPOS_LEGIVEIS.get(d.tipo)} — analisado como {TIPOS_LEGIVEIS.get(d.tipo)}.",
                                    d.ev(0, 0, 200)))

    # 3) escolher as peças vigentes
    cart_doc = next((d for d in cartoes if d.status == "usado"), None)
    cart = carts[id(cart_doc)] if cart_doc else None
    ests = [(d, X.estatuto(d)) for d in documentos if d.tipo == "estatuto" and d.status == "usado"]

    def _chave_est(par):
        dados = par[1]["registro"]["dados"]
        dr = dados.get("data_registro") or dados.get("data_protocolo")
        dd = D.fazer(*dr.split("/")) if dr else None
        return (bool(par[1]["registro"]["forte"]), dd or dt.date(1900, 1, 1))
    ests.sort(key=_chave_est, reverse=True)
    doc_est, est = ests[0] if ests else (None, None)
    for d, _ in ests[1:]:
        d.status = "superado"

    atas = [(d, X.ata(d)) for d in documentos if d.tipo == "ata" and d.status == "usado"]
    posse = [p for p in atas if p[1]["tipo"] in ("posse", "eleicao")]
    if posse:
        def _ini(p):
            ms = [c["inicio"] for c in p[1]["mandatos"]]
            return max(ms) if ms else (p[1]["data_assembleia"] or dt.date(1900, 1, 1))
        posse.sort(key=_ini, reverse=True)
        doc_ata, ata = posse[0]
    elif atas:
        doc_ata, ata = atas[0]
    else:
        doc_ata, ata = None, None
    atas_extra = [(a, d) for d, a in atas if d is not doc_ata]
    for _, d in atas_extra:
        d.status = "apoio"

    # 4) regras
    achados += R.bloco_habilitacao(cart, cart_doc, est, doc_est, api, ref, cfg)
    achados += R.bloco_registro(est, doc_est, ests[1:], ata, doc_ata, atas_extra, ref, cfg)
    achados += R.bloco_representante(est, doc_est, ata, doc_ata, ref)
    achados = [a for a in achados if a]

    # 5) documentos
    for d in documentos:
        recebidos.append({"arquivo": d.arquivo, "doc_type": d.tipo, "tipo": TIPOS_LEGIVEIS.get(d.tipo, "—"),
                          "status": d.status, "leitura": {"ocr": "OCR", "misto": "digital + OCR", "digital": "digital",
                                      "escaneada": "sem texto", "erro": "erro"}.get(
                              d.origem or "", "OCR" if d.lido_por_ocr else "digital"),
                          "paginas": d.n_paginas})
    faltantes = []
    if not cart_doc:
        faltantes.append("Cartão CNPJ da entidade")
    if not doc_est:
        faltantes.append("Estatuto social registrado da entidade")
    if not doc_ata:
        faltantes.append("Ata de eleição/posse da diretoria vigente, registrada")

    resultado = _resultado(achados, faltantes)
    ajustes = _ajustes(achados, faltantes)
    entidade = (cart["razao_social"] if cart else None) or nome_inscricao or (est and est["denominacao"]) or "—"
    return {
        "entidade": entidade, "cnpj": _fmt_cnpj(cnpj_esp) if cnpj_esp else "—", "projeto": projeto,
        "data_referencia": D.br(ref), "resultado": resultado,
        "frase": _frase(resultado, achados, faltantes),
        "documentos_recebidos": recebidos, "documentos_faltantes": faltantes,
        "achados": sorted(achados, key=lambda a: ([b for b, _ in BLOCOS].index(a["bloco"]), a["regra_id"])),
        "ajustes": ajustes, "confirmar_no_edital": CONFIRMAR_EDITAL,
        "nao_solicitados": NAO_SOLICITADAS, "conferencia_visual": VISUAL,
        "_pecas": {"cartao": cart, "estatuto": est, "ata": ata, "doc_est": doc_est, "doc_ata": doc_ata},
    }


def _resultado(achados, faltantes):
    st = {a["status"] for a in achados}
    if R.BLOQUEANTE in st or faltantes:
        return "NAO_APTO"
    if R.PENDENCIA in st or R.ATENCAO in st:
        return "APTO_COM_AJUSTES"
    return "APTO"


RESULTADO_TXT = {"APTO": "APTO", "APTO_COM_AJUSTES": "APTO COM AJUSTES", "NAO_APTO": "NÃO APTO"}


def _frase(res, achados, faltantes):
    nb = sum(a["status"] == R.BLOQUEANTE for a in achados)
    np_ = sum(a["status"] == R.PENDENCIA for a in achados)
    na = sum(a["status"] in (R.ATENCAO, R.ATENCAO_MENOR) for a in achados)
    partes = []
    if nb:
        partes.append(f"{nb} bloqueante{'s' if nb > 1 else ''}")
    if faltantes:
        partes.append(f"{len(faltantes)} peça{'s' if len(faltantes) > 1 else ''} obrigatória{'s' if len(faltantes) > 1 else ''} faltando")
    if np_:
        partes.append(f"{np_} pendência{'s' if np_ > 1 else ''}")
    if na:
        partes.append(f"{na} ponto{'s' if na > 1 else ''} de atenção")
    if res == "NAO_APTO":
        return "Há impedimento: " + ", ".join(partes) + "."
    if res == "APTO_COM_AJUSTES":
        return "Sem bloqueante; " + ", ".join(partes) + "."
    return "Sem bloqueante nem pendência" + (f"; {na} observação(ões) menores." if na else ".")


def _ajustes(achados, faltantes):
    itens = [(R.PRIORIDADE[R.BLOQUEANTE], f"Enviar: {f}.", "—") for f in faltantes]
    for a in achados:
        if a["recomendacao"] and a["status"] not in (R.OK,):
            itens.append((R.PRIORIDADE[a["status"]], a["recomendacao"], a["regra_id"]))
    itens.sort(key=lambda x: x[0])
    vistos, saida = set(), []
    for pr, txt, rid in itens:
        if txt in vistos:
            continue
        vistos.add(txt)
        st = next(k for k, v in R.PRIORIDADE.items() if v == pr)
        saida.append({"status": st, "regra_id": rid, "texto": txt})
    return saida


# ------------------------------------------------------------------ saídas

def _ev_txt(ev):
    pag = f", pág. {ev['pagina']}" if ev.get("pagina") else ""
    return f"{ev['arquivo']}{pag}: “{ev['trecho'][:160]}”"


def markdown(p):
    L = [f"## Conferência documental — {p['entidade']}" + (f" / {p['projeto']}" if p.get("projeto") else ""),
         f"CNPJ {p['cnpj']} · Data: {p['data_referencia']} · Legenda: [OK] conforme · [atenção] atenção · [pendência] pendência",
         f"**Resultado: {RESULTADO_TXT[p['resultado']]}** — {p['frase']}", ""]
    L.append("### Documentos recebidos")
    L.append("| Arquivo | Tipo | Leitura | Situação |")
    L.append("|---|---|---|---|")
    for d in p["documentos_recebidos"]:
        L.append(f"| {d['arquivo']} | {d['tipo']} | {d['leitura']} · {d['paginas']} pág. | {STATUS_DOC.get(d['status'], d['status'])} |")
    if p["documentos_faltantes"]:
        L.append("")
        L.append("**Peças faltantes:** " + "; ".join(p["documentos_faltantes"]) + ".")
    for chave, titulo in BLOCOS:
        linhas = [a for a in p["achados"] if a["bloco"] == chave]
        if not linhas:
            continue
        if chave == "documentos":
            L.append("")
            L.append("**Observações sobre as peças**")
        else:
            L.append("")
            L.append(f"### {titulo}")
        L.append("| Item | Constatação | Status |")
        L.append("|---|---|---|")
        for a in linhas:
            L.append(f"| {a['regra_id']} · {a['item']} | {a['constatacao']}<br><sub>Evidência: {_ev_txt(a['evidencia'])}</sub> "
                     f"| {R.ICONE[a['status']]} {R.ROTULO[a['status']]} |")
    L.append("")
    L.append("### Declarações × modelos")
    L.append("Não avaliado nesta fase: " + "; ".join(p["nao_solicitados"]) + ".")
    L.append("")
    L.append("## Ajustes recomendados (por prioridade)")
    if p["ajustes"]:
        for i, a in enumerate(p["ajustes"], 1):
            L.append(f"{i}. {R.ICONE[a['status']]} {a['texto']} ({a['regra_id']})")
    else:
        L.append("Nenhum ajuste.")
    L.append("")
    L.append("**Confirmar no edital:** " + "; ".join(p["confirmar_no_edital"]) + ".")
    L.append("")
    L.append("**Conferência visual recomendada:** " + "; ".join(p["conferencia_visual"]) + ".")
    return "\n".join(L)


def json_publico(p):
    """Parecer sem objetos internos (para baixar / guardar)."""
    return {k: v for k, v in p.items() if not k.startswith("_")}


def sugestoes_criterios(p):
    """Pré-marcação dos 8 itens da tela 4 a partir dos achados.
    {chave: {"sugestao": True/False/None, "cor", "detalhe", "evidencia"}}"""
    por = {}
    for a in p["achados"]:
        por.setdefault(a["regra_id"], []).append(a)

    def pior(rid):
        lst = por.get(rid, [])
        return min(lst, key=lambda a: R.PRIORIDADE[a["status"]]) if lst else None

    def s(sug, cor, a=None, detalhe=None):
        return {"sugestao": sug, "cor": cor, "detalhe": detalhe or (a["constatacao"] if a else ""),
                "evidencia": (a["evidencia"]["trecho"][:160] if a else ""),
                "regra": a["regra_id"] if a else ""}

    def de(rid, ok_cor="verde"):
        a = pior(rid)
        if not a:
            return s(None, "amarelo", detalhe="Sem documento/leitura para esta regra — confira manualmente.")
        if a["status"] == R.OK:
            return s(True, ok_cor, a)
        if a["status"] in (R.ATENCAO, R.ATENCAO_MENOR, R.INFO):
            return s(None, "amarelo", a)
        return s(False, "vermelho", a)

    out = {}
    pc = p["_pecas"]
    cart = pc["cartao"]
    if cart:
        out["cnpj_receita"] = s(True, "verde", detalhe="Comprovante oficial da Receita Federal identificado.") \
            if cart.get("oficial") else s(None, "amarelo", detalhe="Não parece o comprovante oficial — confira.")
    else:
        out["cnpj_receita"] = s(None, "amarelo", detalhe="Cartão CNPJ da entidade não recebido.")
    h1, h2 = pior("HAB-01"), pior("HAB-02")
    if h1 and h2 and h1["status"] == R.OK and h2["status"] == R.OK:
        out["cnpj_1ano"] = s(True, "verde", h1)
    elif (h1 and h1["status"] == R.BLOQUEANTE) or (h2 and h2["status"] == R.BLOQUEANTE):
        out["cnpj_1ano"] = s(False, "vermelho", h1 if h1 and h1["status"] == R.BLOQUEANTE else h2)
    else:
        out["cnpj_1ano"] = de("HAB-01")
    out["est_finalidade"] = de("HAB-05", ok_cor="amarelo")
    est, doc_est = pc["estatuto"], pc["doc_est"]
    if est:
        nums = [a["num"] for a in est["artigos"]]
        buracos = [n for n in range(1, max(nums) + 1) if n not in nums] if nums else []
        if nums and not buracos and nums == sorted(nums):
            out["est_ordem"] = s(True, "verde", detalhe=f"Artigos 1 a {max(nums)} em sequência.")
        elif doc_est.lido_por_ocr:
            out["est_ordem"] = s(None, "amarelo", detalhe="Documento escaneado: a numeração dos artigos não "
                                 "pôde ser confirmada pela leitura automática — confira visualmente.")
        else:
            out["est_ordem"] = s(False, "vermelho", detalhe="Numeração com falhas: faltam os artigos "
                                 + ", ".join(map(str, buracos[:10])) + ".")
    else:
        out["est_ordem"] = s(None, "amarelo", detalhe="Estatuto da entidade não recebido.")
    out["est_cartorio"] = de("REG-01")
    r6, r7 = pior("REG-06"), pior("REG-07")
    if r6 and r6["status"] == R.OK:
        out["ata_vigencia"] = s(True, "amarelo", r7) if r7 else s(True, "verde", r6)
    elif r6 and r6["status"] == R.BLOQUEANTE:
        out["ata_vigencia"] = s(False, "vermelho", r6)
    else:
        r5 = pior("REG-05")
        out["ata_vigencia"] = s(False, "vermelho", r5) if r5 and r5["status"] == R.PENDENCIA and \
            "posse" in r5["item"].lower() else (s(None, "amarelo", r6) if r6 else de("REG-05"))
    out["ata_cartorio"] = de("REG-05")
    ata = pc["ata"]
    if ata and ata["tipo"] in ("posse", "eleicao"):
        rg = ata["registro"]
        if rg["dados"].get("selo") or rg["dados"].get("registro_digital") or rg["forte"]:
            out["ata_selo"] = s(True, "verde", detalhe="Selo/etiqueta de registro: " + (R._fmt_registro(rg["dados"]) or "identificado") + ".")
        elif rg["indicio"]:
            out["ata_selo"] = s(None, "amarelo", detalhe=f"Carimbo/selo na pág. {R._pags(rg['indicio'])}, ilegível na leitura — confira.")
        else:
            out["ata_selo"] = s(False, "vermelho", detalhe="Não localizei selo/carimbo/folha de registro.")
    else:
        out["ata_selo"] = s(None, "amarelo", detalhe="Ata de posse da diretoria não recebida.")
    return out
