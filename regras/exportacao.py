# -*- coding: utf-8 -*-
"""
Exportação da planilha de pontuação (Excel).

A planilha traz TODAS as organizações, ordenadas por nota, com as 10
primeiras (dentro das vagas) em destaque. Inclui uma coluna em branco
"Interesse do patrocinador" para o patrocinador marcar 'Sim' nas que
quer levar para a Fase 2 — depois é só subir de volta na aba Análises.
"""
import io

import pandas as pd

from regras.memoria import so_digitos

COLUNA_INTERESSE = "Interesse do patrocinador (Sim/Não)"
_MARCADO = {"sim", "s", "x", "1", "true", "verdadeiro", "ok", "interesse"}

# Colunas da planilha. As colunas de bloco são a memória de cálculo: mostram
# quantos pontos cada bloco somou até o total (70).
_COLUNAS = [
    ("Posição", "Posição"),
    ("Entidade", "Entidade"),
    ("CNPJ", "CNPJ"),
    ("Cidade", "Cidade"),
    ("UF", "UF"),
    ("Região", "Região"),
    ("Nota (total)", "Nota"),
    ("Elaboração", "b1"),
    ("Execução", "b2"),
    ("Equipe", "b3"),
    ("Receita", "b4"),
    ("Infra adm.", "b5"),
    ("Infra esp.", "b6"),
    ("Digital", "b7"),
    ("Tempo (anos)", "Anos"),
    ("Situação", "Situação"),
    ("Motivo / observação", "Motivo"),
]
# Índice (1-based) das colunas que formam a memória de cálculo (blocos + total)
_COLS_MEMORIA = list(range(7, 15))  # Nota(total) + b1..b7


def montar_planilha(df, vagas):
    """Recebe o DataFrame já pontuado/classificado e devolve os bytes do .xlsx."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    base = df.sort_values(["Nota", "Entidade"], ascending=[False, True]).copy()
    tabela = pd.DataFrame(
        {rot: (base[col].values if col in base.columns else "") for rot, col in _COLUNAS}
    )
    tabela[COLUNA_INTERESSE] = ""

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        tabela.to_excel(writer, index=False, sheet_name="Pontuação", startrow=1)
        ws = writer.sheets["Pontuação"]
        n_col = tabela.shape[1]

        # Título
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_col)
        titulo = ws.cell(row=1, column=1, value=f"CASE 2027 — Pontuação das inscrições (vagas: {vagas})")
        titulo.font = Font(bold=True, size=13, color="FFFFFF")
        titulo.alignment = Alignment(horizontal="left", vertical="center")
        titulo.fill = PatternFill("solid", fgColor="1F4E79")
        ws.row_dimensions[1].height = 22

        # Cabeçalho (linha 2) — memória de cálculo (blocos + total) com tom diferente
        borda = Side(style="thin", color="D9D9D9")
        for c in range(1, n_col + 1):
            cel = ws.cell(row=2, column=c)
            memoria = c in _COLS_MEMORIA
            cel.font = Font(bold=True, color="7A5412" if memoria else "1F4E79")
            cel.fill = PatternFill("solid", fgColor="F6EFDD" if memoria else "EAF0F7")
            cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cel.border = Border(bottom=Side(style="medium", color="1F4E79"))

        # Destaque das 10 primeiras (dentro das vagas)
        verde = PatternFill("solid", fgColor="E4F1E8")
        col_pos = 1
        for i in range(len(tabela)):
            linha = i + 3  # dados começam na linha 3
            try:
                pos = float(tabela.iloc[i]["Posição"])
                dentro = pos <= vagas
            except (TypeError, ValueError):
                dentro = False
            for c in range(1, n_col + 1):
                cel = ws.cell(row=linha, column=c)
                cel.border = Border(bottom=borda)
                if dentro:
                    cel.fill = verde
                    if c == col_pos:
                        cel.font = Font(bold=True, color="1B5E20")

        larguras = [9, 32, 20, 16, 5, 14, 11, 11, 10, 9, 9, 10, 10, 8, 12, 16, 40, 18]
        for idx, w in enumerate(larguras[:n_col], start=1):
            ws.column_dimensions[ws.cell(row=2, column=idx).column_letter].width = w
        ws.freeze_panes = "A3"

    return buffer.getvalue()


def ler_marcacao(arquivo):
    """Lê a planilha que o patrocinador marcou e devolve o conjunto de CNPJs
    (só dígitos) que ele marcou como interesse. Aceita .xlsx e .csv.

    Devolve (cnpjs_marcados, aviso) — aviso é None quando deu tudo certo.
    """
    nome = getattr(arquivo, "name", str(arquivo)).lower()
    try:
        if nome.endswith(".xlsx"):
            # a planilha exportada tem o título na 1ª linha; o cabeçalho é a 2ª
            df = pd.read_excel(arquivo, dtype=str, header=1)
        else:
            df = pd.read_csv(arquivo, dtype=str, keep_default_na=False)
    except Exception as e:
        return set(), f"Não consegui ler o arquivo. Detalhe: {e}"

    df.columns = [str(c).strip() for c in df.columns]
    col_cnpj = next((c for c in df.columns if "cnpj" in c.lower()), None)
    col_int = next((c for c in df.columns if "interesse" in c.lower()), None)
    if col_cnpj is None or col_int is None:
        return set(), (
            "A planilha precisa ter a coluna de CNPJ e a coluna "
            f"'{COLUNA_INTERESSE}'. Baixe o modelo na aba Resultado e marque nele."
        )

    marcados = set()
    for _, linha in df.iterrows():
        valor = str(linha.get(col_int, "")).strip().lower()
        if valor in _MARCADO:
            cnpj = so_digitos(linha.get(col_cnpj, ""))
            if cnpj:
                marcados.add(cnpj)
    return marcados, None
