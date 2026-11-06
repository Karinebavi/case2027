# -*- coding: utf-8 -*-
"""
Atualização das inscrições a partir do Wix — usada pelo robô do GitHub (de 2 em 2
horas, robo/atualizar_inscricoes.py) e pelo botão "Atualizar agora" do sistema.

Só soma à base o que ainda não está nela (pelo id do envio no Wix): rodar várias
vezes não duplica. Não usa IA e não lê documentos.
"""
import datetime as dt
import json

from regras import base_dados, mapeamento, normalizacao, nuvem, wix

CHAVE_STATUS = "robo/ultima_execucao"
ESSENCIAIS = ("nome_entidade", "cnpj")


def ultima():
    """Último resultado da atualização automática ({quando, ok, novas, ...}) ou None."""
    if not nuvem.ativo():
        return None
    try:
        txt = nuvem.ler(CHAVE_STATUS)
        return json.loads(txt) if txt else None
    except Exception:
        return None


def _status(dados, simular):
    if not simular and nuvem.ativo():
        nuvem.gravar({CHAVE_STATUS: json.dumps(dados, ensure_ascii=False)})


def atualizar(simular=False, origem="robô"):
    """Busca no Wix e soma à base. Devolve um dict com o resumo (só contagens)."""
    agora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    r = {"quando": agora, "origem": origem, "ok": False}
    if not wix.ativo():
        return {**r, "erro": "Wix não configurado"}
    if not nuvem.ativo():
        return {**r, "erro": "banco não configurado"}
    try:
        df, _info = wix.sincronizar()
    except Exception as erro:
        r.update(erro=f"não consegui buscar no Wix ({type(erro).__name__})")
        _status(r, simular)
        return r
    r["no_wix"] = len(df)
    if len(df) == 0:
        r.update(ok=True, novas=0, atualizadas=0)
        _status(r, simular)
        return r
    mapa = mapeamento.auto_map(list(df.columns))
    faltam = [c for c in ESSENCIAIS if not mapa.get(c)]
    if faltam:
        r.update(erro="o formulário mudou: não achei o nome ou o CNPJ — nada foi gravado")
        _status(r, simular)
        return r
    novos = normalizacao.normalizar(df, mapa)
    base = base_dados.carregar()
    if "id_envio" in base.columns and "id_envio" in novos.columns:
        ja = set(base["id_envio"].astype(str).str.strip()) - {""}
        novos = novos[~novos["id_envio"].astype(str).str.strip().isin(ja)]
    r["pendentes"] = len(novos)
    if len(novos) == 0:
        r.update(ok=True, novas=0, atualizadas=0, total_base=len(base))
        _status(r, simular)
        return r
    final, cnpjs_novos, n_atualizados = base_dados.acumular(base, novos)
    r.update(ok=True, novas=len(cnpjs_novos), atualizadas=n_atualizados, total_base=len(final))
    if simular:
        return r
    base_dados.salvar(final)
    nuvem.registrar("atualizar_wix", {k: r.get(k) for k in ("origem", "no_wix", "novas", "atualizadas",
                                                             "total_base")})
    # Confere o CNPJ das que chegaram (dígito, Receita, confirmação) e guarda as sugestões.
    try:
        from regras import cnpj
        diags = cnpj.conferir_base(final, so_novas=True)
        cnpj.salvar_diagnosticos(diags)
        r["cnpj_a_conferir"] = sum(1 for d in diags.values() if d.get("status") in cnpj.A_CONFERIR)
    except Exception as erro:  # a conferência do CNPJ nunca impede a inscrição de entrar
        print(f"[atualizacao] conferência do CNPJ falhou ({type(erro).__name__})")
    _status(r, simular)
    r["cnpjs_novos"] = cnpjs_novos  # só para a tela marcar as novas; o robô não imprime
    return r
