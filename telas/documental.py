# -*- coding: utf-8 -*-
"""
Tela 3 — Documental (Fase 2)
============================
O pool das melhores (por padrão 30) passa pela análise documental. Para cada
uma o mentor sobe os três documentos (Cartão CNPJ, Estatuto e Ata) e confere,
item a item, as regras do edital. Aprovando, segue para a entrevista; excluindo,
informa o motivo e a próxima do ranking entra automaticamente (repescagem).
"""
import base64
import html
import json
import os

import streamlit as st

from telas import _calculo, _ui
from regras import funil
from regras import processo as proc
from leitura import conferencia
from leitura import ia
from leitura import parecer as parecer_mod

# Documentos de exemplo para o "modo de teste" (experimentar a análise sem docs reais).
_EXEMPLOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "dados_exemplo", "documentos")
_EXEMPLOS = {"cartao_cnpj": "cartao_cnpj_EXEMPLO.pdf",
             "estatuto": "estatuto_EXEMPLO.pdf", "ata": "ata_EXEMPLO.pdf"}


def _carregar_exemplos():
    out = {}
    for g, nome in _EXEMPLOS.items():
        caminho = os.path.join(_EXEMPLOS_DIR, nome)
        out[g] = [(nome, open(caminho, "rb").read())] if os.path.exists(caminho) else []
    return out

# Cor da sugestão automática (com texto, não só cor — acessibilidade).
_BADGE = {"verde": "OK", "amarelo": "Confira", "vermelho": "Falta"}

# Conferência documental — (chave, rótulo). Agrupada por documento.
CRITERIOS = {
    "Cartão CNPJ": [
        ("cnpj_receita", "Emitido diretamente da Receita Federal"),
        ("cnpj_1ano", "Mais de 1 ano de funcionamento (fundação + atualizações cadastrais, até a data de hoje)"),
    ],
    "Estatuto": [
        ("est_finalidade", "Finalidade esportiva nos artigos (modalidade / prática de esporte, desporto) como FIM — não como meio para outro fim"),
        ("est_ordem", "Todos os artigos em ordem"),
        ("est_cartorio", "Registrado em cartório"),
    ],
    "Ata": [
        ("ata_vigencia", "Em vigência (atenção se o prazo estiver vencendo)"),
        ("ata_cartorio", "Registrada em cartório"),
        ("ata_selo", "Reconhecimento de selo/carimbo ou folha de registro do cartório"),
    ],
}
_TODAS = [(k, rot) for grupo in CRITERIOS.values() for (k, rot) in grupo]
_LABEL = {k: rot for k, rot in _TODAS}


def mostrar():
    st.title("3 · Documental (Fase 2)")
    _ui.cabecalho(3, "Suba os documentos de cada organização; o sistema lê e monta o parecer. "
                     "Você confere e aprova ou exclui (com motivo) — a próxima entra automaticamente.")

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para começar.")
        return

    mapa = st.session_state["mapa"]
    vagas = int(st.session_state.get("vagas", 10))
    pool_size = int(st.session_state.get("pool_fase2", 30))
    f = _calculo.funil_df(dados, mapa, vagas, pool_size)

    cont = funil.contagem(f)
    aprovadas_doc = int((f["em_pool"] & (f["doc_status"] == "aprovada")).sum())
    c = st.columns(4)
    c[0].metric("No pool", cont["pool"])
    c[1].metric("Pendentes", cont["doc_pendente"])
    c[2].metric("Aprovadas", aprovadas_doc)
    c[3].metric("Descartadas", cont["descartadas"])

    st.caption(
        f"Pool de {pool_size}. Ao excluir uma, a próxima do ranking entra automaticamente. "
        "As aprovadas seguem para a aba 5 · Entrevistas."
    )

    st.subheader("Analisar organização")
    pool = funil.pool_documental(f)
    if len(pool) == 0:
        st.info("Nenhuma organização no pool. Confira o ranking na aba Resultado.")
    else:
        rotulos = {}
        for r in pool.itertuples():
            marca = " · interesse" if r.interesse else ""
            rotulos[f"{int(r.pos_pool):>2}. {r.Entidade}  ·  nota {int(r.Nota)}  ·  [{r.doc_status}]{marca}"] = r.dig
        escolha = st.selectbox("Escolha a organização", list(rotulos.keys()))
        _analisar(f, rotulos[escolha])

    st.divider()
    st.subheader("Pool da Fase 2 (situação atual)")
    vis = pool.copy()
    vis["Interesse"] = vis["interesse"].map(lambda x: "Sim" if x else "")
    vis["Conferência"] = [_progresso(f, d) for d in vis["dig"]]
    vis["Etapa"] = vis["doc_status"].map({"pendente": "Documental (pendente)", "aprovada": "Aprovada → entrevista"})
    st.dataframe(
        vis[["pos_pool", "Entidade", "Cidade", "UF", "Nota", "Interesse", "Conferência", "Etapa"]].rename(
            columns={"pos_pool": "Pool"}),
        width="stretch", hide_index=True,
        column_config={"Nota": st.column_config.NumberColumn("Nota"),
                       "Pool": st.column_config.NumberColumn("Pool", width="small")},
    )

    _banco_descartadas(f)


def _progresso(f, dig):
    reg = _calculo.estado().get(dig, {})
    check = reg.get("doc_check", {})
    n = sum(1 for k, _ in _TODAS if check.get(k))
    return f"{n}/{len(_TODAS)}"


_GRUPOS = [("cartao_cnpj", "Cartão CNPJ", False), ("estatuto", "Estatuto", True), ("ata", "Ata(s)", True)]
_CHAVES_GRUPO = {"Cartão CNPJ": "cartao_cnpj", "Estatuto": "estatuto", "Ata": "ata"}


def _arquivos(dig):
    """Uploads da organização: {grupo: [(nome, bytes)]}."""
    st.markdown("**1 · Documentos** — suba os PDFs; o sistema lê (inclusive escaneados) e monta o parecer.")
    arquivos = {}
    for (g, rot, multi), col in zip(_GRUPOS, st.columns(3)):
        with col:
            up = st.file_uploader(rot + (" — pode mais de um" if multi else ""), type=["pdf"],
                                  accept_multiple_files=multi, key=f"up_{g}_{dig}")
        lst = up if multi else ([up] if up else [])
        arquivos[g] = [(u.name, u.getvalue()) for u in (lst or [])]

    # Modo de teste: experimentar a análise com documentos de exemplo, sem subir nada.
    teste = st.session_state.get(f"_teste_{dig}")
    if not any(arquivos.values()) and teste:
        arquivos = teste
        st.caption(":material/science: Modo de teste — usando documentos de exemplo.")
    b = st.columns([1, 1, 2])
    if b[0].button("Testar com exemplos", icon=":material/science:", key=f"teste_{dig}"):
        st.session_state[f"_teste_{dig}"] = _carregar_exemplos()
        st.session_state.get("_pareceres", {}).pop(dig, None)
        st.rerun()
    if teste and b[1].button("Limpar teste", icon=":material/close:", key=f"limpateste_{dig}"):
        st.session_state.pop(f"_teste_{dig}", None)
        st.session_state.get("_pareceres", {}).pop(dig, None)
        st.rerun()
    st.caption("Os arquivos ficam só nesta sessão (não são guardados). No banco fica apenas o resumo do parecer.")
    return arquivos


@st.cache_data(show_spinner=False, max_entries=40)
def _render_pagina(pdf_bytes, pagina, dpi=130):
    """Renderiza UMA página do PDF como imagem PNG (sempre aparece, ao contrário
    do iframe). Devolve (png_bytes, total_de_paginas)."""
    import io as _io
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_bytes)
    try:
        total = len(doc)
        pagina = max(1, min(pagina, total))
        img = doc[pagina - 1].render(scale=dpi / 72).to_pil()
        buf = _io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue(), total
    finally:
        try:
            doc.close()
        except Exception:
            pass


def _visualizar_pdfs(arquivos, dig, aberto=False):
    """Pré-visualização do documento (página renderizada como imagem)."""
    todos = [(g, n, b) for g, lst in arquivos.items() for n, b in lst]
    if not todos:
        return
    with st.expander(":material/picture_as_pdf: Documento (pré-visualização)", expanded=aberto):
        nomes = [n for _, n, _ in todos]
        escolha = st.selectbox("Documento", nomes, key=f"verpdf_{dig}", label_visibility="collapsed")
        dados = next((b for _, n, b in todos if n == escolha), None)
        if not dados:
            return
        try:
            pagina = int(st.session_state.get(f"verpg_{dig}", 1))
            png, total = _render_pagina(dados, pagina)
            if total > 1:
                pagina = st.slider("Página", 1, total, min(pagina, total), key=f"verpg_{dig}")
                png, total = _render_pagina(dados, pagina)
            st.image(png, width="stretch")
            st.caption(f"{escolha} — página {min(pagina, total)} de {total}")
        except Exception:
            st.caption("Não consegui pré-visualizar — use o botão de download para abrir o arquivo.")


def _parecer_da_sessao(dig, arquivos, r, check):
    """Mostra o botão de análise e devolve o parecer atual (ou None)."""
    guardados = st.session_state.setdefault("_pareceres", {})
    atual = guardados.get(dig)
    if not any(arquivos.values()):
        return None
    ass = conferencia.assinatura(arquivos)
    if atual and atual["assinatura"] == ass:
        return atual["parecer"]
    if atual:
        st.info("Os arquivos mudaram desde a última análise.")
    teste = bool(st.session_state.get(f"_teste_{dig}"))
    cnpj_param = None if teste else dig          # no teste, usa o CNPJ/nome do próprio exemplo
    nome_param = None if teste else r["Entidade"]
    n_pdf = sum(len(v) for v in arquivos.values())
    rotulo = "Rodar análise de exemplo" if teste else f"Analisar {n_pdf} documento(s)"
    if st.button(rotulo, type="primary", icon=":material/play_arrow:", key=f"analisar_{dig}"):
        barra = st.progress(0.0, text="Começando a leitura…")

        def _prog(txt, frac):
            barra.progress(min(max(frac, 0.0), 1.0), text=txt)
        try:
            p = conferencia.analisar(arquivos, cnpj_param, nome_param, progresso=_prog)
        except Exception as erro:  # nunca derrubar a tela
            barra.empty()
            st.error("Não consegui ler esse(s) PDF(s). Pode ser um arquivo protegido por "
                     "senha, corrompido ou uma digitalização muito ruim. Tente abrir o PDF "
                     "e usar **Salvar como** para gerar um novo, ou confira manualmente.")
            with st.expander("Detalhe técnico (para suporte)"):
                st.code(str(erro))
            return None
        barra.empty()
        guardados[dig] = {"assinatura": ass, "parecer": p}
        # pré-marca os itens que o mentor ainda não salvou
        for chave, sug in conferencia.criterios(p).items():
            if chave not in check and sug.get("sugestao") is not None:
                st.session_state[f"chk_{chave}_{dig}"] = bool(sug["sugestao"])
        st.rerun()
    else:
        st.caption("Documentos escaneados levam cerca de 2–3 s por página para ler.")
    return None


# Severidade dos ajustes, em ordem e em linguagem de gente.
_SEV = [(("BLOQUEANTE",), "Impede a aprovação"),
        (("PENDENCIA",), "Falta providenciar"),
        (("ATENCAO", "ATENCAO_MENOR"), "Conferir com atenção")]


_RES_ESTILO = {
    "APTO": ("APTO", "linear-gradient(105deg,#1E9E5A 0%,#13864A 100%)"),
    "APTO_COM_AJUSTES": ("APTO COM AJUSTES", "linear-gradient(105deg,#F0901E 0%,#E07412 100%)"),
    "NAO_APTO": ("NÃO APTO", "linear-gradient(105deg,#D84B4B 0%,#BE3636 100%)"),
}


def _resumo_destaque(p):
    """Cartão enxuto no topo: só o resultado e a frase. Os detalhes de cada
    regra ficam no checklist abaixo (sem repetir a mesma informação três vezes)."""
    rotulo, fundo = _RES_ESTILO.get(p["resultado"], ("—", "linear-gradient(105deg,#7A7A7A,#5E5E5E)"))
    ach = p.get("achados", [])
    n_at = sum(1 for a in ach if a["status"] in ("ATENCAO", "ATENCAO_MENOR"))
    n_pd = sum(1 for a in ach if a["status"] == "PENDENCIA")
    n_bl = sum(1 for a in ach if a["status"] == "BLOQUEANTE")
    partes = []
    if n_bl:
        partes.append(f"{n_bl} bloqueio(s)")
    if n_pd:
        partes.append(f"{n_pd} pendência(s)")
    if n_at:
        partes.append(f"{n_at} ponto(s) de atenção")
    linha = " · ".join(partes) if partes else "nenhum ponto a corrigir"

    st.html(
        f'<div class="case-resumo" style="background:{fundo}">'
        f'<div class="selo">PARECER DA CONFERÊNCIA</div>'
        f'<div class="res">{rotulo}</div>'
        f'<div class="ent">{html.escape(p.get("entidade", ""))}</div>'
        f'<div class="fr">{html.escape(linha)}</div>'
        f'</div>')


def _mostrar_parecer(p, dig):
    _resumo_destaque(p)

    receb = [d.get("arquivo", "") for d in p.get("documentos_recebidos", [])]
    falt = p.get("documentos_faltantes", [])
    st.caption("**Recebidos:** " + (", ".join(receb) if receb else "—")
               + "  ·  **Faltando:** " + (", ".join(falt) if falt else "nenhum"))

    if p.get("sem_texto") and not p.get("ocr_disponivel"):
        st.warning("Documento escaneado e o leitor de imagem (OCR) não está disponível aqui: "
                   + ", ".join(p["sem_texto"]) + ". Confira esses manualmente.")

    # Tudo o que é detalhe fica guardado num único lugar, fechado por padrão.
    with st.expander("Detalhes e parecer completo"):
        ajustes = p.get("ajustes", [])
        for cods, titulo in _SEV:
            itens = [a for a in ajustes if a.get("status") in cods]
            if not itens:
                continue
            st.markdown(f"**{titulo}**")
            for a in itens:
                st.markdown(f"- {a.get('texto', '')}")
        infos = [a for a in ajustes if a.get("status") == "INFO"]
        if infos:
            st.markdown("**Observações**")
            for a in infos:
                st.markdown(f"- {a.get('texto', '')}")

        st.markdown("**Parecer completo (formato oficial)**")
        texto = parecer_mod.markdown(p)
        texto = "\n".join("##" + ln if ln.startswith("#") else ln for ln in texto.split("\n"))
        st.markdown(texto, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        nome = "".join(ch for ch in p["entidade"] if ch.isalnum() or ch in " -_")[:40].strip().replace(" ", "_")
        # BOM (﻿) para o Word/Bloco de Notas do Windows abrir com acentos corretos.
        c1.download_button("Baixar parecer (.md)", ("﻿" + parecer_mod.markdown(p)).encode("utf-8"),
                           f"parecer_{nome}.md", "text/markdown", key=f"dlmd_{dig}", width="stretch")
        c2.download_button("Baixar parecer (.json)",
                           json.dumps(parecer_mod.json_publico(p), ensure_ascii=False, indent=2, default=str).encode("utf-8"),
                           f"parecer_{nome}.json", "application/json", key=f"dljs_{dig}", width="stretch")


def _simnao(v):
    return "Sim" if v is True else ("Não" if v is False else "não identificado")


def _leitura_ia(arquivos, dig, nome):
    """Leitura dos documentos por IA (apoio opcional). Roda só quando o mentor
    clica (controle de custo) e guarda o resultado na sessão."""
    if not ia.disponivel():
        st.caption(":material/smart_toy: Leitura por IA desligada — para ativar, configure a "
                   "seção [ia] no Secrets (Claude na nuvem ou Ollama local).")
        return
    sig = conferencia.assinatura(arquivos)
    guardado = st.session_state.get(f"_ia_{dig}")
    atual = guardado if (guardado and guardado.get("sig") == sig) else None

    st.markdown("**Leitura por IA (apoio)**")
    if atual is None:
        if st.button("Ler com IA", key=f"ia_btn_{dig}", icon=":material/smart_toy:"):
            with st.spinner("A IA está lendo os documentos…"):
                res, err = ia.analisar(arquivos, nome_entidade=nome)
            st.session_state[f"_ia_{dig}"] = {"sig": sig, "res": res, "err": err}
            st.rerun()
        st.caption("A IA lê e resume o que encontrou; as regras acima continuam valendo. Você confirma.")
        return

    if atual.get("err") or not atual.get("res"):
        st.warning(atual.get("err") or "A IA não retornou resultado.")
        if st.button("Tentar de novo", key=f"ia_retry_{dig}"):
            st.session_state.pop(f"_ia_{dig}", None)
            st.rerun()
        return

    r = atual["res"]
    with st.container(border=True):
        fin = r.get("finalidade_esportiva") or {}
        man = r.get("mandato") or {}
        reg = r.get("registro_cartorio") or {}
        st.caption(f"IA: {r.get('_provedor', '')} · {r.get('_modelo', '')}")
        if r.get("resumo"):
            st.markdown(r["resumo"])
        st.markdown(f"- **Finalidade esportiva:** {_simnao(fin.get('tem'))}"
                    + (f" · {fin.get('artigo')}" if fin.get("artigo") else ""))
        if fin.get("trecho"):
            st.caption(f"› “{fin['trecho']}”")
        periodo = " a ".join(x for x in [man.get("inicio"), man.get("fim")] if x)
        st.markdown(f"- **Mandato vigente:** {_simnao(man.get('vigente'))}"
                    + (f" · {periodo}" if periodo else ""))
        st.markdown(f"- **Registro em cartório:** estatuto {_simnao(reg.get('estatuto'))} · "
                    f"ata {_simnao(reg.get('ata'))}")
        pts = r.get("pontos_atencao") or []
        if pts:
            st.markdown("**Pontos de atenção (IA):**")
            for pt in pts[:6]:
                st.markdown(f"- {pt}")
        st.caption("Leitura de apoio — confirme com os documentos e o checklist. Pode errar.")
    if st.button("Reler com IA", key=f"ia_reler_{dig}"):
        st.session_state.pop(f"_ia_{dig}", None)
        st.rerun()


def _item_conferencia(chave, cri, dig, nomes_doc):
    """Abaixo de cada item do checklist: um status curto do que o sistema
    encontrou e o botão que abre o documento na página exata (onde está o
    trecho). Sem texto longo — a tela fica enxuta."""
    if not cri:
        st.caption("Sem documento/leitura para este item — confira manualmente.")
        return
    badge = _BADGE.get(cri.get("cor"), "")
    detalhe = (cri.get("detalhe") or "").strip()
    if len(detalhe) > 110:
        detalhe = detalhe[:110].rstrip() + "…"
    st.caption(f"{badge} · {detalhe}" if detalhe else (badge or ""))
    arq, pag = cri.get("arquivo"), cri.get("pagina")
    if arq and arq in nomes_doc and pag:
        if st.button(f"Conferir no documento (pág. {pag})", key=f"ir_{chave}_{dig}",
                     icon=":material/menu_book:"):
            st.session_state[f"jump_{dig}"] = {"arquivo": arq, "pagina": int(pag)}
            st.rerun()


def _analisar(f, dig):
    linha = f[f["dig"] == dig]
    if linha.empty:
        return
    r = linha.iloc[0]
    estado = _calculo.estado()
    reg = proc.registro(estado, dig)
    check = dict(reg.get("doc_check", {}))

    with st.container(border=True):
        titulo = r["Entidade"] + ("  ·  interesse do patrocinador" if r["interesse"] else "")
        st.markdown(f"### {titulo}")
        st.caption(
            f"Nota {int(r['Nota'])} · posição {int(r['Posição'])} · {r['Cidade']}/{r['UF']} · "
            f"fundação em {r.get('_data_fundacao', '—')} · {r['Anos']} anos (referência para a regra de 1 ano)"
        )
        salvo = reg.get("doc_parecer")
        if salvo:
            st.caption(f"Último parecer salvo ({salvo.get('data')}): "
                       f"{parecer_mod.RESULTADO_TXT.get(salvo.get('resultado'), '—')} · "
                       f"{', '.join(salvo.get('arquivos', []))}")

        arquivos = _arquivos(dig)
        # "Conferir no documento": um botão de item pediu para abrir o PDF numa
        # página. Consumimos aqui, ANTES de montar a pré-visualização, para não
        # alterar o widget depois de criado (regra do Streamlit).
        jump = st.session_state.pop(f"jump_{dig}", None)
        if jump:
            st.session_state[f"verpdf_{dig}"] = jump["arquivo"]
            st.session_state[f"verpg_{dig}"] = int(jump["pagina"])
        p = _parecer_da_sessao(dig, arquivos, r, check)
        if p:
            cL, cR = st.columns([5, 6], gap="medium")
            with cL:
                _visualizar_pdfs(arquivos, dig, aberto=True)
            with cR:
                _mostrar_parecer(p, dig)
                _leitura_ia(arquivos, dig, r["Entidade"])
        else:
            _visualizar_pdfs(arquivos, dig, aberto=False)
        crit = conferencia.criterios(p) if p else {}

        st.markdown("**2 · Conferência do mentor** — o sistema já marcou o que encontrou; confirme ou corrija. "
                    "Clique em *Conferir no documento* para abrir o PDF ao lado, na página exata.")
        nomes_doc = {n for _g, lst in arquivos.items() for n, _b in lst}
        novos = {}
        for grupo, itens in CRITERIOS.items():
            st.markdown(f"*{grupo}*")
            for chave, rot in itens:
                cri = crit.get(chave)
                k = f"chk_{chave}_{dig}"
                if k not in st.session_state:
                    if chave in check:            # já conferido antes: respeita o mentor
                        st.session_state[k] = bool(check.get(chave))
                    else:                          # pré-marca pelo parecer (só o que é conforme)
                        st.session_state[k] = ((cri or {}).get("sugestao") is True)
                novos[chave] = st.checkbox(rot, key=k)
                _item_conferencia(chave, cri, dig, nomes_doc)

        conferidos = sum(1 for k, _ in _TODAS if novos.get(k))
        faltando = [rot for k, rot in _TODAS if not novos.get(k)]
        st.progress(conferidos / len(_TODAS), text=f"{conferidos} de {len(_TODAS)} itens conferidos")

        obs = st.text_area("Observações da análise (opcional)", value=reg.get("doc_obs", ""),
                           key=f"docobs_{dig}", height=70)

        def _persistir():
            reg["doc_check"] = novos
            reg["doc_obs"] = obs
            if p:
                reg["doc_parecer"] = conferencia.resumo_para_salvar(p)

        b1, b2, b3 = st.columns(3)
        if b1.button("Salvar conferência", key=f"salvarconf_{dig}"):
            _persistir()
            _calculo.salvar_estado()
            st.success("Conferência salva.")
            st.rerun()

        if reg.get("doc_status") == "aprovada":
            b2.success("Aprovada")
            if b3.button("Reabrir", key=f"reabrir_{dig}"):
                _persistir()
                reg["doc_status"] = "pendente"
                _calculo.salvar_estado()
                st.rerun()
        else:
            if b2.button("Aprovar na documental", type="primary", key=f"aprovar_{dig}",
                         disabled=bool(faltando)):
                _persistir()
                reg["doc_status"] = "aprovada"
                _calculo.salvar_estado()
                st.rerun()
            if faltando:
                b2.caption(f"Faltam {len(faltando)} item(ns) para poder aprovar.")
            with b3:
                graves = [a["texto"] for a in (p["ajustes"] if p else [])
                          if a["status"] in ("BLOQUEANTE", "PENDENCIA")]
                sugestao = "; ".join(graves[:2]) if graves else ("; ".join(faltando[:2]) if faltando else "")
                motivo = st.text_input("Motivo da exclusão", value=sugestao, key=f"motivo_{dig}",
                                       placeholder="ex.: estatuto sem finalidade esportiva")
                if st.button("Excluir", key=f"excluir_{dig}"):
                    if not motivo.strip():
                        st.warning("Informe o motivo para excluir.")
                    else:
                        _persistir()
                        reg["doc_status"] = "excluida"
                        reg["doc_motivo"] = motivo.strip()
                        _calculo.salvar_estado()
                        st.success("Excluída. A próxima do ranking entrou automaticamente no pool.")
                        st.rerun()


def _banco_descartadas(f):
    desc = funil.descartadas(f)
    with st.expander(f"Banco de descartadas ({len(desc)})"):
        if len(desc) == 0:
            st.caption("Nenhuma organização descartada até aqui.")
            return
        st.caption("Organizações que saíram do processo, com o motivo. Você pode restaurar se foi engano.")
        st.dataframe(
            desc[["Posição", "Entidade", "Cidade", "UF", "Nota", "Fase", "Motivo"]],
            width="stretch", hide_index=True,
            column_config={"Nota": st.column_config.NumberColumn("Nota"),
                           "Fase": st.column_config.TextColumn("Excluída em")},
        )
        rotulos = {f"{r.Entidade} · {r.Motivo}": r.dig for r in desc.itertuples()}
        alvo = st.selectbox("Restaurar organização", ["—"] + list(rotulos.keys()), key="restaurar_sel")
        if alvo != "—" and st.button("Restaurar para o processo"):
            reg = proc.registro(_calculo.estado(), rotulos[alvo])
            reg["doc_status"] = "pendente"
            reg["doc_motivo"] = ""
            reg["entrevista_status"] = "pendente"
            reg["entrevista_motivo"] = ""
            _calculo.salvar_estado()
            st.rerun()
