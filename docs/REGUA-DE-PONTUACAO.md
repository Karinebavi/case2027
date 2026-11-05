# Régua de pontuação em uso no sistema — CASE 2027 (Etapa 1)

> **Em decisão (05/11/2026):** esta é a régua que o sistema aplica hoje. O
> `Formulario_CASE_2027_Etapa1_FINAL.docx` traz valores diferentes em 4 blocos
> (receita 26–100 mil = 10; infraestruturas cedidas = 9; digital: nenhum 8, só site 5,
> site e redes 4) e pontua a pergunta opcional da LIE (sem projeto 10, SLI 8,
> em captação 3, já executou 2). Falta a coordenação definir qual vale.

**Total: 70 pontos** — 7 blocos, cada um vale **até 10**.
A nota máxima fica no perfil **intermediário** de cada bloco (curva assimétrica):
quem é iniciante demais ou avançado demais pontua menos.

Fonte no sistema: `regras/pontuacao.py` (o teste `testes/test_regras.py` confere
que a soma dos máximos dá 70). Pergunta do formulário "CASE 2027 — Inscrição,
Etapa 1 — Nova versão" entre parênteses.

## 1 · Elaboração de projetos (21. já apresentou projeto para captar recursos?)
Conta quantos mecanismos incentivados foram marcados: Leis de Incentivo ao Esporte,
Leis de Incentivo à Cultura, Fundo da Infância (FIA), Fundo do Idoso,
PRONAS/PRONON (contam como um), Emenda Parlamentar. "Outra fonte" não conta.

| Mecanismos marcados | Pontos |
|---|---|
| Nenhum ("Nunca elaboramos") | 5 |
| **1** | **10** |
| 2 | 3 |
| 3 ou mais | 2 |

## 2 · Execução de projetos (22. já executou projeto com recursos aprovados?)
Mesma contagem e mesma tabela do bloco 1 (nenhum = 5 · **1 = 10** · 2 = 3 · 3+ = 2).

## 3 · Equipe (24. quantas pessoas atuam no dia a dia?)
| Resposta | Pontos |
|---|---|
| 1 ou 2 | 8 |
| **3 a 5** | **10** |
| 6 a 8 | 4 |
| 9 a 12 | 3 |
| Mais de 12 | 2 |

## 4 · Receita bruta anual (25.)
| Resposta | Pontos |
|---|---|
| Até R$ 25 mil | 5 |
| De R$ 25 mil a R$ 50 mil | 8 |
| **De R$ 51 mil a R$ 150 mil** | **10** |
| De R$ 151 mil a R$ 500 mil | 3 |
| Acima de R$ 500 mil | 2 |

## 5 · Infraestrutura administrativa (26.)
| Resposta | Pontos |
|---|---|
| Não possui espaço próprio para gestão administrativa | 6 |
| **Utiliza espaço cedido por parceiros ou instituições** | **10** |
| Possui sede administrativa alugada | 7 |
| Possui sede administrativa própria | 5 |

## 6 · Infraestrutura esportiva (27.)
| Resposta | Pontos |
|---|---|
| Não possui local para as atividades | 6 |
| **Utiliza instalações públicas ou cedidas por parceiros** | **10** |
| Possui espaço esportivo alugado | 7 |
| Possui espaço esportivo próprio | 5 |

## 7 · Presença digital (28. quais canais digitais tem hoje?)
| Canais marcados | Pontos |
|---|---|
| Site + alguma rede social | 6 |
| Só site | 8 |
| **Só redes sociais** (Instagram, Facebook ou outra) | **10** |
| Nenhum ("Não temos canais digitais") | 4 |

## O que NÃO tira ponto nem exclui (só selo "Atenção")
Sem computador com câmera/microfone, sem internet, sem 2h semanais, ou menos de
1 ano de funcionamento: a entidade pontua normalmente e entra no ranking com o
aviso. O filtro de quem não segue é a conferência documental (Fase 2).

**Desempate:** entidade mais antiga (data de fundação anterior) fica à frente.
