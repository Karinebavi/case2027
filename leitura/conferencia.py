# -*- coding: utf-8 -*-
"""
Conferência assistida dos documentos da Fase 2.

Recebe o PDF que o mentor subiu, lê, valida e devolve uma SUGESTÃO por critério
do edital — sempre com a cor de confiança e o trecho do documento que motivou a
sugestão. O mentor confirma (ou corrige) o que ficar amarelo/vermelho. Nada é
decidido sozinho: a sugestão só pré-preenche; a palavra final é do mentor.

As chaves dos critérios são as mesmas de telas/documental.py (CRITERIOS).
"""
from leitura import texto as _texto
from leitura import campos as _campos
from leitura import cnpj_online as _cnpj

ESPORTE = ["esporte", "esportiv", "desporto", "modalidade esportiva",
           "pratica de esporte", "pratica desportiva", "atividade fisica",
           "atividades fisicas"]
CARTORIO = ["cartorio", "tabelionato", "registro civil", "registro de titulos",
            "registro de pessoas juridicas", "registrado em cartorio", "registro"]
SELO = ["selo", "carimbo", "folha de registro", "protocolo", "averbacao",
        "reconheco", "reconhecimento de firma"]
RECEITA_TITULO = "comprovante de inscricao e de situacao cadastral"
RECEITA_ORGAO = ["receita federal", "secretaria da receita", "ministerio da fazenda"]

_TIPO_ESPERADO = {"Cartão CNPJ": "cartao_cnpj", "Estatuto": "estatuto", "Ata": "ata"}


def _c(sugestao, cor, evidencia="", detalhe=""):
    return {"sugestao": sugestao, "cor": cor, "evidencia": evidencia, "detalhe": detalhe}


def _ativa(situacao):
    s = str(situacao or "").upper()
    return "ATIVA" in s or s.strip() in ("2", "02")


def conferir(grupo, arquivo, cnpj_inscricao):
    """
    grupo: "Cartão CNPJ" | "Estatuto" | "Ata"
    arquivo: PDF (bytes / UploadedFile)
    cnpj_inscricao: CNPJ da inscrição (dígitos) — usado para cruzar e consultar
    """
    lido = _texto.extrair(arquivo)
    texto = lido["texto"]
    plano = _campos.sem_acento(texto)

    tipo, tipo_cor = _campos.classificar_tipo(texto) if texto else (None, "vermelho")
    esperado = _TIPO_ESPERADO.get(grupo)
    avisos = []
    if lido["origem"] == "erro":
        avisos.append("Não consegui abrir o PDF (arquivo corrompido ou não é um PDF válido).")
    elif lido["escaneado"]:
        if lido["ocr_disp"]:
            avisos.append("Documento escaneado e o OCR não conseguiu ler — confira manualmente.")
        else:
            avisos.append("Documento sem texto (escaneado). Instale o OCR (Tesseract) ou confira manualmente.")
    if tipo and esperado and tipo != esperado:
        legivel = {"cartao_cnpj": "Cartão CNPJ", "estatuto": "Estatuto", "ata": "Ata"}
        avisos.append(f"O arquivo parece ser um {legivel.get(tipo, tipo)}, não um {grupo}.")

    doc = {
        "tipo": tipo, "tipo_cor": tipo_cor, "origem": lido["origem"],
        "conf": lido["conf"], "escaneado": lido["escaneado"],
        "ocr_usado": lido["ocr_usado"], "ocr_disp": lido["ocr_disp"],
        "cnpj_doc": None, "cnpj_bate": None, "api": None, "avisos": avisos,
    }

    if grupo == "Cartão CNPJ":
        criterios = _cartao(plano, texto, cnpj_inscricao, doc)
    elif grupo == "Estatuto":
        criterios = _estatuto(plano, texto, doc)
    elif grupo == "Ata":
        criterios = _ata(plano, texto, doc)
    else:
        criterios = {}

    return {"doc": doc, "criterios": criterios}


def _sem_texto(chaves, escaneado):
    msg = "Sem texto para ler — confira manualmente." if escaneado else "Não foi possível ler o documento."
    return {k: _c(None, "amarelo", "", msg) for k in chaves}


def _cartao(plano, texto, cnpj_inscricao, doc):
    if not texto:
        return _sem_texto(["cnpj_receita", "cnpj_1ano"], doc["escaneado"])

    cnpj_doc, _cand = _campos.achar_cnpj(texto)
    doc["cnpj_doc"] = cnpj_doc
    ins = _campos.so_digitos(cnpj_inscricao)
    if cnpj_doc and ins:
        doc["cnpj_bate"] = (cnpj_doc == ins)
        if doc["cnpj_bate"] is False:
            doc["avisos"].append("O CNPJ do documento diverge do CNPJ da inscrição.")

    # cnpj_receita: título do comprovante + órgão emissor
    tem_titulo = RECEITA_TITULO in plano
    tem_orgao = any(o in plano for o in RECEITA_ORGAO)
    if tem_titulo and tem_orgao:
        c_receita = _c(True, "verde", "", "Título do comprovante + Receita Federal identificados.")
    elif tem_titulo or tem_orgao:
        c_receita = _c(True, "amarelo", "", "Parece da Receita, mas confirme (faltou título ou órgão).")
    else:
        c_receita = _c(False, "vermelho", "", "Não parece o comprovante oficial da Receita Federal.")

    # cnpj_1ano: pela BrasilAPI (data de abertura + situação)
    api = _cnpj.consultar(ins) if ins else None
    doc["api"] = api
    if api:
        anos = _cnpj.anos_desde(api.get("data_abertura"))
        det = (f"Abertura {api.get('data_abertura') or '—'} · "
               f"{anos if anos is not None else '?'} anos · "
               f"situação {api.get('situacao') or '—'} · fonte {api.get('fonte')}")
        if anos is not None and anos >= 1 and _ativa(api.get("situacao")):
            c_1ano = _c(True, "verde", "", det)
        elif anos is not None and anos < 1:
            c_1ano = _c(False, "vermelho", "", "Menos de 1 ano de funcionamento. " + det)
        elif not _ativa(api.get("situacao")):
            c_1ano = _c(False, "vermelho", "", "CNPJ não está ATIVO. " + det)
        else:
            c_1ano = _c(None, "amarelo", "", det)
    else:
        data_doc, cor = _campos.data_apos_rotulo(texto, ["Data de Abertura", "ABERTURA"])
        anos = _cnpj.anos_desde("-".join(reversed(data_doc.split("/"))) if data_doc else None)
        if anos is not None:
            ok = anos >= 1
            c_1ano = _c(ok, "amarelo",
                        f"Data de abertura no documento: {data_doc}",
                        f"Sem internet: li a data no PDF · {anos} anos. Confirme.")
        else:
            c_1ano = _c(None, "amarelo", "", "Sem internet e sem data legível — confira manualmente.")

    return {"cnpj_receita": c_receita, "cnpj_1ano": c_1ano}


def _estatuto(plano, texto, doc):
    if not texto:
        return _sem_texto(["est_finalidade", "est_ordem", "est_cartorio"], doc["escaneado"])

    achou_esp, ev_esp = _campos.achar_termo(texto, ESPORTE)
    if achou_esp:
        c_fin = _c(True, "amarelo", ev_esp,
                   "Achei termo esportivo. Confirme se é o FIM da entidade (não meio para outro fim).")
    else:
        c_fin = _c(False, "vermelho", "", "Não encontrei finalidade esportiva no texto.")

    c_ordem = _c(None, "amarelo", "", "Conferência manual: numeração dos artigos em ordem.")

    achou_cart, ev_cart = _campos.achar_termo(texto, CARTORIO)
    c_cart = (_c(True, "amarelo", ev_cart, "Confirme o registro em cartório.")
              if achou_cart else _c(False, "vermelho", "", "Não encontrei menção a registro em cartório."))

    return {"est_finalidade": c_fin, "est_ordem": c_ordem, "est_cartorio": c_cart}


def _ata(plano, texto, doc):
    if not texto:
        return _sem_texto(["ata_vigencia", "ata_cartorio", "ata_selo"], doc["escaneado"])

    ds = _campos.datas(texto)
    ev_datas = ("Datas no documento: " + ", ".join(ds[:6])) if ds else ""
    c_vig = _c(None, "amarelo", ev_datas,
               "Confira se o mandato/vigência da diretoria está válido (atenção a prazo vencendo).")

    achou_cart, ev_cart = _campos.achar_termo(texto, CARTORIO)
    c_cart = (_c(True, "amarelo", ev_cart, "Confirme o registro em cartório.")
              if achou_cart else _c(False, "vermelho", "", "Não encontrei menção a registro em cartório."))

    achou_selo, ev_selo = _campos.achar_termo(texto, SELO)
    c_selo = (_c(True, "amarelo", ev_selo, "Confirme o selo/carimbo/folha de registro.")
              if achou_selo else _c(False, "vermelho", "", "Não encontrei selo/carimbo/registro."))

    return {"ata_vigencia": c_vig, "ata_cartorio": c_cart, "ata_selo": c_selo}
