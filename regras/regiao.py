# -*- coding: utf-8 -*-
"""
Normaliza o Estado (que vem em texto livre: 'SP', 'São Paulo', 'MINAS GERAIS'...)
para a sigla (UF) e devolve a região. Sem tela aqui.
"""
import unicodedata

UF_VALIDAS = {"AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB",
              "PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"}

NOMES = {
    "ACRE":"AC","ALAGOAS":"AL","AMAPA":"AP","AMAZONAS":"AM","BAHIA":"BA","CEARA":"CE",
    "DISTRITO FEDERAL":"DF","ESPIRITO SANTO":"ES","GOIAS":"GO","MARANHAO":"MA",
    "MATO GROSSO":"MT","MATO GROSSO DO SUL":"MS","MINAS GERAIS":"MG","PARA":"PA",
    "PARAIBA":"PB","PARANA":"PR","PERNAMBUCO":"PE","PIAUI":"PI","RIO DE JANEIRO":"RJ",
    "RIO GRANDE DO NORTE":"RN","RIO GRANDE DO SUL":"RS","RONDONIA":"RO","RORAIMA":"RR",
    "SANTA CATARINA":"SC","SAO PAULO":"SP","SERGIPE":"SE","TOCANTINS":"TO",
}

REGIAO = {
    "AC":"Norte","AP":"Norte","AM":"Norte","PA":"Norte","RO":"Norte","RR":"Norte","TO":"Norte",
    "AL":"Nordeste","BA":"Nordeste","CE":"Nordeste","MA":"Nordeste","PB":"Nordeste",
    "PE":"Nordeste","PI":"Nordeste","RN":"Nordeste","SE":"Nordeste",
    "DF":"Centro-Oeste","GO":"Centro-Oeste","MT":"Centro-Oeste","MS":"Centro-Oeste",
    "ES":"Sudeste","MG":"Sudeste","RJ":"Sudeste","SP":"Sudeste",
    "PR":"Sul","RS":"Sul","SC":"Sul",
}


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def para_uf(valor):
    s = _sem_acento(str(valor)).upper().strip()
    if len(s) == 2 and s in UF_VALIDAS:
        return s
    return NOMES.get(s, "")


def regiao_de(valor):
    return REGIAO.get(para_uf(valor), "")
