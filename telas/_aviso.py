# -*- coding: utf-8 -*-
"""
Caixa "Avisar a entidade por e-mail" — a mesma em todas as telas (CNPJ a conferir,
respostas que não combinam...). Abre o e-mail pronto no Outlook (programa ou
navegador); o sistema não envia nada sozinho. Depois, a equipe marca o que está
esperando: a resposta do e-mail ou uma nova inscrição.
"""
import datetime as dt

import streamlit as st

from regras import contato

ESPERAS = {"resposta": "Aguardando resposta do e-mail", "nova_inscricao": "Aguardando nova inscrição"}


def emails_da_inscricao(linha):
    emails = []
    for campo in ("email", "email_institucional"):
        e = str(linha.get(campo) or "").strip()
        if "@" in e and e.lower() not in [x.lower() for x in emails]:
            emails.append(e)
    return emails


def titulo_espera(aviso):
    """Texto curto para o título do item: ' · aguardando resposta do e-mail (avisada em 26/11)'."""
    espera = ESPERAS.get((aviso or {}).get("espera"))
    if not espera:
        return ""
    return f" · {espera.lower()} (avisada em {str(aviso.get('avisada_em', ''))[:5]})"


def caixa_email(prefixo, linha, assunto, corpo, aviso, ao_marcar):
    """`prefixo`: único por item (chaves dos campos). `aviso`: o que já foi anotado
    ({avisada_em, avisada_por, espera}) ou None. `ao_marcar(dados)`: grava o aviso."""
    st.divider()
    st.markdown("**Avisar a entidade por e-mail**")
    aviso = aviso or {}
    if aviso.get("avisada_em"):
        st.caption(f"Avisada em {aviso['avisada_em']} por {aviso.get('avisada_por', '—')} · "
                   f"{ESPERAS.get(aviso.get('espera'), 'aviso enviado')}.")
    emails = emails_da_inscricao(linha)
    if not emails:
        st.caption("A inscrição não tem e-mail. Use o WhatsApp do responsável, na tela Selecionadas.")
        return
    para = st.multiselect("Para", emails, default=emails, key=f"{prefixo}_para")
    assunto = st.text_input("Assunto", assunto, key=f"{prefixo}_assunto")
    corpo = st.text_area("Mensagem (pode editar antes de abrir)", corpo, key=f"{prefixo}_corpo", height=300)
    b = st.columns(2)
    outlook = contato.link_outlook(para, assunto, corpo)
    if outlook:
        with b[0]:
            st.link_button("Outlook (programa)", contato.link_email(para, assunto, corpo), icon=":material/send:",
                           type="primary", width="stretch",
                           help="Abre o Outlook instalado no computador com o e-mail pronto. "
                                "É só conferir e clicar em Enviar.")
            st.link_button("Outlook (navegador)", outlook, icon=":material/language:", width="stretch",
                           help="Abre o Outlook na internet com o e-mail pronto.")
            st.caption("No navegador: se abrir a caixa de entrada em vez do e-mail novo, é porque pediu login "
                       "— clique de novo que abre pronto.")
    with b[1]:
        espera = st.radio("Depois de enviar", list(ESPERAS), format_func=ESPERAS.get, key=f"{prefixo}_espera",
                          index=list(ESPERAS).index(aviso["espera"]) if aviso.get("espera") in ESPERAS else 0,
                          label_visibility="collapsed")
        if st.button("Marcar como avisada", icon=":material/mark_email_read:", key=f"{prefixo}_avisada",
                     width="stretch"):
            from regras import nuvem
            ao_marcar({"avisada_em": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
                       "avisada_por": nuvem.quem(), "espera": espera})
            st.toast(f"Anotado: {ESPERAS[espera].lower()}.")
            st.rerun()
