# -*- coding: utf-8 -*-
"""
Tela 3 — Documental (Fase 2)
============================
O pool das melhores (por padrão 30) passa pela conferência de documentos.

  1. Quadro do pool — todas de uma vez, com um quadradinho por documento
     (Cartão CNPJ, Estatuto, Ata): tudo à vista, sem abrir uma por uma.
  2. Análise em lote — o sistema busca os documentos no Wix (pelo CNPJ, depois
     e-mail, depois nome) e analisa uma por uma sozinho. O resultado fica SALVO
     no processo: não precisa refazer ao voltar à tela.
  3. Detalhe — ao clicar numa linha, três cartões com o porquê de cada item e
     as ações: aprovar, pedir o documento que falta, excluir com motivo.

Aprovando, segue para a entrevista; excluindo, a próxima do ranking entra.
"""
import datetime as dt
import json
import os
import re

import pandas as pd
import streamlit as st

import tema
from telas import _calculo, _ui
from regras import contato, funil, wix
from regras import processo as proc
from regras.memoria import so_digitos
from leitura import conferencia, ia, resumo
from leitura import parecer as parecer_mod
from leitura import texto as texto_mod

# Documentos de exemplo para testar a análise sem documentos reais.
_EXEMPLOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "dados_exemplo", "documentos")
_EXEMPLOS = {"cartao_cnpj": "cartao_cnpj_EXEMPLO.pdf",
             "estatuto": "estatuto_EXEMPLO.pdf", "ata": "ata_EXEMPLO.pdf"}


def _carregar_exemplos():
    out = {}
    for g, nome in _EXEMPLOS.items():
        caminho = os.path.join(_EXEMPLOS_DIR, nome)
        if os.path.exists(caminho):
            with open(caminho, "rb") as fh:
                out[g] = [(nome, fh.read())]
        else:
            out[g] = []
    return out


# Itens da conferência (guardados em doc_check ao aprovar — outras telas leem).
CRITERIOS = {
    "Cartão CNPJ": [("cnpj_receita", "Emitido pela Receita Federal"),
                    ("cnpj_1ano", "Mais de 1 ano de funcionamento")],
    "Estatuto": [("est_finalidade", "Finalidade esportiva"),
                 ("est_cartorio", "Registrado em cartório")],
    "Ata": [("ata_vigencia", "Mandato da diretoria vigente"),
            ("ata_cartorio", "Registrada em cartório")],
}
_TODAS = [(k, rot) for grupo in CRITERIOS.values() for (k, rot) in grupo]

_DOCS = [("cartao", "Cartão CNPJ", ":material/badge:"),
         ("estatuto", "Estatuto", ":material/menu_book:"),
         ("ata", "Ata da diretoria", ":material/groups:")]
# Selo em palavra (não só cor — acessibilidade) e a cor do badge do Streamlit.
_SELO = {"verde": ("Sim", "green"), "amarelo": ("Conferir", "orange"),
         "vermelho": ("Não", "red"), "cinza": ("Falta", "gray")}
_SITUACAO_COR = {"Aprovada": "verde", "Pronta para aprovar": "verde", "Conferir": "amarelo",
                 "Não atende": "vermelho", "Não analisada": "cinza", "Sem documentos": "vermelho"}
_SITUACAO_POR_RESULTADO = {"APTO": "Pronta para aprovar", "APTO_COM_AJUSTES": "Conferir",
                           "NAO_APTO": "Não atende"}


def _md(texto):
    """Texto vindo de formulário/documento, seguro para st.markdown: não vira
    link, negrito, HTML nem badge (escapa a pontuação de marcação)."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>~$:])", r"\\\1", str(texto or ""))


def _salvar_e_recarregar(msg=None):
    _calculo.salvar_estado()
    if msg:
        st.session_state["_doc_msg"] = msg
    st.rerun()


# ------------------------------------------------------------------ dados

@st.cache_data(ttl=300, show_spinner="Lendo os envios de documentos no Wix…")
def _envios_wix():
    """Envios do formulário de documentos (só nomes e links, sem baixar)."""
    try:
        envios, _ = wix.buscar_documentos(baixar=False)
        return envios, ""
    except Exception as erro:
        print(f"[documental] Wix: {erro}")
        return [], "Não consegui ler o formulário de documentos do Wix agora."


def _contatos(dados):
    """CNPJ (dígitos) -> e-mails da inscrição (responsável primeiro)."""
    out = {}
    for _, row in dados.iterrows():
        d = so_digitos(row.get("cnpj", ""))
        if d:
            out[d] = [str(row.get(k, "") or "").strip() for k in ("email", "email_institucional")
                      if "@" in str(row.get(k, "") or "")]
    return out


def _versao(envio):
    return f"{envio.get('_id')}|{envio.get('_data')}"


def _situacao(pool, estado, ligacoes, wix_ok):
    """Uma linha por entidade do pool: envio no Wix, resumo salvo e o que falta."""
    linhas = []
    for r in pool.to_dict("records"):
        dig = r["dig"]
        reg = estado.get(dig, {})
        auto = reg.get("doc_auto")
        status = reg.get("doc_status", "pendente")
        envio, como = ligacoes.get(dig, (None, None))

        if not envio or status != "pendente":
            precisa = False
        elif not auto:
            precisa = True
        else:  # reanalisa só se o envio do Wix mudou (envio à mão não é sobrescrito)
            precisa = auto.get("origem") == "wix" and auto.get("versao") != _versao(envio)

        if envio:
            n = len(wix.grupos_enviados(envio))
            docs = (f"{n} de 3", "verde" if n == 3 else "amarelo")
        elif auto and auto.get("origem") == "manual":
            docs = ("enviados à mão", "verde")
        elif wix_ok:
            docs = ("não enviou", "vermelho")
        else:
            docs = ("—", "cinza")

        if status == "aprovada":
            situacao = "Aprovada"
        elif auto:
            situacao = _SITUACAO_POR_RESULTADO.get(auto.get("resultado"), "Conferir")
        elif envio or not wix_ok:
            situacao = "Não analisada"
        else:
            situacao = "Sem documentos"

        def doc(chave, auto=auto):
            d = (auto or {}).get(chave) or {}
            return (d.get("curto", "—"), d.get("cor", "cinza")) if auto else ("—", "cinza")

        linhas.append({"dig": dig, "nome": r["Entidade"], "pos": int(r["pos_pool"]), "nota": int(r["Nota"]),
                       "envio": envio, "como": como, "auto": auto, "status": status, "precisa": precisa,
                       "docs": docs, "cartao": doc("cartao"), "estatuto": doc("estatuto"), "ata": doc("ata"),
                       "situacao": situacao})
    return linhas


def _guardar(reg, p, arquivos, origem, como, versao):
    """Salva no processo o resumo compacto da análise (sem os arquivos)."""
    r = resumo.compacto(p)
    r.update(origem=origem, como=como or "", versao=versao,
             data=dt.date.today().strftime("%d/%m/%Y"),
             arquivos=[n for lst in arquivos.values() for n, _ in lst])
    reg["doc_auto"] = r
    reg["doc_parecer"] = conferencia.resumo_para_salvar(p)


# ------------------------------------------------------------------ tela

def mostrar():
    st.title("3 · Documental (Fase 2)")
    _ui.cabecalho(3, "Veja de uma vez como estão os documentos das melhores colocadas. O sistema busca "
                     "no Wix e analisa sozinho; você confere, aprova ou exclui com motivo.")

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para começar.")
        return

    mapa = st.session_state["mapa"]
    vagas = int(st.session_state.get("vagas", 10))
    pool_size = int(st.session_state.get("pool_fase2", 30))
    f = _calculo.funil_df(dados, mapa, vagas, pool_size)
    pool = funil.pool_documental(f)
    if len(pool) == 0:
        st.info("Nenhuma organização no pool. Confira o ranking na aba Resultado.")
        _banco_descartadas(f)
        return

    msg = st.session_state.pop("_doc_msg", None)
    if msg:
        st.success(msg)

    estado = _calculo.estado()
    wix_ok, envios = wix.ativo(), []
    if wix_ok:
        envios, erro = _envios_wix()
        if erro:
            st.warning(erro + " Tente de novo em instantes.")
            wix_ok = False
    contatos = _contatos(dados)
    # Liga os envios de documentos considerando a base inteira (não só o pool):
    # um envio vai para a entidade de nome mais parecido, esteja ela no pool ou não.
    ligacoes = wix.ligar(envios, [{"chave": d, "cnpj": d, "emails": contatos.get(d, []), "nome": n}
                                  for d, n in zip(f["dig"], f["Entidade"])]) if envios else {}
    linhas = _situacao(pool, estado, ligacoes, wix_ok)

    _metricas(linhas, f, wix_ok)
    _lote(linhas, estado)

    dig = _quadro(linhas)
    if dig:
        linha = next(l for l in linhas if l["dig"] == dig)
        _detalhe(f, linha, estado, contatos)
    else:
        st.caption("Clique numa linha do quadro para ver o detalhe e decidir.")

    _banco_descartadas(f)


def _metricas(linhas, f, wix_ok):
    com_docs = sum(1 for l in linhas if l["envio"] or (l["auto"] and l["auto"].get("origem") == "manual"))
    c = st.columns(4)
    c[0].metric("No pool", len(linhas))
    c[1].metric("Com documentos", com_docs,
                help="Documentos encontrados no Wix (pelo CNPJ, e-mail ou nome completo) ou enviados à mão.")
    c[2].metric("Já analisadas", sum(1 for l in linhas if l["auto"]))
    c[3].metric("Aprovadas / excluídas",
                f"{sum(1 for l in linhas if l['status'] == 'aprovada')} / {int((f['doc_status'] == 'excluida').sum())}")
    cols = st.columns([3, 1], vertical_alignment="center")
    if wix_ok:
        cols[0].caption("Documentos do Wix ligados à inscrição pelo CNPJ (ou e-mail do responsável). "
                        "Excluindo uma, a próxima do ranking entra no pool.")
        if cols[1].button("Atualizar do Wix", icon=":material/refresh:", width="stretch"):
            _envios_wix.clear()
            st.rerun()
    else:
        cols[0].caption("Wix desligado ou indisponível: suba os documentos à mão no detalhe de cada entidade.")


def _lote(linhas, estado):
    pend = [l for l in linhas if l["precisa"]]
    if not pend:
        return
    cols = st.columns([1, 2], vertical_alignment="center")
    rodar = cols[0].button(f"Analisar as {len(pend)} que faltam", type="primary",
                           icon=":material/play_arrow:", width="stretch")
    cols[1].caption("Busca os documentos no Wix e analisa uma por uma, sozinho (1 a 3 minutos cada). "
                    "Deixe esta tela aberta; o que já foi analisado fica salvo mesmo se fechar.")
    if not rodar:
        return
    barra = st.progress(0.0, text="Começando…")
    n, falhas = len(pend), []
    for i, l in enumerate(pend):
        def _prog(txt, frac, i=i, nome=l["nome"]):
            barra.progress(min((i + frac) / n, 1.0), text=f"{i + 1} de {n} · {nome}: {txt}")
        try:
            _prog("baixando os documentos do Wix…", 0.0)
            arquivos = wix.baixar_envio(l["envio"])
            if not any(arquivos.values()):
                raise RuntimeError("nenhum arquivo baixado")
            p = conferencia.analisar(arquivos, l["dig"], l["nome"], progresso=_prog)
            _guardar(proc.registro(estado, l["dig"]), p, arquivos, "wix", l["como"], _versao(l["envio"]))
            _calculo.salvar_estado()  # a cada entidade: fechar a tela não perde o que já foi feito
        except Exception as erro:
            print(f"[documental] lote: falhou {l['dig']}: {erro}")
            falhas.append(l["nome"])
    barra.empty()
    msg = f"{n - len(falhas)} de {n} analisadas."
    if falhas:
        msg += " Não consegui ler: " + ", ".join(falhas) + " — abra o detalhe e confira à mão."
    st.session_state["_doc_msg"] = msg
    st.rerun()


def _quadro(linhas):
    """Quadro do pool com um quadradinho colorido por documento. Devolve o CNPJ
    (dígitos) da linha escolhida, ou None."""
    df = pd.DataFrame([{"Pool": l["pos"], "Entidade": l["nome"], "Nota": l["nota"],
                        "Documentos": l["docs"][0], "Cartão": l["cartao"][0], "Estatuto": l["estatuto"][0],
                        "Ata": l["ata"][0], "Situação": l["situacao"]} for l in linhas])
    cores = pd.DataFrame([{"Documentos": l["docs"][1], "Cartão": l["cartao"][1], "Estatuto": l["estatuto"][1],
                           "Ata": l["ata"][1], "Situação": _SITUACAO_COR.get(l["situacao"], "cinza")}
                          for l in linhas])

    def _pinta(col):
        return [f"background-color:{tema.COR_STATUS[c][0]};color:{tema.COR_STATUS[c][1]}" for c in cores[col.name]]

    st.subheader("Quadro do pool")
    st.caption("Verde = conforme · amarelo = conferir · vermelho = não atende · cinza = sem documento ou "
               "ainda não analisada. Cartão mostra o tempo de funcionamento; Estatuto, o artigo do esporte.")
    versao = st.session_state.get("_quadro_v", 0)
    ev = st.dataframe(
        df.style.apply(_pinta, subset=list(cores.columns)),
        hide_index=True, width="stretch", height=min(36 * (len(df) + 1) + 4, 1110),
        on_select="rerun", selection_mode="single-row", key=f"quadro_doc_{versao}",
        column_config={"Pool": st.column_config.NumberColumn("Pool", width="small"),
                       "Nota": st.column_config.NumberColumn("Nota", width="small"),
                       "Entidade": st.column_config.TextColumn("Entidade", width="large")},
    )
    rows = ev.selection.rows if ev else []
    if rows:
        st.session_state["_doc_sel"] = linhas[rows[0]]["dig"]
    sel = st.session_state.get("_doc_sel")
    return sel if any(l["dig"] == sel for l in linhas) else None


# ------------------------------------------------------------------ detalhe

def _detalhe(f, linha, estado, contatos):
    dig = linha["dig"]
    r = f[f["dig"] == dig].iloc[0]
    reg = proc.registro(estado, dig)
    auto = reg.get("doc_auto")

    with st.container(border=True):
        topo = st.columns([6, 1], vertical_alignment="center")
        topo[0].markdown(f"### {_md(r['Entidade'])}")
        if topo[1].button("Fechar", key=f"fechar_{dig}", width="stretch"):
            st.session_state.pop("_doc_sel", None)
            st.session_state["_quadro_v"] = st.session_state.get("_quadro_v", 0) + 1
            st.rerun()
        if linha["envio"]:
            origem = f"no Wix (ligados pelo {linha['como']})"
        elif auto and auto.get("origem") == "manual":
            origem = f"enviados à mão em {auto.get('data', '—')}"
        else:
            origem = "não encontrados no Wix"
        st.caption(f"Nota {int(r['Nota'])} · posição {int(r['Posição'])} · {_md(r['Cidade'])}/{r['UF']} · "
                   f"documentos {origem}" + (f" · analisados em {auto.get('data')}" if auto else ""))

        teste = st.session_state.get(f"_teste_{dig}")
        if teste:
            c = st.columns([4, 1], vertical_alignment="center")
            c[0].warning("Teste com documentos de EXEMPLO (fictícios): não são desta entidade e nada foi salvo.")
            if c[1].button("Sair do teste", key=f"sairteste_{dig}", width="stretch"):
                for k in (f"_teste_{dig}", f"_arq_{dig}"):
                    st.session_state.pop(k, None)
                st.session_state.get("_pareceres", {}).pop(dig, None)
                st.rerun()
            _cartoes(teste, dig)
        elif auto:
            _cartoes(auto, dig)
        elif linha["envio"]:
            st.info("Documentos encontrados no Wix, ainda não analisados. Use **Analisar agora** abaixo "
                    "(ou o botão de lote acima, para todas de uma vez).")
        else:
            st.info("Esta entidade ainda não enviou documentos pelo Wix. Peça os documentos ou, se "
                    "chegaram por e-mail, suba à mão em **Enviar documentos à mão** abaixo.")

        _acoes(r, reg, auto, contatos.get(dig, []), dig)
        st.divider()
        _documentos(dig, r, linha, reg)


def _cartoes(auto, dig):
    for col, (chave, titulo, icone) in zip(st.columns(3), _DOCS):
        doc = auto.get(chave) or {}
        with col, st.container(border=True):
            st.markdown(f"**{icone} {titulo}**")
            for cor, texto in doc.get("linhas", []):
                rotulo, badge = _SELO.get(cor, ("Conferir", "orange"))
                st.markdown(f":{badge}-badge[{rotulo}] {_md(texto)}")
            if doc.get("trecho"):
                st.caption("Trecho: “" + _md(doc["trecho"]) + "”")
            if doc.get("pagina") and doc.get("arquivo"):
                if st.button(f"Ver no documento (pág. {doc['pagina']})", key=f"pag_{chave}_{dig}",
                             icon=":material/menu_book:", type="tertiary"):
                    st.session_state[f"jump_{dig}"] = {"arquivo": doc["arquivo"], "pagina": int(doc["pagina"])}
                    st.session_state[f"abrir_docs_{dig}"] = True
                    st.rerun()


def _acoes(r, reg, auto, emails, dig):
    if reg.get("doc_status") == "aprovada":
        c = st.columns([3, 1], vertical_alignment="center")
        c[0].success("Aprovada na documental — segue para a entrevista.")
        if c[1].button("Reabrir", key=f"reabrir_{dig}", width="stretch"):
            reg["doc_status"] = "pendente"
            _salvar_e_recarregar()
        return

    pontos = [(titulo, cor, t) for chave, titulo, _ in _DOCS
              for cor, t in ((auto or {}).get(chave) or {}).get("linhas", []) if cor != "verde"]
    b1, b2, b3 = st.columns(3)
    with b1:
        conferi = True
        if auto and pontos:
            conferi = st.checkbox("Conferi os pontos em amarelo/vermelho", key=f"conferi_{dig}")
        if st.button("Aprovar", type="primary", icon=":material/check:", key=f"aprovar_{dig}", width="stretch"):
            if not auto:
                st.warning("Analise os documentos antes de aprovar.")
            elif not conferi:
                st.warning("Marque que conferiu os pontos em amarelo/vermelho.")
            else:
                reg["doc_status"] = "aprovada"
                reg["doc_check"] = {k: True for k, _ in _TODAS}
                _salvar_e_recarregar("Aprovada. Segue para a aba 5 · Entrevistas.")
    with b2:
        if emails:
            corpo = contato.modelo_pedir_documentos(r["Entidade"], resumo.pendencias(auto) if auto else [])
            st.link_button("Pedir documentos", contato.link_email(emails[0], "CASE 2027 — documentos", corpo),
                           icon=":material/mail:", width="stretch")
            st.caption("Abre o seu e-mail já escrito; você revisa e envia.")
        else:
            st.caption("Sem e-mail na inscrição para pedir os documentos.")
    with b3:
        graves = [f"{titulo}: {t}" for titulo, cor, t in pontos if cor == "vermelho"]
        motivo = st.text_input("Motivo da exclusão", value="; ".join(graves[:2]), key=f"motivo_{dig}",
                               placeholder="ex.: estatuto sem finalidade esportiva")
        if st.button("Excluir", icon=":material/close:", key=f"excluir_{dig}", width="stretch"):
            if not motivo.strip():
                st.warning("Informe o motivo para excluir.")
            else:
                reg["doc_status"] = "excluida"
                reg["doc_motivo"] = motivo.strip()
                st.session_state.pop("_doc_sel", None)
                _salvar_e_recarregar("Excluída. A próxima do ranking entrou automaticamente no pool.")


def _documentos(dig, r, linha, reg):
    """Documentos da entidade: buscar/analisar no Wix, enviar à mão, ver as
    páginas, parecer completo e leitura por IA. Os arquivos ficam só na sessão."""
    arquivos = st.session_state.get(f"_arq_{dig}")
    precisa = linha["precisa"] or (linha["envio"] and not reg.get("doc_auto"))
    c = st.columns(3)
    if linha["envio"]:
        rotulo = "Analisar agora" if precisa else "Analisar de novo"
        if c[0].button(rotulo, type="primary" if precisa else "secondary", icon=":material/play_arrow:",
                       key=f"analisar_{dig}", width="stretch"):
            with st.spinner("Baixando os documentos do Wix…"):
                arquivos = wix.baixar_envio(linha["envio"])
            _analisar_e_guardar(dig, r, reg, arquivos, "wix", linha["como"], _versao(linha["envio"]))
        if not arquivos and (c[1].button("Abrir os documentos", icon=":material/folder_open:",
                                         key=f"abrir_{dig}", width="stretch")
                             or st.session_state.pop(f"abrir_docs_{dig}", False)):
            with st.spinner("Baixando os documentos do Wix…"):
                st.session_state[f"_arq_{dig}"] = wix.baixar_envio(linha["envio"])
            st.rerun()

    with st.expander("Enviar documentos à mão (recebidos por e-mail, por exemplo)"):
        manual = {}
        for (g, rot, multi), col in zip([("cartao_cnpj", "Cartão CNPJ", False), ("estatuto", "Estatuto", True),
                                         ("ata", "Ata(s)", True)], st.columns(3)):
            with col:
                up = st.file_uploader(rot, type=["pdf", "jpg", "jpeg", "png", "webp"],
                                      accept_multiple_files=multi, key=f"up_{g}_{dig}")
            lst = up if multi else ([up] if up else [])
            manual[g] = [(u.name, u.getvalue()) for u in (lst or [])]
        m = st.columns(2)
        if any(manual.values()) and m[0].button("Analisar estes arquivos", type="primary",
                                                icon=":material/play_arrow:", key=f"manual_{dig}"):
            _analisar_e_guardar(dig, r, reg, manual, "manual", "", "manual")
        if m[1].button("Testar com documentos de exemplo", icon=":material/science:", key=f"exemplo_{dig}"):
            # Só mostra: um resultado fictício NUNCA vai para o registro da entidade.
            exemplos = _carregar_exemplos()
            with st.spinner("Lendo os documentos de exemplo…"):
                p = conferencia.analisar(exemplos)
            st.session_state[f"_teste_{dig}"] = resumo.compacto(p)
            st.session_state[f"_arq_{dig}"] = exemplos
            st.session_state.setdefault("_pareceres", {})[dig] = {
                "assinatura": conferencia.assinatura(exemplos), "parecer": p}
            st.rerun()
        st.caption("Os arquivos ficam só nesta sessão (não são guardados). Fica salvo apenas o resumo da análise.")

    if not arquivos:
        return
    # "Ver no documento": consome o pedido de página ANTES de montar a pré-visualização
    # (o Streamlit não deixa alterar um widget depois de criado).
    jump = st.session_state.pop(f"jump_{dig}", None)
    if jump:
        st.session_state[f"verpdf_{dig}"] = jump["arquivo"]
        st.session_state[f"verpg_{dig}"] = int(jump["pagina"])
    _visualizar(arquivos, dig)

    guardado = st.session_state.get("_pareceres", {}).get(dig)
    p = guardado["parecer"] if guardado and guardado["assinatura"] == conferencia.assinatura(arquivos) else None
    if p is None:
        if st.button("Montar o parecer completo destes documentos", key=f"parecer_{dig}"):
            with st.spinner("Lendo os documentos…"):
                p = conferencia.analisar(arquivos, dig, r["Entidade"])
            st.session_state.setdefault("_pareceres", {})[dig] = {
                "assinatura": conferencia.assinatura(arquivos), "parecer": p}
            st.rerun()
        return
    with st.expander("Parecer completo (formato oficial)"):
        _mostrar_parecer(p, dig)
    with st.expander("Leitura por IA (apoio)"):
        _leitura_ia(arquivos, dig, r["Entidade"])


def _analisar_e_guardar(dig, r, reg, arquivos, origem, como, versao):
    if not any(arquivos.values()):
        st.warning("Nenhum arquivo para analisar.")
        return
    barra = st.progress(0.0, text="Começando a leitura…")
    try:
        p = conferencia.analisar(arquivos, dig, r["Entidade"],
                                 progresso=lambda t, x: barra.progress(min(max(x, 0.0), 1.0), text=t))
    except Exception as erro:
        barra.empty()
        print(f"[documental] análise falhou {dig}: {erro}")
        st.error("Não consegui ler esses documentos. Pode ser um arquivo protegido por senha, "
                 "corrompido ou uma digitalização muito ruim — confira à mão.")
        return
    barra.empty()
    _guardar(reg, p, arquivos, origem, como, versao)
    st.session_state[f"_arq_{dig}"] = arquivos
    st.session_state.setdefault("_pareceres", {})[dig] = {"assinatura": conferencia.assinatura(arquivos),
                                                         "parecer": p}
    _salvar_e_recarregar("Análise concluída e salva.")


# ------------------------------------------------------------------ documentos e parecer

@st.cache_data(show_spinner=False, max_entries=40)
def _render_pagina(pdf_bytes, pagina, dpi=130):
    """Uma página do PDF como imagem PNG. Devolve (png_bytes, total_de_paginas)."""
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


def _visualizar(arquivos, dig):
    """Pré-visualização do documento escolhido (PDF página a página, ou a foto)."""
    todos = [(n, b) for lst in arquivos.values() for n, b in lst]
    if not todos:
        return
    nomes = [n for n, _ in todos]
    escolha = st.selectbox("Documento", nomes, key=f"verpdf_{dig}")
    dados = next((b for n, b in todos if n == escolha), None)
    if not dados:
        return
    if texto_mod._eh_imagem(dados):
        st.image(dados, width="stretch")
        st.caption(escolha)
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
        st.caption("Não consegui pré-visualizar este arquivo.")


_SEV = [(("BLOQUEANTE",), "Impede a aprovação"),
        (("PENDENCIA",), "Falta providenciar"),
        (("ATENCAO", "ATENCAO_MENOR"), "Conferir com atenção")]


def _mostrar_parecer(p, dig):
    receb = [d.get("arquivo", "") for d in p.get("documentos_recebidos", [])]
    falt = p.get("documentos_faltantes", [])
    st.caption("Recebidos: " + _md(", ".join(receb) if receb else "—")
               + "  ·  Faltando: " + _md(", ".join(falt) if falt else "nenhum"))
    if p.get("sem_texto") and not p.get("ocr_disponivel"):
        st.warning("Documento escaneado e o leitor de imagem (OCR) não está disponível aqui: "
                   + _md(", ".join(p["sem_texto"])) + ". Confira esses à mão.")
    ajustes = p.get("ajustes", [])
    for cods, titulo in _SEV:
        itens = [a for a in ajustes if a.get("status") in cods]
        if itens:
            st.markdown(f"**{titulo}**")
            for a in itens:
                st.markdown(f"- {_md(a.get('texto', ''))}")
    # O parecer oficial traz trechos dos documentos enviados pelas entidades:
    # NUNCA renderizar como HTML (unsafe_allow_html) — vira texto puro.
    texto = parecer_mod.markdown(p).replace("<br><sub>", " — ").replace("</sub>", "")
    texto = "\n".join("##" + ln if ln.startswith("#") else ln for ln in texto.split("\n"))
    st.markdown(texto)
    c1, c2 = st.columns(2)
    nome = "".join(ch for ch in p["entidade"] if ch.isalnum() or ch in " -_")[:40].strip().replace(" ", "_")
    # BOM para o Word/Bloco de Notas do Windows abrir com acentos corretos.
    c1.download_button("Baixar parecer (.md)", ("﻿" + parecer_mod.markdown(p)).encode("utf-8"),
                       f"parecer_{nome}.md", "text/markdown", key=f"dlmd_{dig}", width="stretch")
    c2.download_button("Baixar parecer (.json)",
                       json.dumps(parecer_mod.json_publico(p), ensure_ascii=False, indent=2,
                                  default=str).encode("utf-8"),
                       f"parecer_{nome}.json", "application/json", key=f"dljs_{dig}", width="stretch")


def _simnao(v):
    return "Sim" if v is True else ("Não" if v is False else "não identificado")


def _leitura_ia(arquivos, dig, nome):
    """Leitura por IA (apoio opcional). Roda só quando o mentor clica (custo)."""
    if not ia.disponivel():
        st.caption("Leitura por IA desligada — para ativar, configure a seção [ia] no Secrets.")
        return
    sig = conferencia.assinatura(arquivos)
    guardado = st.session_state.get(f"_ia_{dig}")
    atual = guardado if (guardado and guardado.get("sig") == sig) else None
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
    fin = r.get("finalidade_esportiva") or {}
    man = r.get("mandato") or {}
    reg = r.get("registro_cartorio") or {}
    st.caption(f"IA: {r.get('_provedor', '')} · {r.get('_modelo', '')}")
    if r.get("resumo"):
        st.markdown(_md(r["resumo"]))
    st.markdown(f"- Finalidade esportiva: {_simnao(fin.get('tem'))}"
                + (f" · {_md(fin.get('artigo'))}" if fin.get("artigo") else ""))
    if fin.get("trecho"):
        st.caption("Trecho: “" + _md(fin["trecho"]) + "”")
    periodo = " a ".join(x for x in [man.get("inicio"), man.get("fim")] if x)
    st.markdown(f"- Mandato vigente: {_simnao(man.get('vigente'))}" + (f" · {_md(periodo)}" if periodo else ""))
    st.markdown(f"- Registro em cartório: estatuto {_simnao(reg.get('estatuto'))} · ata {_simnao(reg.get('ata'))}")
    for pt in (r.get("pontos_atencao") or [])[:6]:
        st.markdown(f"- {_md(pt)}")
    st.caption("Leitura de apoio — confirme com os documentos. Pode errar.")
    if st.button("Reler com IA", key=f"ia_reler_{dig}"):
        st.session_state.pop(f"_ia_{dig}", None)
        st.rerun()


# ------------------------------------------------------------------ descartadas

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
