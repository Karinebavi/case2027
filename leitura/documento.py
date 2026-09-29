# -*- coding: utf-8 -*-
"""
Um documento lido (PDF → páginas de texto) e as buscas que as regras usam.

Tudo o que é achado vem com EVIDÊNCIA: arquivo + página + trecho do próprio
documento. As buscas rodam sobre o texto "plano" (sem acento, minúsculo),
mas o trecho mostrado é o original.
"""
import re
import unicodedata
from collections import Counter

from leitura.campos import sem_acento, so_digitos, _valida_cnpj

TIPOS_LEGIVEIS = {"cartao_cnpj": "Cartão CNPJ", "estatuto": "Estatuto", "ata": "Ata",
                  "irrelevante": "Outro documento", None: "Não identificado"}


def plano_1a1(texto):
    """Sem acento e minúsculo, mantendo 1 caractere por caractere (as posições
    no texto plano valem no texto original)."""
    if len(sem_acento(texto)) == len(texto):
        return sem_acento(texto)
    return "".join((sem_acento(c) or " ")[:1] for c in texto)


class Evidencia(dict):
    """{"arquivo", "pagina", "trecho"} — o que sustenta um achado."""

    def __init__(self, arquivo, pagina, trecho):
        super().__init__(arquivo=arquivo, pagina=pagina,
                         trecho=re.sub(r"\s+", " ", str(trecho or "")).strip()[:320])


class Documento:
    def __init__(self, arquivo, paginas, grupo=None):
        self.arquivo = arquivo
        self.grupo = grupo  # o que o mentor disse que é (campo onde subiu)
        self.paginas = []
        partes, self._inicios = [], []
        pos = 0
        for p in paginas:
            txt = unicodedata.normalize("NFC", p.get("texto") or "")
            extra = unicodedata.normalize("NFC", p.get("extra") or "")
            self.paginas.append({**p, "texto": txt, "extra": extra})
            self._inicios.append(pos)
            partes.append(txt)
            pos += len(txt) + 2
        self.texto = "\n\n".join(partes)
        self.plano = plano_1a1(self.texto)
        self.tipo = None
        self.origem = None
        self.status = "usado"   # usado | superado | duplicado | outra_entidade | irrelevante
        self.hash = None

    # ---------- posição → página ----------
    def pagina_de(self, pos):
        n = 1
        for i, ini in enumerate(self._inicios):
            if pos >= ini:
                n = i + 1
        return n

    def trecho(self, pos, antes=80, depois=160):
        ini = max(0, pos - antes)
        fim = min(len(self.texto), pos + depois)
        return self.texto[ini:fim]

    def ev(self, pos, antes=80, depois=160, trecho=None):
        return Evidencia(self.arquivo, self.pagina_de(pos),
                         trecho if trecho is not None else self.trecho(pos, antes, depois))

    def buscar(self, padrao, flags=0):
        """Todas as ocorrências do regex no texto plano (sem acento)."""
        return list(re.finditer(padrao, self.plano, flags))

    def primeiro(self, padrao, flags=0):
        m = re.search(padrao, self.plano, flags)
        return m

    @property
    def n_paginas(self):
        return len(self.paginas)

    @property
    def lido_por_ocr(self):
        return any(p["origem"] == "ocr" for p in self.paginas)

    @property
    def sem_texto(self):
        return len(self.texto.strip()) < 50

    # ---------- artigos ----------
    def artigos(self):
        """[{num, pos, pagina, texto}] na ordem do documento (estatuto)."""
        if hasattr(self, "_artigos"):
            return self._artigos
        rx = re.compile(r"(?m)^[\s\-—•*|]*(?:art(?:igo)?|an|ar1|arl)[\.,]?\s*(\d{1,3})\s*"
                        r"(?:[º°ªo]|(?<=\d)2(?=\s*[\.\-—–=:]))?\s*[\.\-—–=:,]*\s*(?=[\-—–=]|[A-Za-zÀ-ú]|$)")
        heads = []
        esperado = 1
        for m in rx.finditer(self.plano):
            bruto = m.group(1)
            opcoes = [int(bruto)]
            if len(bruto) >= 2 and bruto[-1] in "29":  # "132" = 13º lido pelo OCR
                opcoes.append(int(bruto[:-1]))
            num = next((o for o in opcoes if o == esperado), None)
            if num is None:
                num = min(opcoes, key=lambda o: abs(o - esperado))
            heads.append((num, m.start()))
            esperado = num + 1
        arts = []
        for i, (num, pos) in enumerate(heads):
            fim = heads[i + 1][1] if i + 1 < len(heads) else len(self.texto)
            arts.append({"num": num, "pos": pos, "pagina": self.pagina_de(pos),
                         "texto": self.texto[pos:fim], "plano": self.plano[pos:fim]})
        self._artigos = arts
        return arts

    def artigo_em(self, pos):
        """Artigo que contém a posição (ou None)."""
        atual = None
        for a in self.artigos():
            if a["pos"] <= pos:
                atual = a
            else:
                break
        return atual

    def rotulo_artigo(self, pos):
        a = self.artigo_em(pos)
        if not a:
            return ""
        par = ""
        trecho_ate = self.plano[a["pos"]:pos]
        ps = re.findall(r"(?:§|\$|paragrafo)\s*(\d{1,2}|unico|primeiro|segundo|terceiro|quarto)", trecho_ate)
        if ps:
            par = f", § {ps[-1]}".replace("§ unico", "parágrafo único")
        return f"Art. {a['num']}{par}"

    # ---------- CNPJ e nome da entidade ----------
    def cnpjs(self):
        """CNPJs válidos no texto, na ordem, sem repetir."""
        vistos = []
        for m in re.finditer(r"\d{2}\.?\d{3}\.?\d{3}\s*/?\s*\d{4}\s*-?\s*\d{2}", self.texto):
            num = so_digitos(m.group())
            if len(num) == 14 and num not in vistos and _valida_cnpj(num) is not False:
                vistos.append(num)
        return vistos

    def denominacao(self):
        """Nome da entidade mais repetido em MAIÚSCULAS nas primeiras páginas."""
        bloco = "\n".join(p["texto"] for p in self.paginas[:3])
        ruido = {"ESTATUTO", "CAPITULO", "CAPÍTULO", "REGISTRO", "CIVIL", "ATA", "ASSEMBLEIA",
                 "ASSEMBLÉIA", "GERAL", "EXTRAORDINARIA", "EXTRAORDINÁRIA", "ORDINÁRIA", "ORDINARIA",
                 "CNPJ", "CPF", "RG", "ANEXO", "PÁGINA", "REPÚBLICA", "FEDERATIVA", "BRASIL",
                 "CADASTRO", "NACIONAL", "PESSOA", "PESSOAS", "JURÍDICA", "JURÍDICAS", "CÓDIGO",
                 "DESCRIÇÃO", "TÍTULO", "DATA", "HORA", "LOCAL", "PRESENÇA", "MESA", "ORDEM", "DIA",
                 "ALTERAÇÃO", "ARTIGO", "DOS", "DAS", "MATRÍCULA", "RCPJ", "LIVRO", "CNP", "CNPJ/MF",
                 "SOB", "INSCRITA", "DEVIDAMENTE", "PORTADORA", "ELEIÇÃO", "DIRETORIA", "POSSE"}
        cont = Counter()
        for m in re.finditer(r"(?:[A-ZÀ-Ú]{2,}[\s\-]+){1,7}[A-ZÀ-Ú]{3,}", bloco):
            palavras = m.group().split()
            while palavras and (palavras[0] in ruido or len(palavras[0]) < 3):
                palavras.pop(0)
            while palavras and palavras[-1] in ruido:
                palavras.pop()
            nucleo = [p for p in palavras if p not in ruido and len(p) >= 3]
            if len(palavras) >= 2 and len(nucleo) >= 2:
                cont[" ".join(palavras)] += 1
        if not cont:
            return None
        org = re.compile(r"ASSOCIA|ASSOC|INSTITUTO|CASA|APAE|CLUBE|FUNDA[ÇC]|LIGA|FEDERA|CENTRO|"
                         r"GR[ÊE]MIO|ESPORT|SOCIEDADE|PROJETO|ACADEMIA|UNI[ÃA]O|N[ÚU]CLEO")
        return max(cont.items(), key=lambda kv: (bool(org.search(kv[0])), kv[1], len(kv[0])))[0]


# ---------- semelhança de nomes de entidade ----------
_GENERICAS = {"de", "da", "do", "das", "dos", "e", "a", "o", "na", "no", "associacao", "assoc",
              "instituto", "entidade", "organizacao", "social"}


def tokens_nome(nome):
    return {t for t in re.findall(r"[a-z0-9]+", sem_acento(nome)) if t not in _GENERICAS and len(t) > 1}


def nome_confere(nome_esperado, doc):
    """Fração dos termos do nome esperado que aparecem no início do documento (0..1)."""
    alvo = tokens_nome(nome_esperado)
    if not alvo:
        return None
    inicio = set(re.findall(r"[a-z0-9]+", " ".join(sem_acento(p["texto"]) for p in doc.paginas[:3])))
    return len(alvo & inicio) / len(alvo)


# ---------- tipo de documento ----------
_TIPOS = {
    "cartao_cnpj": (["comprovante de inscricao e de situacao", "cadastro nacional da pessoa juridica"],
                    ["natureza juridica", "situacao cadastral", "data de abertura", "nome empresarial"]),
    "estatuto": (["estatuto social", "estatuto da", "estatuto do"],
                 ["capitulo i", "dos associados", "da denominacao", "assembleia geral", "finalidade",
                  "compete ao presidente", "patrimonio"]),
    "ata": (["ata da assembleia", "ata de assembleia", "ata da reuniao", "ata de posse",
             "ata de assembleia", "ata da assembléia"],
            ["presentes", "mandato", "posse", "eleicao", "lavrei a presente", "nada mais havendo",
             "ordem do dia"]),
}


def classificar(doc):
    """(tipo, pontos) pelo conteúdo. Um estatuto ANEXO a uma ata vira 'ata'
    se a ata vier primeiro no arquivo."""
    plano = doc.plano
    cabeca = sem_acento("\n".join(p["texto"] for p in doc.paginas[:2]))
    pont = {}
    for tipo, (fortes, apoio) in _TIPOS.items():
        s = sum(4 for t in fortes if t in cabeca) + sum(1 for t in fortes if t in plano)
        s += sum(1 for t in apoio if t in plano)
        pont[tipo] = s
    tipo, top = max(pont.items(), key=lambda kv: kv[1])
    if top < 3:
        return "irrelevante", pont
    # o TÍTULO decide quando a ata traz o estatuto junto (ata de AGE + estatuto anexo)
    for p in doc.paginas[:2]:
        titulo = re.sub(r"\s+", " ", sem_acento(p["texto"]))
        titulo = re.sub(r"^.{0,260}?(?=\bata\b|\bestatuto\b)", "", titulo)[:160]
        if re.match(r"ata\b.{0,40}(assembl|reuniao|posse|eleicao)", titulo):
            return "ata", pont
        if re.match(r"estatuto\b", titulo) and "comprovante de inscricao" not in plano[:600]:
            return "estatuto", pont
    return tipo, pont
