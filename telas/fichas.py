# -*- coding: utf-8 -*-
"""
Tela 6 — Fichas (Fase 4)
========================
As organizações selecionadas aparecem como mini-cartões com toda a informação
e os dados de contato (com botões para e-mail e WhatsApp já preenchidos). Ao
final, uma seção para enviar o retorno às que não foram selecionadas.
"""
import io

import pandas as pd
import streamlit as st

from telas import _calculo, _ui
from regras import funil, contato
from regras import processo as proc
from regras.memoria import so_digitos

ASSUNTO = "CASE 2027 — Instituto Imaginação"


def mostrar():
    st.title("6 · Fichas (Fase 4)")
    _ui.cabecalho(6, "Veja as selecionadas em cartões com os contatos (e-mail/WhatsApp) e envie "
                     "o retorno para as que não passaram.")

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para começar.")
        return

    mapa = st.session_state["mapa"]
    vagas = int(st.session_state.get("vagas", 10))
    pool_size = int(st.session_state.get("pool_fase2", 30))
    f = _calculo.funil_df(dados, mapa, vagas, pool_size)
    contatos = _mapa_contatos(dados)

    sel = funil.selecionadas(f)
    selecionadas = sel[sel["Fase"] == "Selecionada"]
    reservas = sel[sel["Fase"] == "Aprovada (reserva)"]

    c = st.columns(3)
    c[0].metric("Selecionadas (vagas)", len(selecionadas))
    c[1].metric("Reservas aprovadas", len(reservas))
    c[2].metric("Meta (vagas)", vagas)

    if len(sel) == 0:
        st.info("Ainda não há organizações aprovadas nas duas fases. Conclua a Documental e a Entrevista.")
    else:
        st.download_button(
            "Baixar fichas das selecionadas (Excel)",
            _exportar(sel),
            "fichas_selecionadas_case2027.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.subheader("Selecionadas")
        _grade(f, selecionadas, contatos)
        if len(reservas):
            st.divider()
            st.subheader("Reservas aprovadas")
            _grade(f, reservas, contatos)

    _comunicacao(f, contatos)


def _mapa_contatos(dados):
    """CNPJ (só dígitos) -> dados de contato, a partir da base importada."""
    cols = ["responsavel", "email", "email_institucional", "whatsapp", "presidente",
            "site", "instagram", "modalidade", "beneficiarios"]
    m = {}
    for _, row in dados.iterrows():
        dig = so_digitos(row.get("cnpj", ""))
        if dig:
            m[dig] = {k: str(row.get(k, "") or "") for k in cols}
    return m


def _email_de(ct):
    for k in ("email", "email_institucional"):
        e = ct.get(k, "")
        if e and "@" in e:
            return e
    return ""


def _grade(f, df, contatos):
    linhas = list(df.itertuples())
    for i in range(0, len(linhas), 2):
        cols = st.columns(2)
        for col, r in zip(cols, linhas[i:i + 2]):
            with col:
                _cartao(f, r.dig, contatos)


def _cartao(f, dig, contatos):
    r = f[f["dig"] == dig].iloc[0]
    estado = _calculo.estado()
    reg = proc.registro(estado, dig)
    selecionada = r["Fase"] == "Selecionada"

    with st.container(border=True):
        badge = "SELECIONADA" if selecionada else "RESERVA"
        cor = "#9333EA" if selecionada else "#FF9A2D"
        st.markdown(
            f"<span style='background:{cor};color:#fff;padding:2px 8px;border-radius:4px;"
            f"font-size:12px;font-weight:600'>{badge}</span>", unsafe_allow_html=True)
        st.markdown(f"### {r['Entidade']}")
        st.caption(f"Posição {int(r['Posição'])} · nota {int(r['Nota'])} · {r['Cidade']}/{r['UF']} · "
                   f"{r['Região']} · {r['Anos']} anos")

        info = st.columns(2)
        info[0].markdown(f"**Interesse do patrocinador:** {'Sim' if r['interesse'] else 'Não'}")
        comp = {True: "Sim", False: "Não", None: "—"}[reg.get("entrevista_compareceu")]
        info[1].markdown(f"**Compareceu à entrevista:** {comp}")

        mentor = st.text_input("Mentor responsável", value=reg.get("entrevista_mentor", ""), key=f"fmentor_{dig}")
        if mentor != reg.get("entrevista_mentor", ""):
            if st.button("Salvar mentor", key=f"fsalvar_{dig}"):
                reg["entrevista_mentor"] = mentor.strip()
                _calculo.salvar_estado()
                st.rerun()

        relato = reg.get("entrevista_relato", "")
        if relato:
            st.markdown(f"**Relato da reunião:** {relato}")

        # ---- Contato ----
        ct = contatos.get(dig, {})
        email = _email_de(ct)
        whats = ct.get("whatsapp", "")
        resp = ct.get("responsavel", "") or ct.get("presidente", "")
        st.markdown("**Contato**")
        linha = []
        if resp:
            linha.append(resp)
        if email:
            linha.append(email)
        if whats:
            linha.append("WhatsApp: " + whats)
        st.caption(" · ".join(linha) if linha else "Sem dados de contato na base (reimporte o CSV para captar).")
        if email or whats:
            corpo = contato.modelo_selecionada(r["Entidade"])
            bc = st.columns(2)
            if email:
                bc[0].link_button("Enviar e-mail", contato.link_email(email, ASSUNTO, corpo), use_container_width=True)
            if whats:
                bc[1].link_button("WhatsApp", contato.link_whatsapp(whats, corpo), use_container_width=True)

        # ---- Dados da entidade ----
        linhas_dados = []
        pres = ct.get("presidente", "")
        if pres and pres != resp:
            linhas_dados.append(f"**Presidente:** {pres}")
        ei = ct.get("email_institucional", "")
        if ei and "@" in ei and ei != email:
            linhas_dados.append(f"**E-mail institucional:** {ei}")
        if ct.get("site"):
            linhas_dados.append(f"**Site:** {ct['site']}")
        if ct.get("instagram"):
            linhas_dados.append(f"**Instagram:** {ct['instagram']}")
        if ct.get("modalidade"):
            linhas_dados.append(f"**Modalidade:** {ct['modalidade']}")
        if ct.get("beneficiarios"):
            linhas_dados.append(f"**Beneficiários atendidos:** {ct['beneficiarios']}")
        if linhas_dados:
            st.markdown("**Dados da entidade**")
            for ld in linhas_dados:
                st.markdown(f"<div style='font-size:13px;color:#4A4668'>{ld}</div>",
                            unsafe_allow_html=True)

        with st.expander("Pontuação por bloco (radar)"):
            _ui.ficha(f, r["Entidade"])


def _comunicacao(f, contatos):
    st.divider()
    st.subheader("Comunicação com as entidades")
    st.caption(
        "Envie um retorno às entidades. Os botões abrem o seu e-mail já preenchido — "
        "você revisa e envia pela conta do Instituto Imaginação. Nada é enviado automaticamente."
    )

    grupos = {
        "Não passaram para a Fase 2 (abaixo do corte)": f[(~f["em_pool"]) & (f["Status"] == "Em classificação")],
        "Fora do perfil": f[f["Status"] == "Fora do perfil"],
        "Inelegíveis": f[f["Status"] == "Inelegível"],
        "Descartadas (documental/entrevista)": funil.descartadas(f),
    }
    escolha = st.selectbox("Grupo que vai receber o retorno", list(grupos.keys()))
    grupo = grupos[escolha]

    regs = [(row["Entidade"], contatos.get(so_digitos(row["CNPJ"]), {})) for _, row in grupo.iterrows()]
    emails = [_email_de(ct) for _, ct in regs]
    emails = [e for e in emails if e]
    st.caption(f"{len(grupo)} organizações neste grupo · {len(emails)} com e-mail na base.")

    assunto = st.text_input("Assunto", ASSUNTO, key="com_assunto")
    corpo = st.text_area("Mensagem", contato.modelo_nao_selecionada("sua organização"),
                         height=200, key="com_corpo")

    if not emails:
        st.info("Nenhum e-mail disponível neste grupo. Reimporte o CSV com as colunas de contato "
                "(responsável, e-mail) para habilitar o envio.")
        return

    LIMITE = 40
    c1, c2 = st.columns(2)
    link = contato.link_email(emails[:LIMITE], assunto, corpo, oculto=True)
    c1.link_button(f"Abrir e-mail em Cco (até {LIMITE})", link, use_container_width=True)
    tabela = pd.DataFrame({"Entidade": [n for n, _ in regs], "E-mail": [_email_de(c) for _, c in regs]})
    c2.download_button("Baixar lista de contatos (CSV)", tabela.to_csv(index=False).encode("utf-8"),
                       "contatos_grupo_case2027.csv", "text/csv", use_container_width=True)
    if len(emails) > LIMITE:
        st.caption(f"O botão de e-mail cobre os primeiros {LIMITE} (limite do link). "
                   "Para a lista toda, baixe o CSV e use mala direta.")
    with st.expander("Ver/copiar todos os e-mails"):
        st.code("; ".join(emails))


def _exportar(sel):
    cols = ["Posição", "Entidade", "CNPJ", "Cidade", "UF", "Região", "Nota", "Anos",
            "Fase", "interesse", "entrevista_mentor", "entrevista_compareceu", "entrevista_relato"]
    cols = [c for c in cols if c in sel.columns]
    tab = sel[cols].rename(columns={
        "Anos": "Tempo (anos)", "Fase": "Situação", "interesse": "Interesse patrocinador",
        "entrevista_mentor": "Mentor", "entrevista_compareceu": "Compareceu",
        "entrevista_relato": "Relato da reunião",
    })
    if "Interesse patrocinador" in tab.columns:
        tab["Interesse patrocinador"] = tab["Interesse patrocinador"].map({True: "Sim", False: "Não"})
    if "Compareceu" in tab.columns:
        tab["Compareceu"] = tab["Compareceu"].map({True: "Sim", False: "Não"}).fillna("—")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        tab.to_excel(writer, index=False, sheet_name="Selecionadas")
    return buffer.getvalue()
