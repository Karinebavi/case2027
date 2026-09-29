# -*- coding: utf-8 -*-
"""
Consulta pública da situação cadastral do CNPJ (BrasilAPI, base Minha Receita).

Só o número do CNPJ sai daqui — nenhum dado pessoal. Serve para automatizar a
regra do edital de "mais de 1 ano de funcionamento" (data de abertura) e para
conferir se o CNPJ está ATIVO. Tem cache de 7 dias para não repetir consulta.
Se estiver sem internet, devolve None e a tela cai para conferência manual.
"""
import datetime as _dt

try:
    import requests
except Exception:
    requests = None

try:
    import streamlit as st
    _cache = st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
except Exception:
    def _cache(fn):  # fora do Streamlit (testes), roda sem cache
        return fn


def _normalizar(bruto):
    """Aceita o formato da BrasilAPI ou do publica.cnpj.ws e unifica as chaves."""
    if not isinstance(bruto, dict):
        return None
    # BrasilAPI: campos no topo
    if "data_inicio_atividade" in bruto or "descricao_situacao_cadastral" in bruto:
        return {
            "razao_social": bruto.get("razao_social") or bruto.get("nome_fantasia"),
            "data_abertura": bruto.get("data_inicio_atividade"),
            "situacao": (bruto.get("descricao_situacao_cadastral")
                         or str(bruto.get("situacao_cadastral") or "")).upper(),
            "municipio": bruto.get("municipio"),
            "uf": bruto.get("uf"),
            "cep": "".join(c for c in str(bruto.get("cep") or "") if c.isdigit()) or None,
            "logradouro": " ".join(x for x in [bruto.get("descricao_tipo_de_logradouro"),
                                               bruto.get("logradouro")] if x) or None,
            "numero": str(bruto.get("numero") or "").lstrip("0") or None,
            "fonte": "BrasilAPI",
        }
    # publica.cnpj.ws: aninhado
    est = bruto.get("estabelecimento", {}) if isinstance(bruto.get("estabelecimento"), dict) else {}
    sit = est.get("situacao_cadastral")
    return {
        "razao_social": bruto.get("razao_social"),
        "data_abertura": est.get("data_inicio_atividade"),
        "situacao": str(sit or "").upper(),
        "municipio": (est.get("cidade") or {}).get("nome") if isinstance(est.get("cidade"), dict) else None,
        "uf": est.get("estado", {}).get("sigla") if isinstance(est.get("estado"), dict) else None,
        "cep": "".join(c for c in str(est.get("cep") or "") if c.isdigit()) or None,
        "logradouro": " ".join(x for x in [est.get("tipo_logradouro"), est.get("logradouro")] if x) or None,
        "numero": str(est.get("numero") or "").lstrip("0") or None,
        "fonte": "cnpj.ws",
    }


@_cache
def consultar(cnpj):
    """Devolve dict normalizado (razao_social, data_abertura, situacao, ...) ou None."""
    num = "".join(c for c in str(cnpj or "") if c.isdigit())
    if len(num) != 14 or requests is None:
        return None
    urls = [
        f"https://brasilapi.com.br/api/cnpj/v1/{num}",
        f"https://publica.cnpj.ws/cnpj/{num}",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "CASE2027/1.0"})
            if r.status_code == 200:
                dados = _normalizar(r.json())
                if dados:
                    return dados
        except Exception:
            continue
    return None


def anos_desde(data_abertura, referencia=None):
    """Anos completos entre a data de abertura (YYYY-MM-DD) e hoje. None se falhar."""
    if not data_abertura:
        return None
    ref = referencia or _dt.date.today()
    try:
        d = _dt.date.fromisoformat(str(data_abertura)[:10])
    except Exception:
        return None
    anos = ref.year - d.year - ((ref.month, ref.day) < (d.month, d.day))
    return anos
