# -*- coding: utf-8 -*-
"""
Regras de checagem da conferência documental (LIE), conforme a
"Especificação de conhecimento — Conferência Documental LIE" (Trilha Gestão).

Blocos: 1 Habilitação (HAB-xx), 2 Registro e diretoria (REG-xx),
3 Representante legal (REP-xx). O bloco 4 (declarações) e o documento de
identidade não fazem parte das peças pedidas no CASE 2027 — ficam listados
como "não solicitados nesta fase".

Princípios aplicados:
  - nunca inventar exigência: o que depende do edital sai com "confirmar no
    edital" (parâmetros em CONFIG_PADRAO);
  - constatação factual: cita data, nº de registro, artigo, página;
  - todo achado tem evidência (arquivo + página + trecho). Sem evidência,
    o achado não é emitido;
  - leitura por OCR não vira "não existe": quando o texto é escaneado, o que
    não foi lido pede conferência visual em vez de reprovar.
"""
import datetime as dt
import re
from difflib import SequenceMatcher

from leitura import datas as D
from leitura.campos import sem_acento
from leitura.documento import Evidencia
from leitura.extratores import cargo_canonico

OK, ATENCAO, ATENCAO_MENOR, PENDENCIA, BLOQUEANTE, INFO = (
    "OK", "ATENCAO", "ATENCAO_MENOR", "PENDENCIA", "BLOQUEANTE", "INFO")
PRIORIDADE = {BLOQUEANTE: 0, PENDENCIA: 1, ATENCAO: 2, ATENCAO_MENOR: 3, INFO: 4, OK: 5}
ICONE = {OK: "[OK]", ATENCAO: "[atenção]", ATENCAO_MENOR: "[atenção]",
         PENDENCIA: "[pendência]", BLOQUEANTE: "[bloqueante]", INFO: "[info]"}
ROTULO = {OK: "Conforme", ATENCAO: "Atenção", ATENCAO_MENOR: "Atenção menor",
          PENDENCIA: "Pendência", BLOQUEANTE: "Bloqueante", INFO: "Informação"}

# Parâmetros que dependem do edital (seção 9 da especificação) — ajustáveis.
CONFIG_PADRAO = {
    "tempo_minimo_anos": 1,
    "recencia_cartao_dias": 30,
    "cartao_muito_antigo_dias": 365,
    "mandato_alerta_meses": 6,
    "fim_execucao_projeto": None,       # date — se informado, REG-07 compara
    # Classes CNAE de atividade esportiva (IBGE 93.1 e 85.91-1). Confirmar no edital.
    "cnaes_esportivas": ["85.91-1-00", "93.11-5-00", "93.12-3-00", "93.13-1-00",
                         "93.19-1-01", "93.19-1-99"],
    "naturezas_osc": {"399-9": "Associação Privada", "306-9": "Fundação Privada",
                      "322-0": "Organização Religiosa"},
}


def achado(regra_id, bloco, item, status, constatacao, evidencias, recomendacao=""):
    evs = [e for e in (evidencias if isinstance(evidencias, list) else [evidencias]) if e]
    if not evs:
        return None  # sem evidência, não emite (princípio da especificação)
    return {"regra_id": regra_id, "bloco": bloco, "item": item, "status": status,
            "constatacao": constatacao, "evidencia": evs[0], "evidencias": evs,
            "recomendacao": recomendacao}


def _ev_api(api, data_ref):
    return Evidencia("Consulta pública CNPJ (" + (api.get("fonte") or "Receita") + ")", None,
                     f"situação {api.get('situacao') or '—'} · abertura {api.get('data_abertura') or '—'} · "
                     f"consultado em {D.br(data_ref)}")


def _anos_meses(ini, fim):
    meses = (fim.year - ini.year) * 12 + (fim.month - ini.month) - (fim.day < ini.day)
    a, m = divmod(max(meses, 0), 12)
    txt_m = f"{m} {'meses' if m != 1 else 'mês'}"
    if not a:
        return txt_m if m else f"{max((fim - ini).days, 0)} dias"
    return f"{a} ano{'s' if a != 1 else ''}" + (f" e {txt_m}" if m else "")


def _pags(lst):
    if not lst:
        return "—"
    lst = sorted(set(lst))
    faixas, ini, ant = [], lst[0], lst[0]
    for n in lst[1:] + [None]:
        if n is not None and n == ant + 1:
            ant = n
            continue
        faixas.append(f"{ini}" if ini == ant else f"{ini}–{ant}")
        if n is not None:
            ini = ant = n
    return ", ".join(faixas)


def _fmt_registro(dados):
    partes = []
    if dados.get("registro_numero"):
        partes.append(f"registro nº {dados['registro_numero']}")
    if dados.get("averbacao"):
        partes.append(dados["averbacao"])
    if dados.get("matricula"):
        partes.append(f"matrícula nº {dados['matricula']}")
    if dados.get("livro"):
        partes.append(f"Livro {dados['livro']}")
    if dados.get("protocolo"):
        partes.append(f"protocolo nº {dados['protocolo']}" +
                      (f" em {dados['data_protocolo']}" if dados.get("data_protocolo") else ""))
    if dados.get("data_registro"):
        partes.append(f"data {dados['data_registro']}")
    if dados.get("selo"):
        partes.append(f"selo {dados['selo']}")
    if dados.get("registro_digital"):
        partes.append("registro e assinatura digital do cartório")
    if dados.get("cartorio"):
        partes.append(dados["cartorio"])
    return "; ".join(partes)


# =========================================================== BLOCO 1 — HABILITAÇÃO

def bloco_habilitacao(cart, doc_cart, est, doc_est, api, ref, cfg):
    B = "habilitacao"
    out = []

    # HAB-01 — tempo de funcionamento
    fontes, evs = [], []
    abertura = cart["data_abertura"] if cart else None
    if abertura:
        fontes.append(f"CNPJ aberto em {D.br(abertura)} (Cartão CNPJ)")
        evs.append(cart["ev"].get("abertura"))
    elif api and api.get("data_abertura"):
        try:
            abertura = dt.date.fromisoformat(str(api["data_abertura"])[:10])
            fontes.append(f"CNPJ aberto em {D.br(abertura)} (consulta pública)")
            evs.append(_ev_api(api, ref))
        except ValueError:
            pass
    fundacao = est["data_fundacao"] if est else None
    if fundacao:
        fontes.append(f"fundação em {D.br(fundacao)} (Estatuto)")
        evs.append(est["ev"].get("fundacao"))
    base = abertura or fundacao
    if base:
        anos = (ref - base).days / 365.25
        st = OK if anos > cfg["tempo_minimo_anos"] else BLOQUEANTE
        out.append(achado("HAB-01", B, "Tempo de funcionamento", st,
                          "; ".join(fontes) + f" — {_anos_meses(base, ref)} até {D.br(ref)}. "
                          f"Critério: mais de {cfg['tempo_minimo_anos']} ano (confirmar no edital).",
                          evs, "" if st == OK else "Entidade não atinge o tempo mínimo de funcionamento."))

    # HAB-02 — situação cadastral
    if cart and cart["situacao"]:
        ativa = "ATIVA" in cart["situacao"].upper()
        txt = f"Situação cadastral {cart['situacao']} desde {cart['data_situacao']} (Cartão CNPJ)."
        evs = [cart["ev"].get("situacao")]
        if api and api.get("situacao"):
            txt += f" Consulta pública hoje: {api['situacao']}."
            evs.append(_ev_api(api, ref))
            ativa = ativa and "ATIVA" in api["situacao"].upper()
        out.append(achado("HAB-02", B, "Situação cadastral", OK if ativa else BLOQUEANTE, txt, evs,
                          "" if ativa else "Regularizar a situação cadastral na Receita Federal."))
    elif api and api.get("situacao"):
        ativa = "ATIVA" in api["situacao"].upper()
        out.append(achado("HAB-02", B, "Situação cadastral", OK if ativa else BLOQUEANTE,
                          f"Consulta pública: situação {api['situacao']} (cartão CNPJ não enviado).",
                          _ev_api(api, ref), "" if ativa else "Regularizar a situação cadastral."))

    # HAB-03 — recência do cartão
    if cart:
        if cart["data_emissao"]:
            dias = (ref - cart["data_emissao"]).days
            txt = f"Cartão emitido em {D.br(cart['data_emissao'])} — há {dias} dias."
            if dias <= cfg["recencia_cartao_dias"]:
                st, rec = OK, ""
            elif dias <= cfg["cartao_muito_antigo_dias"]:
                st, rec = ATENCAO, "Emitir o cartão CNPJ novamente (recomendado até 30 dias; confirmar no edital)."
            else:
                st, rec = PENDENCIA, "Cartão com mais de 1 ano: emitir novamente no site da Receita Federal."
            divergente = []
            end = cart.get("endereco") or {}
            if api and api.get("cep") and end.get("cep") and api["cep"] != end["cep"]:
                divergente.append(f"CEP no cartão {end['cep']} × hoje na Receita {api['cep']}")
            if api and api.get("situacao") and cart.get("situacao") and \
                    api["situacao"].upper() not in cart["situacao"].upper():
                divergente.append(f"situação no cartão {cart['situacao']} × hoje {api['situacao']}")
            evs = [cart["ev"].get("emissao")]
            if divergente:
                st = PENDENCIA
                txt += " Dados do cartão diferem da Receita hoje: " + "; ".join(divergente) + "."
                rec = "Emitir o cartão CNPJ atualizado."
                evs.append(_ev_api(api, ref))
            out.append(achado("HAB-03", B, "Recência do cartão CNPJ", st, txt, evs, rec))
        else:
            out.append(achado("HAB-03", B, "Recência do cartão CNPJ", ATENCAO,
                              "Não há a linha 'Emitido no dia…' — pode ser um print parcial da tela do CNPJ.",
                              Evidencia(doc_cart.arquivo, 1, doc_cart.texto[:200]),
                              "Baixar o comprovante completo em PDF no site da Receita Federal."))

    # HAB-04 — natureza jurídica
    if cart and cart["natureza_juridica"]:
        cod, desc = cart["natureza_juridica"]
        st = OK if cod in cfg["naturezas_osc"] else ATENCAO
        out.append(achado("HAB-04", B, "Natureza jurídica", st, f"{cod} – {desc}.", cart["ev"].get("natureza"),
                          "" if st == OK else "Confirmar se a natureza jurídica é compatível com OSC no edital."))

    # HAB-05 — finalidade esportiva
    if est:
        fins = [f for f in est["finalidade"] if f["em_fins"]]
        if fins:
            arts = sorted({f["artigo"] for f in fins}, key=lambda a: [int(x) for x in re.findall(r"\d+", a)][:1])
            out.append(achado("HAB-05", B, "Finalidade esportiva", OK,
                              "Esporte previsto no objeto/finalidades nos artigos: " + "; ".join(arts) +
                              ". Confirme que o esporte é FIM da entidade (não só meio para outro fim).",
                              [f["ev"] for f in fins[:5]]))
        elif est["finalidade"]:
            f = est["finalidade"][0]
            out.append(achado("HAB-05", B, "Finalidade esportiva", ATENCAO,
                              f"Termo esportivo aparece em {f['artigo']}, fora do artigo de finalidades.",
                              f["ev"], "Confirmar se o estatuto traz o esporte como finalidade."))
        elif not doc_est.sem_texto:
            out.append(achado("HAB-05", B, "Finalidade esportiva", PENDENCIA,
                              "Não localizei esporte/desporto/atividade física no estatuto" +
                              (" (lido por OCR — confira visualmente)." if doc_est.lido_por_ocr else "."),
                              Evidencia(doc_est.arquivo, 1, doc_est.texto[:200]),
                              "Incluir finalidade esportiva no estatuto (reforma estatutária)."))
        if est.get("restrita_associados"):
            r = est["restrita_associados"]
            out.append(achado("HAB-05", B, "Finalidade restrita aos associados", INFO,
                              f"{r['artigo']}: a finalidade cita atividades 'entre seus associados'.",
                              r["ev"], "Garantir acesso público no desenho do projeto."))

    # (HAB-06 CNAE × finalidade — removido a pedido: não é exigência desta fase.)

    # HAB-07 — endereço CNPJ × estatuto
    if cart and est and est.get("sede") and cart.get("endereco"):
        out.append(_hab07(cart, est, B))
    return [a for a in out if a]


def _norm_rua(txt):
    t = sem_acento(txt or "")
    t = re.sub(r"\b(rua|r|avenida|av|estrada|est|travessa|tv|alameda|al|praca|pc|rodovia|rod|n|no)\b\.?", " ", t)
    t = re.sub(r"\b(de|da|do|dos|das)\b", " ", t)
    return " ".join(re.findall(r"[a-z]+", t))


def _hab07(cart, est, B):
    ce, se = cart["endereco"], est["sede"]
    r1, r2 = _norm_rua(ce.get("logradouro")), _norm_rua(se.get("logradouro"))
    parecido = bool(r1 and r2) and (SequenceMatcher(None, r1, r2).ratio() >= 0.72 or r2 in r1 or r1 in r2)
    num_ok = (ce.get("numero") or "").lstrip("0") == (se.get("numero") or "").lstrip("0") \
        if ce.get("numero") and se.get("numero") else None
    cep_ok = (ce.get("cep") == se.get("cep")) if ce.get("cep") and se.get("cep") else None
    txt = (f"Cartão CNPJ: {ce.get('linha') or ce.get('logradouro')}, CEP {ce.get('cep') or '—'} · "
           f"Estatuto ({est['ev'].get('sede_art') or 'sede'}): {se.get('logradouro')}"
           f"{', nº ' + se['numero'] if se.get('numero') else ''}{', CEP ' + se['cep'] if se.get('cep') else ''}.")
    evs = [cart["ev"].get("endereco"), est["ev"].get("sede")]
    if parecido and num_ok is not False and cep_ok is not False:
        return achado("HAB-07", B, "Endereço CNPJ × estatuto", OK, txt, evs)
    if parecido and num_ok is not False and cep_ok is False:
        return achado("HAB-07", B, "Endereço CNPJ × estatuto", ATENCAO_MENOR, txt + " Só o CEP diverge.", evs,
                      "Padronizar o CEP pelos Correios (Receita e estatuto).")
    return achado("HAB-07", B, "Endereço CNPJ × estatuto", ATENCAO, txt + " Endereços divergem.", evs,
                  "Atualizar o endereço na Receita Federal (ou no estatuto) e emitir o cartão novamente.")


# ======================================================= BLOCO 2 — REGISTRO E DIRETORIA

def _registro_status(reg, doc, peca, rid, B):
    d = reg["dados"]
    if reg["forte"]:
        return achado(rid, B, f"{peca} registrad{'a' if peca == 'Ata' else 'o'}", OK,
                      "Registrado: " + (_fmt_registro(d) or "marca de registro do cartório") +
                      f" (pág. {_pags(reg['forte'][:1])}).", reg["ev"])
    if reg["indicio"]:
        return achado(rid, B, f"{peca} registrad{'a' if peca == 'Ata' else 'o'}", ATENCAO,
                      f"Há carimbo/selo de cartório na pág. {_pags(reg['indicio'])}, mas nº, livro e data "
                      "não ficaram legíveis na leitura automática (documento escaneado).",
                      reg["ev_indicio"], "Conferir visualmente o carimbo e anotar nº do registro, livro e data.")
    if doc.lido_por_ocr or doc.sem_texto:
        return achado(rid, B, f"{peca} registrad{'a' if peca == 'Ata' else 'o'}", PENDENCIA,
                      "Não localizei o carimbo/selo de registro na leitura automática (documento escaneado). "
                      "O registro costuma ficar no VERSO ou numa página à parte que muitas vezes não é enviada.",
                      Evidencia(doc.arquivo, doc.n_paginas, doc.paginas[-1]["texto"][-200:]),
                      f"Conferir o verso e as demais folhas; se realmente não houver, pedir a versão registrada/averbada d{'a' if peca == 'Ata' else 'o'} {peca.lower()}.")
    return achado(rid, B, f"{peca} registrad{'a' if peca == 'Ata' else 'o'}", PENDENCIA,
                  "Não localizei registro/averbação de cartório no documento. O selo de registro costuma "
                  "ficar no VERSO ou numa folha à parte que muitas vezes não é enviada junto.",
                  Evidencia(doc.arquivo, doc.n_paginas, doc.paginas[-1]["texto"][-200:]),
                  f"Conferir o verso e as demais folhas; se realmente não houver, pedir a versão registrada/averbada d{'a' if peca == 'Ata' else 'o'} {peca.lower()}.")


def _mandato(ata, est, ref):
    """Escolhe o mandato da diretoria vigente. Devolve dict ou None."""
    cands = ata["mandatos"]
    anos_est = None
    ev_est = None
    if est:
        prefer = [m for m in est["mandatos"] if m["orgao"] in ("Diretoria", "Conselho Diretor")] or \
            [m for m in est["mandatos"] if m["orgao"] in ("Presidente", "—")]
        if prefer:
            anos_est, ev_est = prefer[0]["anos"], prefer[0]
    for fonte in ("explicito", "anos"):
        cs = [c for c in cands if c["fonte"] == fonte]
        if cs:
            c = max(cs, key=lambda c: c["inicio"])
            return {**c, "anos_estatuto": anos_est, "mandato_est": ev_est}
    ini = [c for c in cands if c["fonte"] == "inicio"]
    base = max(ini, key=lambda c: c["inicio"]) if ini else None
    if not base and ata["data_assembleia"]:
        base = {"inicio": ata["data_assembleia"], "fim": None, "fonte": "assembleia", "ev": ata["ev"].get("data")}
    if base and anos_est:
        return {**base, "fim": D.somar_anos(base["inicio"], anos_est), "fonte": "estatuto",
                "anos_estatuto": anos_est, "mandato_est": ev_est}
    if base:
        return {**base, "anos_estatuto": None, "mandato_est": None}
    return None


def _rotulo_ata(ata):
    if ata["tipo"] == "posse" and ata["eleicao"] and ata["data_assembleia"]:
        return f"ata de eleição de {D.br(ata['data_assembleia'])} e posse"
    t = {"posse": "ata de posse", "eleicao": "ata de eleição", "alteracao_estatutaria": "ata de alteração estatutária",
         "fundacao": "ata de fundação"}.get(ata["tipo"], "ata")
    return t + (f" de {D.br(ata['data_assembleia'])}" if ata["data_assembleia"] else "")


def bloco_registro(est, doc_est, outros_est, ata, doc_ata, atas_extra, ref, cfg):
    B = "registro"
    out = []
    if est:
        reg = est["registro"]
        out.append(_registro_status(reg, doc_est, "Estatuto", "REG-01", B))
        # REG-02 — versão vigente
        if outros_est:
            out.append(achado("REG-02", B, "Estatuto vigente identificado", ATENCAO_MENOR,
                              f"Recebidas {len(outros_est) + 1} versões do estatuto. Vigente: {doc_est.arquivo} "
                              f"({_fmt_registro(reg['dados']) or 'registro mais recente'}); superada(s): "
                              + ", ".join(d.arquivo for d, _ in outros_est) + ".",
                              [reg["ev"] or Evidencia(doc_est.arquivo, 1, doc_est.texto[:160])],
                              "Subir no sistema só a versão vigente."))
        fls = reg["fls"]
        if fls and any(b[1] < a[1] for a, b in zip(fls, fls[1:])):
            out.append(achado("REG-02", B, "Mais de um documento no mesmo PDF", ATENCAO_MENOR,
                              "O contador de folhas reinicia no meio do arquivo (" +
                              ", ".join(f"pág. {p}: fl. {x}/{y}" for p, x, y in fls[:6]) + ").",
                              Evidencia(doc_est.arquivo, fls[0][0], f"fl. {fls[0][1]}/{fls[0][2]}"),
                              "Separar e subir só o estatuto vigente (pedir o PDF isolado ao cartório se o "
                              "recorte invalidar a assinatura digital)."))
        if est.get("reforma"):
            out.append(achado("REG-02", B, "Versão do estatuto", INFO,
                              f"Documento identificado como “{est['reforma']['texto'].strip()}”.", est["reforma"]["ev"]))
        # REG-03 — registro em todas as folhas
        n = doc_est.n_paginas
        marcadas = sorted(set(reg["forte"]) | set(reg["indicio"]))
        if len(marcadas) >= n:
            out.append(achado("REG-03", B, "Registro em todas as folhas", OK,
                              f"Marca de registro identificada nas {n} folhas.", reg["ev"] or reg["ev_indicio"]))
        elif marcadas:
            sem = [p for p in range(1, n + 1) if p not in marcadas]
            out.append(achado("REG-03", B, "Registro em todas as folhas", ATENCAO,
                              f"Marca de registro identificada em {len(marcadas)} de {n} folhas (pág. {_pags(marcadas)}). "
                              f"Sem marca legível: pág. {_pags(sem)}."
                              + (" Rubrica e carimbo manuscritos não são lidos automaticamente." if doc_est.lido_por_ocr else ""),
                              reg["ev"] or reg["ev_indicio"],
                              f"Conferir visualmente a rubrica/carimbo do cartório nas folhas {_pags(sem)}."))
        # REG-04 — certidão/etiqueta com data e selo
        d = reg["dados"]
        if reg["forte"]:
            if d.get("selo") or d.get("registro_digital") or (d.get("data_registro") and (d.get("protocolo") or d.get("matricula"))):
                out.append(achado("REG-04", B, "Etiqueta/certidão do registro", OK,
                                  "Etiqueta de registro com " + ", ".join(
                                      x for x in [f"data {d['data_registro']}" if d.get("data_registro") else "",
                                                  f"selo {d['selo']}" if d.get("selo") else "",
                                                  "assinatura digital do cartório" if d.get("registro_digital") else "",
                                                  f"protocolo {d['protocolo']}" if d.get("protocolo") else ""] if x) + ".",
                                  reg["ev"]))
            else:
                out.append(achado("REG-04", B, "Etiqueta/certidão do registro", ATENCAO,
                                  "Atenção redobrada: há marca de registro, mas NÃO localizei a data e o selo "
                                  "na etiqueta — confira o verso e as demais páginas (o selo costuma ficar lá).",
                                  reg["ev"], "Conferir o selo/data no verso; se não houver, pedir certidão do "
                                  "registro ao cartório."))
        # REG-15 — certidão de alterações (peça não solicitada no CASE)
        quando = d.get("data_registro") or d.get("data_protocolo")
        out.append(achado("REG-15", B, "Certidão de alterações", INFO,
                          "Certidão de inteiro teor/breve relato não faz parte das peças solicitadas"
                          + (f"; registro do estatuto em {quando}." if quando else "."),
                          reg["ev"] or reg["ev_indicio"] or Evidencia(doc_est.arquivo, 1, doc_est.texto[:120]),
                          "Recomendável emitir se o estatuto for antigo ou houver dúvida sobre alterações posteriores."))
        # (REG-08 mandato vitalício — removido a pedido.)

    # ------- ATA
    if ata:
        reg = ata["registro"]
        if ata["tipo"] in ("posse", "eleicao"):
            out.append(_registro_status(reg, doc_ata, "Ata", "REG-05", B))
        for a2, d2 in atas_extra:
            out.append(achado("REG-05", B, "Outra ata recebida", INFO,
                              f"{d2.arquivo}: {_rotulo_ata(a2)} — usada como apoio (não elege diretoria).",
                              a2["ev"].get("data") or Evidencia(d2.arquivo, 1, d2.texto[:160])))
        if ata["tipo"] not in ("posse", "eleicao"):
            out.append(achado("REG-05", B, "Ata de posse da diretoria vigente", PENDENCIA,
                              f"A ata enviada é {_rotulo_ata(ata)} — não elege nem empossa diretoria, então não "
                              "comprova quem é a diretoria vigente.",
                              ata["ev"].get("data") or Evidencia(doc_ata.arquivo, 1, doc_ata.texto[:200]),
                              "Enviar a ata de eleição e posse da diretoria vigente, registrada em cartório."))
        else:
            out += _regras_mandato(ata, doc_ata, est, ref, cfg, B)
        # anexo citado e não incluso / páginas faltando
        anx = ata.get("anexo_estatuto")
        pgd = ata.get("paginas_declaradas")
        if anx and not anx["incluso"]:
            extra = (f" A numeração do documento indica {pgd['total']} páginas, mas o arquivo tem "
                     f"{doc_ata.n_paginas}." if pgd and pgd["total"] > doc_ata.n_paginas else "")
            out.append(achado("REG-05", B, "Anexo citado na ata", ATENCAO,
                              "A ata cita o Estatuto Social como anexo, mas ele não está no arquivo." + extra,
                              [anx["ev"]] + ([pgd["ev"]] if pgd else []),
                              "Enviar o estatuto consolidado aprovado nesta assembleia, com o registro."))
        if ata.get("destituicao"):
            out.append(achado("REG-05", B, "Destituição de dirigente registrada na ata", ATENCAO,
                              "A ata registra a destituição de dirigente (ver trecho: motivos e deliberação).",
                              ata["destituicao"],
                              "Avaliar o impacto conforme o edital (ex.: prestação de contas pendente, "
                              "regularidade da nova diretoria)."))
        # (REG-12 cargos vagos e REG-10 convocação dispensada — removidos a pedido.)
        # inconsistência de datas (eleição citada depois da posse)
        out += _datas_incoerentes(ata, doc_ata, B)

    if est and ata and ata["tipo"] in ("posse", "eleicao"):
        out += _regras_cruzadas(est, doc_est, ata, doc_ata, B)
    return [a for a in out if a]


def _regras_mandato(ata, doc_ata, est, ref, cfg, B):
    out = []
    m = _mandato(ata, est, ref)
    if not m:
        out.append(achado("REG-06", B, "Mandato vigente", ATENCAO,
                          "Não localizei o período do mandato na ata.",
                          ata["ev"].get("data") or Evidencia(doc_ata.arquivo, 1, doc_ata.texto[:200]),
                          "Conferir o período do mandato na ata e no estatuto."))
        return out
    evs = [m.get("ev")] + ([m["mandato_est"]["ev"]] if m.get("mandato_est") else [])
    origem = {"explicito": "período escrito na ata", "anos": "período escrito na ata",
              "estatuto": f"posse em {D.br(m['inicio'])} + {m.get('anos_estatuto')} anos "
                          f"({m['mandato_est']['artigo'] if m.get('mandato_est') else 'estatuto'})",
              "inicio": "início na ata", "assembleia": "data da assembleia"}.get(m["fonte"], m["fonte"])
    if not m.get("fim"):
        out.append(achado("REG-06", B, "Mandato vigente", ATENCAO,
                          f"Mandato a partir de {D.br(m['inicio'])}; não localizei o prazo (fim) na ata nem no estatuto.",
                          evs, "Conferir a duração do mandato no estatuto."))
        return out
    txt = f"Mandato de {D.br(m['inicio'])} a {D.br(m['fim'])} ({origem})."
    pror = est.get("prorrogacao") if est else None
    if ref > m["fim"]:
        txt += f" Encerrado há {_anos_meses(m['fim'], ref)} na data de referência {D.br(ref)}."
        if pror:
            txt += f" O estatuto prevê prorrogação de mandato ({pror['artigo']})."
            evs.append(pror["ev"])
        out.append(achado("REG-06", B, "Mandato vigente", BLOQUEANTE, txt, evs,
                          "Enviar a ata de eleição/posse da diretoria atual, registrada em cartório."))
    elif ref < m["inicio"]:
        out.append(achado("REG-06", B, "Mandato vigente", ATENCAO, txt + " O mandato ainda não começou.", evs,
                          "Conferir as datas de posse."))
    else:
        out.append(achado("REG-06", B, "Mandato vigente", OK, txt, evs))
        falta = (m["fim"] - ref).days
        alerta = cfg["mandato_alerta_meses"] * 30.4
        fim_exec = cfg.get("fim_execucao_projeto")
        if falta < alerta or (fim_exec and m["fim"] < fim_exec):
            motivo = f"vence em {falta} dias" if falta < alerta else f"vence antes do fim da execução ({D.br(fim_exec)})"
            out.append(achado("REG-07", B, "Mandato próximo do fim", ATENCAO,
                              f"Mandato até {D.br(m['fim'])} — {motivo}."
                              + (f" O estatuto prevê prorrogação ({pror['artigo']})." if pror else ""),
                              evs, "Realizar AG eletiva e averbar a nova ata antes do fim do mandato."))
    # REG-08 — duração da ata × estatuto
    if m["fonte"] in ("explicito", "anos") and m.get("anos_estatuto"):
        dur = round(((m["fim"] - m["inicio"]).days + 1) / 365.25)
        st = OK if dur == m["anos_estatuto"] else ATENCAO
        out.append(achado("REG-08", B, "Duração do mandato × estatuto", st,
                          f"Ata: {dur} anos · Estatuto ({m['mandato_est']['artigo']}): {m['anos_estatuto']} anos.",
                          evs, "" if st == OK else "Alinhar o período do mandato ao estatuto."))
    return out


def _datas_incoerentes(ata, doc_ata, B):
    out = []
    ini = next((c["inicio"] for c in ata["mandatos"] if c["fonte"] in ("explicito", "inicio")), None)
    if not ini:
        return out
    for mm in doc_ata.buscar(r"eleit[oa]s?[^;]{0,80}?no dia"):
        ds = D.achar_datas(doc_ata.texto[mm.start(): mm.end() + 90])
        if ds and ds[0][0] > ini:
            out.append(achado("REG-17", B, "Datas incoerentes na ata", ATENCAO_MENOR,
                              f"A ata diz que os membros foram eleitos em {D.br(ds[0][0])}, depois da posse "
                              f"({D.br(ini)}) — provável erro de digitação.",
                              doc_ata.ev(mm.start(), 20, 140), "Corrigir nos próximos atos."))
            break
    return out


def _regras_cruzadas(est, doc_est, ata, doc_ata, B):
    out = []
    # (REG-09 rito, REG-10/REG-11 convocação e REG-12 composição/acúmulo — removidos a pedido.)
    # REG-13 — cadeia de registro
    de, da = est["registro"]["dados"], ata["registro"]["dados"]
    chaves = [("matricula", "matrícula"), ("registro_numero", "registro")]
    comuns = [(k, n) for k, n in chaves if de.get(k) and da.get(k)]
    if comuns:
        k, n = comuns[0]
        st = OK if de[k] == da[k] else ATENCAO
        out.append(achado("REG-13", B, "Cadeia de registro (mesmo cartório/PJ)", st,
                          f"Estatuto: {n} {de[k]} · Ata: {n} {da[k]}.",
                          [est["registro"]["ev"], ata["registro"]["ev"]],
                          "" if st == OK else "Pedir certidão de inteiro teor do cartório atual para confirmar a cadeia de registro."))
    elif de.get("cartorio") and da.get("cartorio") and \
            SequenceMatcher(None, sem_acento(de["cartorio"]), sem_acento(da["cartorio"])).ratio() < 0.6:
        out.append(achado("REG-13", B, "Cadeia de registro (mesmo cartório/PJ)", ATENCAO,
                          f"Estatuto: {de['cartorio']} · Ata: {da['cartorio']}.",
                          [est["registro"]["ev"], ata["registro"]["ev"]],
                          "Pedir certidão de inteiro teor do cartório atual."))
    # REG-14 — averbações faltantes
    avs = sorted(set(est["registro"]["averbacoes"]) | set(ata["registro"]["averbacoes"]))
    if len(avs) >= 2:
        buracos = [n for n in range(min(avs), max(avs)) if n not in avs]
        if buracos:
            out.append(achado("REG-14", B, "Averbações faltantes", BLOQUEANTE,
                              f"Recebidas Av.{', Av.'.join(map(str, avs))}; FALTAM: Av.{', Av.'.join(map(str, buracos))}. "
                              "A sequência de averbações precisa estar completa.",
                              [est["registro"]["ev"] or ata["registro"]["ev"]],
                              "Enviar as averbações faltantes (certidão de inteiro teor/breve relato). "
                              "Sem a sequência completa, a entidade é rejeitada."))
    # REG-16 — parentesco na diretoria
    out += _parentesco(ata, B)
    # REG-17 — referência a artigo do estatuto
    arts = {a["num"]: a for a in est["artigos"]}
    for c in ata["citacoes"]:
        art = arts.get(c["artigo"])
        if not art or doc_est.lido_por_ocr and len(arts) < 10:
            continue
        palavras = {w for w in re.findall(r"[a-z]{6,}", c["contexto"][-160:])} - {
            "estatuto", "conforme", "presente", "social", "assembleia", "artigo", "qualidade", "previsto"}
        if palavras and not any(w in art["plano"] for w in palavras):
            out.append(achado("REG-17", B, "Referência a artigo do estatuto", ATENCAO_MENOR,
                              f"A ata cita o Art. {c['artigo']} do estatuto, mas esse artigo trata de outro assunto "
                              f"(“{art['texto'][:90].strip()}…”).",
                              [c["ev"], Evidencia(doc_est.arquivo, art["pagina"], art["texto"][:200])],
                              "Corrigir a referência nos próximos atos."))
    return out


def _mesmo_endereco(e1, e2):
    """Palavras do endereço menor contidas no maior (tolera lixo de OCR no meio)."""
    if not e1 or not e2:
        return False
    t1, t2 = (set(re.findall(r"[a-z]{3,}|\d+", sem_acento(e))) for e in (e1, e2))
    menor, maior = sorted((t1, t2), key=len)
    return len(menor) >= 3 and len(menor & maior) / len(menor) >= 0.8


def _sobrenomes(nome):
    toks = [t for t in re.findall(r"[a-z]+", sem_acento(nome)) if t not in ("de", "da", "do", "dos", "das", "e")]
    return set(toks[1:])  # tudo menos o prenome


def _parentesco(ata, B):
    out = []
    pessoas = [e for e in ata["eleitos"] if e.get("nome")]
    vistos = set()
    for i, a in enumerate(pessoas):
        for b in pessoas[i + 1:]:
            par = tuple(sorted([a["nome"], b["nome"]]))
            if par in vistos or sem_acento(a["nome"]) == sem_acento(b["nome"]):
                continue
            pais_a = {sem_acento(p) for p in a["filiacao"]}
            pais_b = {sem_acento(p) for p in b["filiacao"]}
            comum = [p for p in pais_a if any(SequenceMatcher(None, p, q).ratio() > 0.9 for q in pais_b)]
            motivo = None
            if comum:
                nome_pai = next(x for x in a["filiacao"] if sem_acento(x) == comum[0])
                motivo = f"mesma filiação ({nome_pai}) — possíveis irmãos"
            else:
                casados = all((x["estado_civil"] or "").startswith("casad") for x in (a, b))
                sob = _sobrenomes(a["nome"]) & _sobrenomes(b["nome"])
                mesmo_end = _mesmo_endereco(a.get("endereco"), b.get("endereco"))
                if casados and mesmo_end:
                    motivo = ("ambos casados" + (", sobrenome em comum" if sob else "") +
                              " e mesmo endereço — possíveis cônjuges")
                elif len(sob) >= 2:
                    motivo = f"sobrenomes em comum ({', '.join(sorted(sob))}) — possível parentesco"
            if motivo:
                vistos.add(par)
                out.append(achado("REG-16", B, "Parentesco na diretoria", ATENCAO,
                                  f"{a['cargo']} {a['nome']} e {b['cargo']} {b['nome']}: {motivo}.",
                                  [a["ev"], b["ev"]],
                                  "Confirmar se o edital/norma exige vedação (ex.: requisitos de governança do "
                                  "art. 18-A da Lei 9.615/98). Não é bloqueante sem essa confirmação."))
    return out


# ====================================================== BLOCO 3 — REPRESENTANTE LEGAL

def bloco_representante(est, doc_est, ata, doc_ata, ref):
    B = "representante"
    out = []
    # (REP-04 poder de representar/assinar e REP-05 presidente empossado — removidos a pedido.)
    if est or ata:
        doc = doc_est or doc_ata
        out.append(achado("REP-06", B, "Responsável na Receita (QSA)", INFO,
                          "O cartão CNPJ não mostra o quadro de sócios e administradores (QSA); a checagem é possível "
                          "no site da Receita Federal, se o edital pedir.", Evidencia(doc.arquivo, None, "—")))
    return [a for a in out if a]
