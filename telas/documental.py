# -*- coding: utf-8 -*-
"""
Tela 4 — Documental (Fase 2)
============================
O pool das melhores (por padrão 30) passa pela análise documental. Para cada
uma o mentor sobe os três documentos (Cartão CNPJ, Estatuto e Ata) e confere,
item a item, as regras do edital. Aprovando, segue para a entrevista; excluindo,
informa o motivo e a próxima do ranking entra automaticamente (repescagem).
"""
import json

import streamlit as st

from telas import _calculo, _ui
from regras import funil
from regras import processo as proc
from leitura import conferencia
from leitura import parecer as parecer_mod

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
    st.title("4 · Documental (Fase 2)")
    _ui.cabecalho()

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
    st.caption("Os arquivos ficam só nesta sessão (não são guardados). No banco fica apenas o resumo do parecer.")
    return arquivos


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
    n_pdf = sum(len(v) for v in arquivos.values())
    if st.button(f"Analisar {n_pdf} documento(s)", type="primary", key=f"analisar_{dig}"):
        barra = st.progress(0.0, text="Começando a leitura…")

        def _prog(txt, frac):
            barra.progress(min(max(frac, 0.0), 1.0), text=txt)
        try:
            p = conferencia.analisar(arquivos, dig, r["Entidade"], progresso=_prog)
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


_RES_UI = {"APTO": "success", "APTO_COM_AJUSTES": "warning", "NAO_APTO": "error"}

# Severidade dos ajustes, em ordem e em linguagem de gente.
_SEV = [("BLOQUEANTE", "Impede a aprovação"),
        ("PENDENCIA", "Falta providenciar"),
        ("ATENCAO", "Conferir com atenção")]


def _mostrar_parecer(p, dig):
    tipo = _RES_UI[p["resultado"]]
    getattr(st, tipo)(f"**{parecer_mod.RESULTADO_TXT[p['resultado']]}** — {p['frase']}")

    # Visão rápida: o que chegou e o que falta.
    receb = [d.get("arquivo", "") for d in p.get("documentos_recebidos", [])]
    falt = p.get("documentos_faltantes", [])
    cols = st.columns(2)
    cols[0].caption("**Recebidos:** " + (", ".join(receb) if receb else "—"))
    cols[1].caption("**Faltando:** " + (", ".join(falt) if falt else "nenhum"))

    if p.get("sem_texto") and not p.get("ocr_disponivel"):
        st.warning("Documento escaneado e o leitor de imagem (OCR) não está disponível aqui: "
                   + ", ".join(p["sem_texto"]) + ". Confira esses manualmente.")

    # Pontos agrupados por gravidade, em linguagem simples (código da regra discreto).
    ajustes = p.get("ajustes", [])
    for cod, titulo in _SEV:
        itens = [a for a in ajustes if a.get("status") == cod]
        if not itens:
            continue
        st.markdown(f"**{titulo}**")
        for a in itens:
            reg = f" <span style='opacity:.45;font-size:.85em'>({a['regra']})</span>" if a.get("regra") else ""
            st.markdown(f"- {a.get('texto', '')}{reg}", unsafe_allow_html=True)

    infos = [a for a in ajustes if a.get("status") == "INFO"]
    if infos:
        with st.expander("Observações (opcional)"):
            for a in infos:
                st.markdown(f"- {a.get('texto', '')}")

    with st.expander("Parecer completo (formato oficial da conferência)"):
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


def _legenda(sug):
    if not sug:
        return
    badge = _BADGE.get(sug["cor"], "")
    detalhe = sug.get("detalhe", "")
    regra = f"[{sug['regra']}] " if sug.get("regra") else ""
    st.caption(f"{badge} · {regra}{detalhe}" if detalhe else badge)


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
        p = _parecer_da_sessao(dig, arquivos, r, check)
        if p:
            _mostrar_parecer(p, dig)
        crit = conferencia.criterios(p) if p else {}

        st.markdown("**2 · Conferência do mentor** — os itens vêm pré-marcados pelo parecer; confirme ou corrija.")
        novos = {}
        for grupo, itens in CRITERIOS.items():
            st.markdown(f"*{grupo}*")
            for chave, rot in itens:
                k = f"chk_{chave}_{dig}"
                if k not in st.session_state:
                    st.session_state[k] = bool(check.get(chave, False))
                novos[chave] = st.checkbox(rot, key=k)
                _legenda(crit.get(chave))

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
