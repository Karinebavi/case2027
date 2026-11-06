# -*- coding: utf-8 -*-
"""
Relatório da conferência documental de UMA entidade (HTML de uma página).

Monta, a partir da leitura da IA guardada no processo (doc_leitura), o que a IA
leu em cada documento, como separou as páginas e o que o sistema decidiu em
cada item — com arquivo, página e trecho. As regras são aplicadas na hora
(regras_ia.avaliar): se uma regra mudar, o relatório acompanha, sem pagar uma
nova leitura. Abre em qualquer navegador e pode ser salvo em PDF (Imprimir).
"""
import datetime as dt
import html

from leitura import regras_ia

RESULTADO = {"APTO": ("Apto", "ok"), "APTO_COM_AJUSTES": ("Apto com ajustes", "atencao"),
             "NAO_APTO": ("Não apto", "nao")}
CLASSE = {"OK": "ok", "ATENCAO": "atencao", "CONFIRA": "confira", "PENDENCIA": "pend", "NAO_APTO": "nao"}
BLOCO = {"documentos": "Documentos", "cartao": "Cartão CNPJ", "finalidade": "Finalidade esportiva",
         "mandato": "Mandato da diretoria", "cartorio": "Registro em cartório"}
TIPO = {"cartao_cnpj": "cartão CNPJ", "estatuto": "estatuto", "certidao_inteiro_teor": "certidão de inteiro teor",
        "negativa_alteracoes": "certidão negativa", "ata": "ata", "edital_convocacao": "edital",
        "lista_presenca": "lista de presença", "requerimento_cartorio": "requerimento ao cartório",
        "etiqueta_registro": "etiqueta de registro", "declaracao": "declaração",
        "documento_pessoal": "documento pessoal", "outro": "outro", "em_branco": "em branco"}
TIPO_ATA = {"eleicao_e_posse": "eleição e posse", "eleicao": "eleição", "posse": "posse", "fundacao": "fundação",
            "alteracao_estatutaria": "alteração do estatuto", "prestacao_contas": "prestação de contas",
            "outra": "outra"}
LOCAL = {"artigo_de_finalidades": "no artigo/seção de finalidades", "outro_artigo": "em outro artigo",
         "meios_ou_atividades": "entre os meios/atividades", "prerrogativas": "entre as prerrogativas",
         "natureza_ou_carater": "só no caráter/nome", "nao_encontrado": "não encontrado"}
SIM_NAO = {True: "sim", False: "não", None: "—"}

CSS = """
:root { --fg:#221F2E; --mut:#625E75; --heading:#3E087C; --roxo:#9333EA; --borda:#E4DFF2; --lav:#F5F3FC; }
* { box-sizing:border-box; }
body { margin:0; background:#fff; color:var(--fg); font:15px/1.55 'Nunito Sans', system-ui, sans-serif; }
main { max-width:1000px; margin:0 auto; padding:32px 16px 64px; }
h1,h2,h3 { font-family:'Baloo 2', sans-serif; color:var(--heading); line-height:1.15; }
h1 { font-size:1.9rem; margin:0; } h2 { font-size:1.2rem; margin:30px 0 8px; } h3 { font-size:1rem; margin:18px 0 6px; }
.mut { color:var(--mut); } code { font-size:.85em; background:var(--lav); padding:1px 5px; border-radius:4px; }
header.topo { display:flex; gap:12px; align-items:flex-start; justify-content:space-between; flex-wrap:wrap;
  border-bottom:1px solid var(--borda); padding-bottom:16px; }
table { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }
th, td { text-align:left; vertical-align:top; padding:7px 10px; border-bottom:1px solid var(--borda); }
tr.grupo th { background:var(--lav); color:var(--heading); font-size:.85rem; }
table.dados th { width:220px; color:var(--mut); font-weight:600; }
.itens td:first-child { width:150px; } .itens td:last-child { width:240px; font-size:.9rem; }
.trecho { margin-top:4px; color:var(--mut); font-style:italic; font-size:.92rem; }
.pill { display:inline-block; padding:2px 10px; border-radius:999px; font-weight:700; font-size:.82rem; white-space:nowrap; }
.pill.grande { font-size:1.05rem; padding:5px 16px; }
.ok { background:#E4F1E8; color:#1B5E20; } .atencao { background:#FBF1DD; color:#7A5412; }
.confira { background:#EDE4FB; color:#5B21B6; } .pend { background:#F6E4E4; color:#8A2A2A; }
.nao { background:#8A2A2A; color:#fff; }
.legenda .pill { margin:0 4px 4px 0; }
ul { padding-left:18px; } li { margin-bottom:6px; }
.tag { background:var(--lav); color:var(--roxo); border-radius:999px; padding:1px 8px; font-size:.78rem; font-weight:700; }
footer { margin-top:40px; border-top:1px solid var(--borda); padding-top:12px; font-size:.85rem; color:var(--mut); }
::selection { background:#EAE4FB; }
@media print { main { padding:0; } h2 { break-after:avoid; } tr { break-inside:avoid; } }
@media (max-width:640px) { table.dados th { width:auto; } .itens td:last-child { width:auto; } }
"""


def e(t):
    return html.escape("—" if t in (None, "") else str(t))


def _linhas(pares):
    return "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in pares if v not in (None, ""))


def _onde(o):
    partes = [o.get("arquivo"), f"p. {o['pagina']}" if o.get("pagina") else None]
    return " · ".join(p for p in partes if p) or None


def _registro(reg):
    reg = reg or {}
    situacao = {"registrado": "registrado", "so_protocolado": "só protocolado (sem registro)",
                "sem_indicacao": "sem sinal de cartório", "ilegivel": "há carimbo, mas não dá para ler"}
    return [("Situação", situacao.get(reg.get("situacao"), reg.get("situacao"))),
            ("Cartório", reg.get("cartorio_nome")),
            ("Registro Civil de Pessoas Jurídicas", SIM_NAO.get(reg.get("e_registro_civil_pessoas_juridicas"))),
            ("Nº do registro", reg.get("numero_registro")), ("Averbação", reg.get("averbacao")),
            ("Livro / folha", " / ".join(x for x in [reg.get("livro"), reg.get("folha")] if x)),
            ("Protocolo", reg.get("protocolo")), ("Data do registro", reg.get("data_registro")),
            ("Selo", reg.get("selo")), ("Cidade do cartório", reg.get("cidade_cartorio")),
            ("Onde está", " · ".join(x for x in [_onde(reg), reg.get("posicao_na_pagina")] if x)),
            ("Dúvidas de leitura", reg.get("incertezas"))]


def _paginas(L):
    por_arq = {}
    for p in L.get("paginas") or []:
        por_arq.setdefault(p.get("arquivo"), []).append((p.get("pagina") or 0, TIPO.get(p.get("tipo"), p.get("tipo"))))
    itens = []
    for arq, pgs in por_arq.items():
        grupos, atual = [], None
        for n, t in sorted(pgs):
            if atual and atual[2] == t and n == atual[1] + 1:
                atual[1] = n
            else:
                atual = [n, n, t]
                grupos.append(atual)
        texto = " · ".join(f"p.{a}" + (f"–{b}" if b != a else "") + f" {t}" for a, b, t in grupos)
        misturado = len({t for _, _, t in grupos}) > 1
        itens.append(f"<li><code>{e(arq)}</code> {'<span class=tag>vários documentos</span>' if misturado else ''}"
                     f"<br><span class=mut>{e(texto)}</span></li>")
    return "<ul>" + "".join(itens) + "</ul>" if itens else "<p class=mut>—</p>"


def montar(nome, leitura, info=None, cnpj=None, cidade_uf=None, data_inscricao=None, data_leitura=None):
    """HTML (texto) do relatório. leitura = o dict do leitor_ia guardado no processo."""
    info = info or {}
    L = leitura or {}
    av = regras_ia.avaliar(L, cnpj=cnpj, data_inscricao=data_inscricao, cidade_uf=cidade_uf)
    rot, cls = RESULTADO[av["resultado"]]

    itens = []
    for b in regras_ia.BLOCOS:
        do_bloco = [i for i in av["itens"] if i["bloco"] == b]
        if not do_bloco:
            continue
        itens.append(f"<tr class=grupo><th colspan=3>{e(BLOCO[b])}</th></tr>")
        for i in do_bloco:
            ev = i["evidencia"]
            onde = " · ".join(x for x in [ev.get("arquivo"), f"p. {ev['pagina']}" if ev.get("pagina") else None,
                                          ev.get("artigo")] if x)
            trecho = f"<div class=trecho>“{e(ev['trecho'])}”</div>" if ev.get("trecho") else ""
            itens.append(f"<tr><td><span class='pill {CLASSE[i['status']]}'>{e(i['rotulo'])}</span></td>"
                         f"<td><b>{e(i['item'])}</b><br>{e(i['motivo'])}{trecho}</td>"
                         f"<td class=mut>{e(onde) if onde else ''}</td></tr>")

    c = L.get("cartao") or {}
    cartao = _linhas([("Nome empresarial", c.get("nome_empresarial")), ("CNPJ", c.get("cnpj")),
                      ("Emitido em", c.get("data_emissao")), ("Situação cadastral", c.get("situacao_cadastral")),
                      ("Natureza jurídica", " - ".join(x for x in [c.get("natureza_codigo"),
                                                                   c.get("natureza_descricao")] if x)),
                      ("Abertura", c.get("data_abertura")), ("Município", c.get("municipio_uf")),
                      ("Onde está", _onde(c))]) if c else ""

    es = L.get("estatuto") or {}
    fin = es.get("finalidade") or {}
    man = es.get("mandato_diretoria") or {}
    estatuto = ""
    if es:
        estatuto = ("<h3>Finalidade esportiva</h3><table class=dados>" + _linhas([
            ("Onde o esporte aparece", LOCAL.get(fin.get("local"), fin.get("local"))),
            ("Artigo", fin.get("artigo")), ("Capítulo / seção", fin.get("titulo_secao")),
            ("Abertura do artigo", fin.get("frase_de_abertura")), ("Trecho", fin.get("trecho")),
            ("Página", fin.get("pagina")), ("Explicação", fin.get("explicacao"))]) + "</table>"
            + "<h3>Mandato da diretoria no estatuto</h3><table class=dados>" + _linhas([
                ("Duração", f"{man['duracao_anos']:g} anos" if man.get("duracao_anos") else None),
                ("Artigo", man.get("artigo")), ("Trecho", man.get("trecho")), ("Página", man.get("pagina")),
                ("Data fixa", man.get("data_fixa_trecho")), ("Prorrogação", man.get("prorrogacao_trecho"))])
            + "</table><h3>Registro do estatuto</h3><table class=dados>" + _linhas(
                [("Arquivo / páginas", " · ".join(x for x in [es.get("arquivo"), es.get("paginas")] if x)),
                 ("Data do estatuto", es.get("data_do_estatuto"))] + _registro(es.get("registro"))) + "</table>")
        num = es.get("numeracao_artigos") or {}
        if num.get("falhas"):
            estatuto += ("<h3>Numeração dos artigos</h3><ul>" + "".join(
                f"<li>{e(f.get('descricao'))}" + (f" <span class=mut>(p. {e(f['pagina'])})</span>" if f.get("pagina")
                                                  else "") + "</li>" for f in num["falhas"]) + "</ul>")

    a = regras_ia._ata_da_diretoria(L) or {}
    ata = ""
    if a:
        ata = "<table class=dados>" + _linhas([
            ("Arquivo / páginas", " · ".join(x for x in [a.get("arquivo"), a.get("paginas")] if x)),
            ("Tipo", TIPO_ATA.get(a.get("tipo"), a.get("tipo"))), ("Assembleia", a.get("data_assembleia")),
            ("Convocação (edital)", a.get("data_convocacao")), ("Período escrito", a.get("periodo_trecho")),
            ("Início do mandato", a.get("inicio_mandato")), ("Fim do mandato", a.get("fim_mandato")),
            ("Duração", f"{a['duracao_anos']:g} anos" if a.get("duracao_anos") else None),
            ("Quando entram em exercício", a.get("clausula_exercicio_trecho")),
            ("Prorrogação", a.get("prorrogacao_trecho"))]) + "</table><h3>Registro da ata</h3><table class=dados>" \
            + _linhas(_registro(a.get("registro"))) + "</table>"
    outras = [x for x in (L.get("atas") or []) if x is not a]
    if outras:
        ata += "<h3>Outras atas enviadas</h3><ul>" + "".join(
            f"<li>{e(TIPO_ATA.get(x.get('tipo'), x.get('tipo')))} de {e(x.get('data_assembleia'))} "
            f"<span class=mut>({e(x.get('arquivo'))})</span></li>" for x in outras) + "</ul>"

    campo = {"cartao_cnpj": "Cartão CNPJ", "estatuto": "Estatuto", "ata": "Ata"}
    como = {"texto": "pelo texto", "ia": "pela IA (1ª página)", "formato": "pelo formato",
            "sem triagem": "sem triagem"}
    tri = "".join(
        f"<tr><td><span class='pill {'ok' if t.get('passa') else 'pend'}'>{'Seguiu' if t.get('passa') else 'Ficou fora'}"
        f"</span></td><td><b>{e(campo.get(t.get('grupo'), t.get('grupo')))}</b> · <code>{e(t.get('nome'))}</code>"
        f"{' · ' + e(t['paginas']) + ' p.' if t.get('paginas') else ''}<br>{e(t.get('motivo'))}</td>"
        f"<td class=mut>{e(como.get(t.get('como'), t.get('como')))}</td></tr>" for t in (L.get("_triagem") or []))
    selos = "".join(f"<li>{e({'reconhecimento_firma': 'Reconhecimento de firma', 'autenticacao_copia': 'Autenticação de cópia'}.get(s.get('tipo'), 'Outro selo'))}"
                    f" <span class=mut>({e(_onde(s))})</span></li>" for s in (L.get("outros_selos") or []))
    obs = "".join(f"<li>{e(o)}</li>" for o in (L.get("observacoes") or []))
    fora = L.get("_fora") or []
    quando = data_leitura or dt.date.today().strftime("%d/%m/%Y")
    lido = " · ".join(x for x in [f"Lido pela IA ({info['modelo']})" if info.get("modelo") else "Lido pela IA",
                                  f"em {quando}"] if x)
    sub = " · ".join(x for x in [cidade_uf, f"CNPJ {cnpj}" if cnpj else None,
                                 f"inscrição em {data_inscricao:%d/%m/%Y}" if isinstance(data_inscricao, dt.date)
                                 else None] if x)
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conferência documental · {e(nome)}</title>
<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;700&family=Nunito+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main>
<header class=topo><div><p class=mut style="margin:0">CASE 2027 · conferência documental</p>
<h1>{e(nome)}</h1><p class=mut style="margin:4px 0 0">{e(sub)}</p></div>
<span class='pill grande {cls}'>{rot}</span></header>
<p class=mut>{e(lido)}. A IA só leu os documentos; quem decidiu cada item foram as regras do programa.
A decisão final é do mentor.</p>
<p class=legenda><span class='pill ok'>OK</span><span class='pill atencao'>Atenção</span><span class='pill confira'>Confira visualmente</span><span class='pill pend'>Pendência</span><span class='pill nao'>Não apto</span></p>

<h2>O que o sistema decidiu</h2>
<table class=itens><tbody>{''.join(itens)}</tbody></table>

<h2>O que a IA leu</h2>
<h3>Cartão CNPJ</h3>{'<table class=dados>' + cartao + '</table>' if cartao else '<p class=mut>Não encontrado.</p>'}
{estatuto or '<h3>Estatuto</h3><p class=mut>Não encontrado.</p>'}
<h3>Ata da diretoria</h3>{ata or '<p class=mut>Nenhuma ata que eleja ou empossa a diretoria.</p>'}

{'<h2>Triagem dos arquivos</h2><p class=mut>Antes da leitura completa, cada arquivo é conferido: o que foge do padrão (convite, pauta, contrato, planilha) não é lido.</p><table class=itens><tbody>' + tri + '</tbody></table>' if tri else ''}

<h2>Como a IA separou as páginas</h2>
<p class=mut>Cada página foi classificada pelo conteúdo, não pelo nome do arquivo.</p>
{_paginas(L)}
{'<h2>Selos que não são registro</h2><ul>' + selos + '</ul>' if selos else ''}
{'<h2>Arquivos que não abriram</h2><ul>' + ''.join(f'<li>{e(x)}</li>' for x in fora) + '</ul>' if fora else ''}
{'<h2>Outras observações da IA</h2><ul>' + obs + '</ul>' if obs else ''}
<footer>Relatório gerado pelo sistema CASE 2027 em {dt.date.today():%d/%m/%Y}. Para guardar em PDF, use
Imprimir &gt; Salvar como PDF no navegador. Contém dados da entidade: compartilhe só com a equipe do programa.</footer>
</main></body></html>"""
