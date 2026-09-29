# -*- coding: utf-8 -*-
"""Mapa do Brasil (GeoJSON dos estados) para os gráficos do dashboard."""
import json
import os

_ARQ = os.path.join(os.path.dirname(os.path.dirname(__file__)), "base", "brasil_uf.geojson")

# UF -> nome (para textos e para casar com o GeoJSON quando preciso)
UF_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}


def carregar_geojson():
    """Devolve o GeoJSON dos estados (ou None se o arquivo não existir)."""
    if not os.path.exists(_ARQ):
        return None
    with open(_ARQ, "r", encoding="utf-8") as f:
        return json.load(f)
