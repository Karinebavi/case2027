# -*- coding: utf-8 -*-
"""
Tela 4 — Documental (Fase 2)
============================
O pool das melhores (por padrão 30) passa pela análise documental. Para cada
uma o mentor sobe os três documentos (Cartão CNPJ, Estatuto e Ata) e confere,
item a item, as regras do edital. Aprovando, segue para a entrevista; excluindo,
informa o motivo e a próxima do ranking entra automaticamente (repescagem).
"""
import hashlib

import streamlit as st

from telas import _calculo, _ui
from regras import funil
from regras import processo as proc
from leitura import conferencia

# Cor da sugestão automática (com texto, não só cor — acessibilidade).
_BADGE = {"verde": "🟢 OK", "amarelo": "🟡 Confira", "vermelho": "🔴 Falta"}

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


def _ler(grupo, arquivo, dig):
    """Lê o PDF subido (cache por conteúdo), mostra o resumo do documento e
    devolve o dicionário de critérios sugeridos. Vazio se não houver arquivo."""
    if arquivo is None:
        return {}
    try:
        dados = arquivo.getvalue()
    except Exception:
        return {}
    ck = f"{dig}:{grupo}:{hashlib.md5(dados).hexdigest()}"
    cache = st.session_state.setdefault("_conf_cache", {})
    if ck not in cache:
        with st.spinner(f"Lendo {grupo}…"):
            cache[ck] = conferencia.conferir(grupo, dados, dig)
    res = cache[ck]
    _mostrar_doc(res["doc"])
    return res["criterios"]


def _mostrar_doc(doc):
    origem = {"digital": "texto digital", "ocr": "OCR (escaneado)",
              "escaneada": "escaneado — sem texto", "erro": "não lido"}.get(
                  doc["origem"], doc["origem"])
    partes = [f"Leitura: {origem}"]
    if doc.get("cnpj_bate") is True:
        partes.append("✓ CNPJ confere com a inscrição")
    elif doc.get("cnpj_bate") is False:
        partes.append("✗ CNPJ diverge da inscrição")
    api = doc.get("api")
    if api:
        partes.append(f"Receita: {api.get('situacao') or '—'} · abertura {api.get('data_abertura') or '—'}")
    st.caption(" · ".join(partes))
    for aviso in doc.get("avisos", []):
        st.warning(aviso)


def _default(check, chave, sug):
    if chave in check:
        return bool(check[chave])
    if sug and sug.get("sugestao") is not None:
        return bool(sug["sugestao"])
    return False


def _legenda(sug):
    if not sug:
        return
    badge = _BADGE.get(sug["cor"], "")
    detalhe = sug.get("detalhe", "")
    st.caption(f"{badge} · {detalhe}" if detalhe else badge)
    ev = sug.get("evidencia")
    if ev:
        st.caption(f"› trecho: “{ev}”")


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

        novos = {}
        for grupo, itens in CRITERIOS.items():
            st.markdown(f"**{grupo}**")
            arquivo = st.file_uploader(
                f"Subir {grupo} (PDF) — o sistema lê e sugere; você confirma. Fica só nesta sessão.",
                type=["pdf"], key=f"up_{grupo}_{dig}")
            crit = _ler(grupo, arquivo, dig)  # {} se não houver arquivo
            for chave, rot in itens:
                sug = crit.get(chave)
                novos[chave] = st.checkbox(rot, value=_default(check, chave, sug),
                                           key=f"chk_{chave}_{dig}")
                _legenda(sug)

        conferidos = sum(1 for k, _ in _TODAS if novos.get(k))
        faltando = [rot for k, rot in _TODAS if not novos.get(k)]
        st.progress(conferidos / len(_TODAS), text=f"{conferidos} de {len(_TODAS)} itens conferidos")

        obs = st.text_area("Observações da análise (opcional)", value=reg.get("doc_obs", ""),
                           key=f"docobs_{dig}", height=70)

        def _persistir():
            reg["doc_check"] = novos
            reg["doc_obs"] = obs

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
                sugestao = "; ".join(faltando[:2]) if faltando else ""
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
