# -*- coding: utf-8 -*-
"""
Classificação — ranking único nacional por nota (sem cota por região).
Desempate: organização mais antiga (data de fundação anterior).

Devolve, para cada inscrição, a 'Posição' no ranking e a 'Situação' final:
  Classificada    -> dentro do número de vagas
  Fila de espera  -> passou nas regras, mas ficou acima da linha de corte
  Fora do perfil  -> caiu no corte de teto
  Inelegível      -> falhou uma eliminatória ou tem menos de 1 ano
"""
from datetime import date

from regras import pontuacao as pont


def classificar(scored, vagas):
    df = scored.copy()

    def chave(i):
        d = pont.parse_data(df.loc[i, "_data_fundacao"]) or date.max
        return (-int(df.loc[i, "Nota"]), d)  # maior nota primeiro; mais antiga primeiro

    em_classificacao = [i for i in df.index if df.loc[i, "Status"] == "Em classificação"]
    ordem = sorted(em_classificacao, key=chave)

    df["Posição"] = None
    df["Situação"] = df["Status"]  # começa com Inelegível / Fora do perfil
    for posicao, i in enumerate(ordem, start=1):
        df.loc[i, "Posição"] = posicao
        df.loc[i, "Situação"] = "Classificada" if posicao <= vagas else "Fila de espera"
    return df


def classificar_fase2(scored, verdicts, vagas):
    """
    3ª classificação (Fase 2), a partir das conferências de documentos:
      - exclui as conferidas com documento NÃO conforme;
      - as com esporte no Instagram ganham peso 2x na nota;
      - re-ranqueia o que sobrou (as excluídas abrem espaço para a fila);
      - o corte continua no número de vagas.
    Só entram as que estavam 'Em classificação' na Fase 1.
    """
    em = scored[scored["Status"] == "Em classificação"].copy()

    def excluida(cnpj):
        v = verdicts.get(cnpj, {})
        return bool(v.get("conferida") and not v.get("documentos_ok"))

    def nota_fase2(linha):
        v = verdicts.get(linha["CNPJ"], {})
        base = int(linha["Nota"])
        if v.get("conferida") and v.get("documentos_ok") and v.get("tem_esporte"):
            return base * 2
        return base

    em["Excluída"] = em["CNPJ"].map(excluida)
    em["Nota Fase 2"] = em.apply(nota_fase2, axis=1)

    def chave(i):
        d = pont.parse_data(em.loc[i, "_data_fundacao"]) or date.max
        return (-int(em.loc[i, "Nota Fase 2"]), d)

    ordem = sorted([i for i in em.index if not em.loc[i, "Excluída"]], key=chave)

    em["Posição Fase 2"] = None
    em["Situação Fase 2"] = "—"
    em.loc[em["Excluída"], "Situação Fase 2"] = "Excluída (documento)"
    for posicao, i in enumerate(ordem, start=1):
        em.loc[i, "Posição Fase 2"] = posicao
        em.loc[i, "Situação Fase 2"] = "Classificada" if posicao <= vagas else "Fila de espera"
    return em
