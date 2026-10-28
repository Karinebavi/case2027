# -*- coding: utf-8 -*-
"""
Contato com as entidades — monta links de e-mail (mailto) e WhatsApp (wa.me)
já preenchidos, e os modelos de mensagem. Não envia nada sozinho: o gestor
revisa e dispara pela própria conta do Instituto Imaginação (seguro e grátis,
e nada de dado pessoal sai do computador até ele enviar).
"""
import urllib.parse

ASSINATURA = "Equipe CASE 2027 — Instituto Imaginação"


def so_digitos(s):
    return "".join(c for c in str(s) if c.isdigit())


def numero_whatsapp(numero):
    """Devolve o número só com dígitos, com DDI 55 do Brasil quando faltar."""
    d = so_digitos(numero)
    if not d:
        return ""
    if not d.startswith("55") and len(d) in (10, 11):
        d = "55" + d
    return d


def link_whatsapp(numero, texto=""):
    d = numero_whatsapp(numero)
    if not d:
        return ""
    url = f"https://wa.me/{d}"
    if texto:
        url += "?text=" + urllib.parse.quote(texto)
    return url


def link_email(destinatarios, assunto="", corpo="", oculto=False):
    """mailto: para um destinatário (to) ou vários. Com 'oculto', usa Cco (bcc)
    para não expor os e-mails entre as entidades."""
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]
    dest = [d.strip() for d in destinatarios if d and "@" in str(d)]
    if not dest:
        return ""
    params = {}
    if oculto and len(dest) > 1:
        cabeca = "mailto:"
        params["bcc"] = ",".join(dest)
    else:
        cabeca = "mailto:" + ",".join(dest)
    if assunto:
        params["subject"] = assunto
    if corpo:
        params["body"] = corpo
    consulta = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return cabeca + ("?" + consulta if consulta else "")


def modelo_selecionada(nome):
    return (
        f"Olá, equipe da {nome}!\n\n"
        "É com grande alegria que informamos que a sua organização foi SELECIONADA "
        "para a próxima etapa do CASE 2027. Em breve entraremos em contato com os "
        "próximos passos.\n\n"
        "Parabéns e obrigado pela participação!\n\n"
        f"{ASSINATURA}"
    )


def modelo_pedir_documentos(nome, pendencias):
    """Pede à entidade o documento que faltou ou veio incompleto (Fase 2)."""
    itens = "\n".join(f"- {p}" for p in pendencias) or "- Cartão CNPJ, Estatuto social e Ata da diretoria"
    return (
        f"Olá, equipe da {nome}!\n\n"
        "A sua organização está na etapa de conferência de documentos do CASE 2027. "
        "Para seguirmos, precisamos que nos envie:\n\n"
        f"{itens}\n\n"
        "Pedimos o documento completo (todas as páginas), em PDF ou em fotos legíveis.\n\n"
        f"{ASSINATURA}"
    )


def modelo_nao_selecionada(nome):
    return (
        f"Olá, equipe da {nome}!\n\n"
        "Agradecemos muito a sua inscrição no CASE 2027. Após a avaliação, informamos "
        "que a sua organização não avançou nesta edição. Reconhecemos o valor do seu "
        "trabalho e incentivamos que participe das próximas oportunidades.\n\n"
        "Seguimos à disposição e desejamos sucesso na sua jornada.\n\n"
        f"{ASSINATURA}"
    )
