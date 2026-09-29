# -*- coding: utf-8 -*-
"""
Leitura do CSV das inscrições — robusta e segura.

Aceita o CSV separado por vírgula (formato do Wix) e também por
ponto-e-vírgula (quando o Excel PT-BR salva, mas SEM corromper).
Se perceber que o arquivo foi bagunçado pelo Excel, avisa com uma
mensagem clara em vez de importar dados errados.
"""
import io
import pandas as pd

# uma base de inscrições tem muitas colunas; bem menos que isso = suspeito
MIN_COLUNAS = 5


class ArquivoCorrompido(Exception):
    """Erro amigável: o arquivo não está num CSV válido (provável estrago do Excel)."""


def _decodificar(fonte) -> str:
    dados = fonte.read()
    if isinstance(dados, bytes):
        for enc in ("utf-8", "latin-1"):
            try:
                return dados.decode(enc)
            except UnicodeDecodeError:
                continue
        return dados.decode("utf-8", errors="replace")
    return dados


def _tentar(texto: str, sep: str):
    try:
        return pd.read_csv(io.StringIO(texto), dtype=str, keep_default_na=False, sep=sep)
    except Exception:
        return None


def ler_csv(fonte) -> pd.DataFrame:
    """Lê o CSV de um caminho ou de um arquivo enviado. Devolve um DataFrame."""
    if isinstance(fonte, str):
        with open(fonte, "rb") as arq:
            texto = _decodificar(arq)
    else:
        texto = _decodificar(fonte)

    # 1) formato normal do Wix: separado por vírgula
    df = _tentar(texto, ",")
    if df is not None and df.shape[1] >= MIN_COLUNAS:
        return df

    # 2) Excel PT-BR salvou com ponto-e-vírgula, mas o arquivo está íntegro
    #    (cabeçalho separou certinho, sem vírgulas amontoadas na 1ª coluna)
    df = _tentar(texto, ";")
    if df is not None and df.shape[1] >= MIN_COLUNAS and "," not in str(df.columns[0]):
        return df

    # 3) chegou aqui = o Excel corrompeu o arquivo. Não dá pra confiar.
    raise ArquivoCorrompido(
        "Esse arquivo parece ter sido aberto e salvo no Excel, o que bagunçou o "
        "formato do CSV (e pode ter perdido dados). Envie o arquivo ORIGINAL "
        "exportado do Wix, sem abrir no Excel antes. Se quiser só espiar o "
        "conteúdo, abra no Bloco de Notas — nunca no Excel."
    )
