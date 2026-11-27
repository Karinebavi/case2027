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


# CNPJ digitado com problema (tela Inscrições -> "CNPJs a conferir")
ASSUNTO_CNPJ = "CASE 2027 — confirmação do CNPJ da sua inscrição"
_MOTIVO_CNPJ = {
    "invalido": "o número informado não corresponde a um CNPJ válido (os dígitos finais não conferem)",
    "formato": "o número informado não tem os 14 dígitos de um CNPJ",
    "outra_entidade": "o número informado está registrado na Receita Federal em nome de outra instituição",
    "confirmacao_diferente": "o CNPJ informado no campo de confirmação é diferente do CNPJ informado na inscrição",
}


def modelo_cnpj(nome, digitado, status, responsavel=""):
    """Pede à entidade que confirme o CNPJ. Não cita o nome de outra instituição
    (quando o número é de outra, diz só isso)."""
    saudacao = f"Olá, {responsavel.split()[0]}!" if str(responsavel).strip() else f"Olá, equipe da {nome}!"
    motivo = _MOTIVO_CNPJ.get(status, "não conseguimos confirmar o CNPJ informado")
    return (
        f"{saudacao}\n\n"
        f"Recebemos a inscrição da {nome} no CASE 2027 — obrigado pela participação!\n\n"
        f"Ao conferir os dados, vimos que {motivo}:\n\n"
        f"CNPJ informado: {digitado or '—'}\n\n"
        "Para seguirmos com a sua inscrição, pedimos que responda a este e-mail com:\n"
        "- o CNPJ correto da organização; e\n"
        "- o Cartão CNPJ atualizado (pode ser o PDF emitido no site da Receita Federal).\n\n"
        "Não é preciso fazer uma nova inscrição: nós corrigimos aqui.\n\n"
        f"{ASSINATURA}"
    )


def link_outlook(destinatarios, assunto="", corpo=""):
    """Abre o Outlook (Microsoft 365, no navegador) com o e-mail já montado — é só
    clicar em Enviar. Funciona igual no sistema online e no computador, sem depender
    de qual programa de e-mail o Windows usa como padrão (o mailto depende)."""
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]
    dest = [d.strip() for d in destinatarios if d and "@" in str(d)]
    if not dest:
        return ""
    params = {"to": ",".join(dest), "subject": assunto, "body": corpo}
    return ("https://outlook.office.com/mail/deeplink/compose?"
            + urllib.parse.urlencode({k: v for k, v in params.items() if v}, quote_via=urllib.parse.quote))


# Respostas que não combinam: 21/22 marcam a LIE e a 23 diz "Ainda não tenho projeto na LIE"
ASSUNTO_COERENCIA = "CASE 2027 — confirmação de respostas da sua inscrição"


def modelo_coerencia_lie(nome, perguntas, resposta_23, responsavel="",
                         link="https://www.case.org.br/inscricoes2027"):
    saudacao = f"Olá, {responsavel.split()[0]}!" if str(responsavel).strip() else f"Olá, equipe da {nome}!"
    qual = {"21": "na pergunta 21 (projetos que a organização já escreveu)",
            "22": "na pergunta 22 (projetos que a organização já executou)"}
    onde = " e ".join(qual[p] for p in perguntas if p in qual) or "nas perguntas 21/22"
    return (
        f"{saudacao}\n\n"
        f"Recebemos a inscrição da {nome} no CASE 2027 — obrigado pela participação!\n\n"
        "Ao conferir as respostas, notamos duas informações que não combinam:\n"
        f"- {onde[0].upper() + onde[1:]}, foi marcada a Lei de Incentivo ao Esporte;\n"
        f"- na pergunta 23 (situação na Lei de Incentivo ao Esporte), a resposta foi “{resposta_23.strip()}”.\n\n"
        "Quem já elaborou ou executou projeto pela Lei de Incentivo ao Esporte normalmente tem, pelo menos, "
        "cadastro no sistema da Lei ou projeto submetido.\n\n"
        "Pode nos confirmar qual é a situação correta? Se alguma resposta foi marcada por engano, por favor "
        f"refaça a inscrição pelo link abaixo — vale a inscrição mais recente:\n{link}\n\n"
        f"{ASSINATURA}"
    )
