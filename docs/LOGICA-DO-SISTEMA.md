# CASE 2027 — A lógica do sistema (fonte da verdade)

> Este documento descreve, em linguagem simples, **o que o sistema faz e em que ordem**.
> Ele é o combinado oficial do projeto. Se o sistema fizer algo diferente daqui, é o
> sistema que está errado — não o documento.

## Para que serve

Ajudar os **mentores** a **classificar, selecionar e entrar em contato** com as
entidades (OSCs) inscritas no CASE — um projeto esportivo incentivado. As entidades
se inscrevem no **Wix**: preenchem as informações e anexam os documentos. O sistema
puxa essas inscrições, pontua, classifica e conduz o funil até as selecionadas.

---

## O funil, em 5 fases

```
Inscrições (Wix)
      │
  [ FASE 1 ]  Pontuação e classificação automática  ── ninguém é excluído
      │                                                  (telas 1 e 2)
      ▼
  [ FASE 2 ]  Conferência documental (só quando o mentor manda ler)
      │                                                  (tela 3)
      ▼
  [ FASE 3 ]  Relatório para o patrocinador (ele marca o interesse)
      │                                                  (tela 4)
      ▼
  [ FASE 4 ]  Entrevistas (cartão com contato)
      │                                                  (tela 5)
      ▼
  [ FASE 5 ]  As selecionadas finais (cartão + documentos + contato)
                                                         (tela 6)
```

---

### FASE 1 — Pontuação e classificação  ·  *telas 1 (Importar) e 2 (Resultado)*

- O sistema puxa as inscrições do Wix e **pontua todas** (0 a 70 pontos, em 7 blocos).
- Classifica **da maior nota para a menor**, num ranking único nacional.
- **REGRA DE OURO: ninguém é excluído aqui.** Todas entram no ranking e pontuam
  normalmente. Quem tem alguma pendência (sem computador/internet/disponibilidade
  para a mentoria online, ou menos de 1 ano de funcionamento) **não sai da lista** —
  recebe apenas um **selo "Atenção"** para o mentor olhar. A nota mais baixa já a
  coloca mais embaixo naturalmente.
- **Tudo à vista:** o quadro mostra cidade, nota, **em quais blocos** ela ganhou os
  pontos e o selo de atenção — sem precisar abrir uma por uma.
- O **filtro de verdade** de quem não segue é a Fase 2 (documental), não a Fase 1.

### FASE 2 — Conferência documental  ·  *tela 3 (Documental)*

- **Só começa quando o mentor pede.** Não roda sozinha.
- Analisa os 3 documentos de cada entidade e devolve, de forma clara e direta:
  - **Cartão CNPJ:** tem mais de 1 ano? Foi emitido há pouco tempo (recente)?
  - **Estatuto:** o esporte está na finalidade? **Em qual artigo** (ex.: Art. 2º),
    com o **trecho**. Está registrado em cartório?
  - **Ata:** a diretoria está **vigente**? Registrada em cartório?
- As que não passam na documental ficam **bem sinalizadas** (quem e **por quê**).
- **Como a tela funciona:** um **quadro** com as 30 e um quadradinho colorido por
  documento; um botão **analisa sozinho, uma por uma**, as que têm documentos no Wix
  (o resultado fica salvo — não precisa refazer); ao clicar numa linha, **três
  cartões** (Cartão, Estatuto, Ata) e as ações: aprovar, pedir documento, excluir.
- **Ligação com o Wix:** a entidade preenche a inscrição e, no fim, segue um link
  para o **formulário de documentos**. Esse formulário **precisa pedir o CNPJ** —
  é por ele que o sistema liga os documentos à inscrição certa (depois tenta o
  e-mail do responsável e, por último, o nome completo).

### FASE 3 — Relatório para o patrocinador  ·  *tela 4 (Análises)*

- Gera o relatório das **melhores colocadas** que passaram na documental.
- Esse relatório vai ao **patrocinador**, que marca **quais tem interesse** em seguir.

### FASE 4 — Entrevistas  ·  *tela 5 (Entrevistas)*

- Cada entidade aparece como **cartão** com telefone e contato, para o mentor ligar.
- O mentor registra o **resultado** da entrevista (compareceu, parecer).
- Não comparecer / parecer negativo exclui e **a próxima da fila entra** (repescagem).

### FASE 5 — As selecionadas  ·  *tela 6 (Fichas)*

- As **vagas** finais (padrão 10) saem aqui, cada uma em um **cartão completo**:
  dados, **documentos**, contato (e-mail/WhatsApp já prontos) — tudo organizado.

> **Tela 7 (Dashboard)** não é uma fase: é só a **visão geral** (números e gráficos).

---

## Princípios que não mudam

1. **Fase 1 nunca exclui.** Pendência é **observação**, não eliminação.
2. **O filtro real é a documental (Fase 2).**
3. **Tudo à vista.** O mentor enxerga o porquê da nota sem abrir uma por uma.
4. **A palavra final é do mentor.** O sistema sugere; ele confirma.
5. **Dados pessoais são protegidos.** Nada de CNPJ/nomes/documentos expostos fora do sistema.

## Glossário dos selos

| No sistema | O que quer dizer |
|---|---|
| **Classificada** | Dentro do número de vagas, no ranking. |
| **Fila de espera** | No ranking, abaixo da linha das vagas. |
| **Atenção** | Tem uma pendência sinalizada (não exclui; confere na Fase 2). |
| **Fase 2 = Sim** | Está no grupo que vai à conferência documental. |
| **Excluída (documental/entrevista)** | Saiu nessas fases, com o motivo registrado. |
