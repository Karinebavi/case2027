# -*- coding: utf-8 -*-
"""Peças de interface reaproveitadas pelas telas (cabeçalho, ficha)."""
import streamlit as st

import tema

BLOCOS = ["Elaboração", "Execução", "Equipe", "Receita", "Infra adm.", "Infra esp.", "Digital"]
COLS_B = ["b1", "b2", "b3", "b4", "b5", "b6", "b7"]

# As 7 etapas do processo, na ordem das abas (para o guia "passo a passo").
FASES = ["Importar", "Resultado", "Documental", "Análises", "Entrevistas", "Fichas", "Dashboard"]


def _stepper(atual):
    partes = ['<div class="case-steps">']
    for i, nome in enumerate(FASES, 1):
        classe = "done" if i < atual else ("cur" if i == atual else "todo")
        partes.append(f'<div class="step {classe}"><div class="bola">{i}</div>'
                      f'<div class="rot">{nome}</div></div>')
        if i < len(FASES):
            partes.append('<div class="liga"></div>')
    partes.append("</div>")
    st.markdown("".join(partes), unsafe_allow_html=True)


def rotulos(df):
    """Rótulos únicos por entidade -> (rotulo_por_cnpj, cnpj_por_rotulo).

    Usado pela seleção da Fase 2 no Resultado e na aba Análises, para que os
    dois falem a mesma língua (mesmo rótulo para a mesma entidade).
    """
    rotulo_por_cnpj, cnpj_por_rotulo = {}, {}
    for r in df.sort_values("Nota", ascending=False).itertuples():
        lab = r.Entidade
        if lab in cnpj_por_rotulo:
            lab = f"{r.Entidade} · {r.Cidade}"
        if lab in cnpj_por_rotulo:
            lab = f"{r.Entidade} · {r.CNPJ}"
        cnpj_por_rotulo[lab] = r.CNPJ
        rotulo_por_cnpj[r.CNPJ] = lab
    return rotulo_por_cnpj, cnpj_por_rotulo


def cabecalho(passo=None, oque=None):
    """Faixa institucional + guia passo a passo.

    passo: número da etapa (1..7) para destacar no stepper.
    oque:  uma frase curta dizendo o que a pessoa faz nesta tela.
    """
    dados = st.session_state.get("dados")
    n = len(dados) if dados is not None else 0
    vagas = st.session_state.get("vagas", 10)
    if n:
        ctx = f"Ciclo 2027 · {n} inscrições carregadas · {vagas} vagas"
    else:
        ctx = "Ciclo 2027 · nenhuma base carregada"
    st.markdown(
        f'<div class="case-header"><div class="t">CASE 2027 — Seleção de Entidades</div>'
        f'<div class="c">{ctx}</div></div>',
        unsafe_allow_html=True,
    )
    if passo:
        _stepper(passo)
    if oque:
        st.markdown(f'<div class="case-guia"><b>O que fazer aqui:</b> {oque}</div>',
                    unsafe_allow_html=True)


def ficha(df, entidade, dados=None, mapa=None):
    """Mostra a ficha de uma entidade: nota por bloco, radar (entidade x média) e dados.
    Com `dados`+`mapa`, mostra a memória de cálculo detalhada (o que respondeu
    e como pontuou em cada bloco)."""
    import plotly.graph_objects as go

    linha = df[df["Entidade"] == entidade]
    if linha.empty:
        return
    r = linha.iloc[0]
    valores = [int(r[c]) for c in COLS_B]

    em = df[df["Status"] == "Em classificação"]
    if len(em):
        medias = [round(float(em[c].mean()), 1) for c in COLS_B]
    else:
        medias = [0] * 7

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores + [valores[0]], theta=BLOCOS + [BLOCOS[0]],
        fill="toself", name=entidade[:24], line_color=tema.ROXO,
    ))
    fig.add_trace(go.Scatterpolar(
        r=medias + [medias[0]], theta=BLOCOS + [BLOCOS[0]],
        name="Média das classificáveis", line_color=tema.LARANJA,
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 10], tickvals=[0, 2, 4, 6, 8, 10])),
        showlegend=True, height=380, margin=dict(l=50, r=50, t=30, b=30),
        legend=dict(orientation="h", y=-0.1),
    )

    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(fig, use_container_width=True)
    with c2:
        st.metric("Nota total", int(r["Nota"]))
        st.write(f"**Situação:** {r['Situação']}")
        pos = r.get("Posição")
        if pos is not None and str(pos) not in ("", "None", "nan"):
            st.write(f"**Posição no ranking:** {int(pos)}")
        st.write(f"**Cidade / UF:** {r['Cidade']} · {r['UF']}")
        st.write(f"**Região:** {r['Região']}")
        st.write(f"**Tempo de funcionamento:** {r['Anos']} anos")

    motivo = str(r.get("Motivo", "") or "")
    if motivo:
        # Fase 1 não exclui nem zera: a pendência é só um aviso para o mentor.
        st.warning(f"**Atenção:** {motivo}. A nota não muda por isso — confira na Fase 2 (documental).")

    _experiencia_esportiva(dados, r.get("CNPJ", ""))

    st.markdown("**Memória de cálculo — como foi a pontuação, bloco a bloco**")
    det = []
    if dados is not None and mapa is not None:
        from regras import pontuacao as _pont
        det = _pont.detalhar(dados, mapa, r.get("CNPJ", ""))
    if det:
        linhas_mem = [{"Bloco": d["Bloco"], "O que respondeu": d["Resposta"],
                       "Pontos": d["Pontos"], "Máx": d["Máx"],
                       "Média das aptas": medias[i] if i < len(medias) else None,
                       "Como foi contado": d["Como foi contado"]}
                      for i, d in enumerate(det)]
        st.dataframe(linhas_mem, width="stretch", hide_index=True, column_config={
            "O que respondeu": st.column_config.TextColumn("O que respondeu", width="medium"),
            "Pontos": st.column_config.NumberColumn("Pontos", width="small"),
            "Máx": st.column_config.NumberColumn("Máx", width="small"),
            "Média das aptas": st.column_config.NumberColumn("Média das aptas", width="small"),
            "Como foi contado": st.column_config.TextColumn("Como foi contado", width="medium"),
        })
        st.caption(f"Soma dos blocos: {sum(d['Pontos'] for d in det)} de 70 pontos possíveis.")
    else:
        tabela = [{"Bloco": b, "Pontos": v, "Média das aptas": m} for b, v, m in zip(BLOCOS, valores, medias)]
        st.dataframe(tabela, width="stretch", hide_index=True)


def _md_seguro(texto):
    """Texto da inscrição sem virar link, negrito ou HTML no st.markdown."""
    import re
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>~$:])", lambda m: chr(92) + m.group(1), str(texto or ""))


def _experiencia_esportiva(dados, cnpj):
    """Perguntas da experiência esportiva (não entram na nota, mas pesam na análise)."""
    if dados is None:
        return
    from regras.memoria import so_digitos
    alvo = so_digitos(cnpj)
    linha = next((row for _, row in dados.iterrows() if so_digitos(row.get("cnpj", "")) == alvo), None)
    if linha is None:
        return
    campos = [("Modalidades", "modalidades"), ("Outra atividade esportiva", "outra_modalidade"),
              ("Pessoas atendidas hoje", "beneficiarios"),
              ("Projetos esportivos/sociais dos últimos 3 anos", "projetos_3anos")]
    valores = [(rot, str(linha.get(ch, "") or "").strip()) for rot, ch in campos]
    if not any(v for _, v in valores):
        return
    with st.container(border=True):
        st.markdown("**Experiência esportiva** · não entra na nota; apoio para a análise")
        for rot, v in valores:
            if v:
                st.markdown(f"**{rot}:** {_md_seguro(v)}")
