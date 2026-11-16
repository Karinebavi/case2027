# -*- coding: utf-8 -*-
"""Trava da leitura dos documentos: bloqueada por padrão, liberada só por decisão explícita."""
from regras import liberacao, nuvem


def test_sem_nada_guardado_fica_bloqueada(monkeypatch):
    monkeypatch.setattr(nuvem, "ativo", lambda: True)
    monkeypatch.setattr(nuvem, "ler", lambda chave: None)
    assert liberacao.liberada() is False


def test_se_o_banco_falhar_fica_bloqueada(monkeypatch):
    def falha(chave):
        raise RuntimeError("banco fora")
    monkeypatch.setattr(nuvem, "ativo", lambda: True)
    monkeypatch.setattr(nuvem, "ler", falha)
    assert liberacao.liberada() is False


def test_liberar_e_bloquear_ficam_guardados_e_no_historico(monkeypatch):
    guardado, historico = {}, []
    monkeypatch.setattr(nuvem, "ativo", lambda: True)
    monkeypatch.setattr(nuvem, "gravar", lambda itens: guardado.update(itens))
    monkeypatch.setattr(nuvem, "ler", lambda chave: guardado.get(chave))
    monkeypatch.setattr(nuvem, "registrar", lambda acao, detalhe=None: historico.append(acao))
    liberacao.definir(True, "equipe")
    assert liberacao.liberada() is True and liberacao.estado()["por"] == "equipe"
    liberacao.definir(False, "equipe")
    assert liberacao.liberada() is False
    assert historico == ["liberar_leitura", "bloquear_leitura"]
