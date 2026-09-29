# -*- coding: utf-8 -*-
"""
Os campos que o sistema precisa encontrar no CSV das inscrições.

Cada campo tem:
  grupo        -> só para organizar a tela em blocos
  chave        -> nome interno usado pelo sistema
  rótulo       -> nome amigável que aparece pra pessoa
  obrigatório  -> se o sistema precisa dele para funcionar
  dicas        -> pedaços de texto usados para ACHAR a coluna certa sozinho

Editar aqui é fácil e não mexe em nenhuma tela.
"""

# (grupo, chave, rótulo, obrigatório, dicas)
CAMPOS = [
    ("Identificação", "nome_entidade", "Nome da entidade", True, ["nome completo da entidade", "nome da entidade"]),
    ("Identificação", "cnpj", "CNPJ", True, ["cnpj"]),
    ("Identificação", "data_fundacao", "Data de fundação", True, ["fundação", "fundacao"]),
    ("Identificação", "uf", "Estado (UF)", True, ["estado"]),
    ("Identificação", "cidade", "Cidade", False, ["cidade"]),
    ("Identificação", "data_envio", "Data de envio da inscrição", False,
     ["data de envio", "carimbo de data", "submission", "timestamp", "data/hora"]),
    ("Identificação", "beneficiarios", "Número de beneficiários", False,
     ["beneficiários", "beneficiarios", "consegue atender"]),

    ("Eliminatórias (Sim/Não)", "estatuto", "Estatuto com finalidade esportiva", True, ["estatuto"]),
    ("Eliminatórias (Sim/Não)", "computador", "Computador com câmera e microfone", True, ["computador", "câmera", "camera"]),
    ("Eliminatórias (Sim/Não)", "internet", "Internet para as reuniões", True, ["internet"]),
    ("Eliminatórias (Sim/Não)", "disponibilidade", "Disponibilidade de 1h30 por semana", True, ["disponibilidade", "1h30"]),
    ("Eliminatórias (Sim/Não)", "modalidades", "Modalidades esportivas praticadas", False, ["modalidade"]),

    ("Perguntas de nota", "p18", "Elaboração — projetos que já escreveu", True, ["escreveu para pedir", "elabor"]),
    ("Perguntas de nota", "p19", "Execução — projetos que já colocou em prática", True, ["colocou em prática", "execu"]),
    ("Perguntas de nota", "p20_lie", "Situação na Lei de Incentivo ao Esporte (LIE)", False,
     ["lei de incentivo", "incentivo ao esporte", "(lie)", "lie"]),
    ("Perguntas de nota", "p21", "Equipe — nº de pessoas", True, ["pessoas atuam", "quantas pessoas", "colaboradores", "equipe"]),
    ("Perguntas de nota", "p22", "Receita bruta anual", True, ["receita"]),
    ("Perguntas de nota", "p23", "Infraestrutura administrativa", True, ["gestão e administra", "administrativa", "gestão e administração"]),
    ("Perguntas de nota", "p24", "Infraestrutura esportiva", True, ["execução das atividades", "infraestrutura esportiva", "local das atividades", "local para a execução"]),

    ("Canais digitais", "site", "Site (link)", True, ["possui site", "site"]),
    ("Canais digitais", "instagram", "Instagram (link)", True, ["instagram"]),
    ("Canais digitais", "facebook", "Facebook (link)", True, ["facebook"]),
    ("Canais digitais", "outra_rede", "Outra rede social (link)", False, ["outra rede"]),
]


def grupos():
    """Lista dos grupos, na ordem em que aparecem."""
    vistos = []
    for grupo, *_ in CAMPOS:
        if grupo not in vistos:
            vistos.append(grupo)
    return vistos
