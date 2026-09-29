# -*- coding: utf-8 -*-
"""
Tela 5 — Entrevistas (Fase 3)
=============================
As aprovadas na documental passam pela entrevista (roteiro de 15 min do
CASE 2027). Para cada uma: aloca-se o mentor responsável, registra-se o
parecer por bloco, se a organização compareceu e a decisão. Não comparecer
ou parecer negativo exclui e a próxima do ranking é repescada.
"""
import streamlit as st

from telas import _calculo, _ui
from regras import funil
from regras import processo as proc

# Roteiro padronizado (Etapa 3). tipo: "check" (OK/ALERTA) ou "nota" (texto).
ROTEIRO = [
    ("0–4 min · Boas-vindas", "Apresentação do mentor e do CASE; validar câmera, áudio e conexão.", "check"),
    ("4–6 min · Disponibilidade semanal", "Ponto focal definido e agenda compatível (1h30 por semana).", "check"),
    ("6–8 min · Experiência com projetos", "Quem elaborou/executou os projetos; gargalos de gestão/captação.", "nota"),
    ("8–11 min · Pergunta avaliativa", "O que espera alcançar no programa; por que o CASE faz sentido hoje.", "nota"),
    ("11–13 min · Dúvidas da entidade", "Espaço para dúvidas sobre mentorias e próximos passos.", "nota"),
    ("13–14 min · Infraestrutura técnica", "Câmera, áudio e conexão estáveis durante a reunião.", "check"),
    ("14–15 min · Agradecimento", "Agradecer e confirmar a data de divulgação do resultado.", "nota"),
]
OPCOES_CHECK = ["(não avaliado)", "OK", "ALERTA"]


def mostrar():
    st.title("5 · Entrevistas (Fase 3)")
    _ui.cabecalho()

    dados = st.session_state.get("dados")
    if dados is None or not st.session_state.get("mapa_ok"):
        st.info("Importe um CSV na tela 1 · Importar para começar.")
        return

    mapa = st.session_state["mapa"]
    vagas = int(st.session_state.get("vagas", 10))
    pool_size = int(st.session_state.get("pool_fase2", 30))
    f = _calculo.funil_df(dados, mapa, vagas, pool_size)

    aptas = funil.para_entrevista(f)
    pendentes = int((aptas["entrevista_status"] == "pendente").sum())
    aprovadas = int((aptas["entrevista_status"] == "aprovada").sum())
    cont = funil.contagem(f)
    c = st.columns(4)
    c[0].metric("Para entrevista", len(aptas))
    c[1].metric("Pendentes", pendentes)
    c[2].metric("Aprovadas", aprovadas)
    c[3].metric("Descartadas (total)", cont["descartadas"])

    if len(aptas) == 0:
        st.info("Nenhuma organização aprovada na documental ainda. Volte à aba 4 · Documental.")
        return

    st.caption("Aprovar mantém no processo; não comparecer ou parecer negativo exclui e repesca a próxima.")

    rotulos = {}
    for r in aptas.itertuples():
        marca = " · interesse" if r.interesse else ""
        rotulos[f"{r.Entidade}  ·  nota {int(r.Nota)}  ·  [{r.entrevista_status}]{marca}"] = r.dig
    escolha = st.selectbox("Escolha a organização", list(rotulos.keys()))
    _entrevistar(f, rotulos[escolha])

    st.divider()
    st.subheader("Situação das entrevistas")
    vis = aptas.copy()
    vis["Mentor"] = vis["entrevista_mentor"].replace("", "—")
    vis["Compareceu"] = vis["entrevista_compareceu"].map({True: "Sim", False: "Não"}).fillna("—")
    vis["Entrevista"] = vis["entrevista_status"].map(
        {"pendente": "Pendente", "aprovada": "Aprovada"}).fillna("—")
    st.dataframe(
        vis[["Posição", "Entidade", "Cidade", "UF", "Nota", "Mentor", "Compareceu", "Entrevista"]],
        width="stretch", hide_index=True,
        column_config={"Nota": st.column_config.NumberColumn("Nota")},
    )


def _entrevistar(f, dig):
    r = f[f["dig"] == dig].iloc[0]
    estado = _calculo.estado()
    reg = proc.registro(estado, dig)
    parecer = dict(reg.get("entrevista_parecer", {}))

    with st.container(border=True):
        titulo = r["Entidade"] + ("  ·  interesse do patrocinador" if r["interesse"] else "")
        st.markdown(f"### {titulo}")
        st.caption(f"Nota {int(r['Nota'])} · posição {int(r['Posição'])} · {r['Cidade']}/{r['UF']} · {r['Anos']} anos")

        col1, col2 = st.columns([2, 1])
        mentor = col1.text_input("Mentor responsável", value=reg.get("entrevista_mentor", ""), key=f"mentor_{dig}")
        comp = col2.radio("Compareceu?", ["—", "Sim", "Não"],
                          index={None: 0, True: 1, False: 2}[reg.get("entrevista_compareceu")],
                          key=f"comp_{dig}", horizontal=True)

        st.markdown("**Roteiro / parecer técnico (15 min)**")
        novos = {}
        for titulo_b, obj, tipo in ROTEIRO:
            st.markdown(f"*{titulo_b}* — {obj}")
            if tipo == "check":
                atual = parecer.get(titulo_b, "(não avaliado)")
                idx = OPCOES_CHECK.index(atual) if atual in OPCOES_CHECK else 0
                novos[titulo_b] = st.radio(titulo_b, OPCOES_CHECK, index=idx,
                                           key=f"chk_{dig}_{titulo_b}", horizontal=True, label_visibility="collapsed")
            else:
                novos[titulo_b] = st.text_area(titulo_b, value=parecer.get(titulo_b, ""),
                                               key=f"nota_{dig}_{titulo_b}", height=70, label_visibility="collapsed")

        relato = st.text_area("Relato da reunião (resumo do mentor)", value=reg.get("entrevista_relato", ""),
                              key=f"relato_{dig}", height=90)

        def _persistir():
            reg["entrevista_mentor"] = mentor.strip()
            reg["entrevista_compareceu"] = {"—": None, "Sim": True, "Não": False}[comp]
            reg["entrevista_parecer"] = novos
            reg["entrevista_relato"] = relato

        b1, b2, b3 = st.columns(3)
        if b1.button("Salvar parecer", key=f"salvar_{dig}"):
            _persistir()
            _calculo.salvar_estado()
            st.success("Parecer salvo.")
            st.rerun()
        if b2.button("Aprovar na entrevista", type="primary", key=f"aprovarent_{dig}"):
            _persistir()
            reg["entrevista_status"] = "aprovada"
            _calculo.salvar_estado()
            st.rerun()
        with b3:
            motivo = st.text_input("Motivo (se excluir)", key=f"motivoent_{dig}",
                                   placeholder="ex.: não compareceu")
            if st.button("Excluir / repescar", key=f"excluirent_{dig}"):
                _persistir()
                reg["entrevista_status"] = "excluida"
                reg["entrevista_motivo"] = motivo.strip() or ("não compareceu" if comp == "Não" else "parecer negativo")
                _calculo.salvar_estado()
                st.success("Excluída. A próxima do ranking foi repescada.")
                st.rerun()

        if reg.get("entrevista_status") == "aprovada":
            st.success("Aprovada na entrevista.")
