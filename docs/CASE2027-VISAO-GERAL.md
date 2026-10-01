# CASE 2027 — Visão Geral do Sistema

Documento de referência para a equipe. Suba na seção **Contexto** do Projeto.

## O que é
Sistema interno do Instituto Imaginação para a seleção de OSCs (organizações da sociedade civil)
esportivas no ciclo CASE 2027. Ele recebe as inscrições exportadas do formulário (Wix), pontua
cada entidade por uma régua objetiva, classifica num ranking único nacional e conduz a seleção
pelas fases seguintes (documental, entrevista e fichas finais). É um app web feito em Streamlit,
de uso interno, com acesso por senha.

## As telas (abas) e o funil
O menu lateral segue a ordem do processo:

1. **Importar** — sobe o CSV das inscrições. A base **acumula** a cada arquivo (não duplica: o CNPJ
   é a chave; a versão mais recente substitui a antiga). Dá para baixar a base e zerar.
2. **Resultado** — todas as organizações em ordem de nota, com a situação em cor e o motivo de quem
   não segue. Define **Vagas finais** (padrão 10) e **quantas vão à Fase 2** (padrão as 30 melhores).
   Exporta a planilha de pontuação (com a memória de cálculo: pontos de cada bloco).
3. **Análises** — as 30 da Fase 2 já com a coluna de **interesse do patrocinador** (marca no app ou
   sobe a planilha que o patrocinador preencheu). O interesse apenas destaca, não elimina.
4. **Documental (Fase 2)** — o mentor sobe Cartão CNPJ, Estatuto e Ata; o sistema **lê os PDFs
   (inclusive escaneados, com OCR)** e monta um parecer que pré-marca a conferência. O mentor
   confirma e **aprova** ou **exclui com motivo**. Excluiu uma, a próxima do ranking entra sozinha
   (repescagem automática). As excluídas vão para o Banco de descartadas.
5. **Entrevistas (Fase 3)** — as aprovadas na documental. Aloca o mentor responsável, segue o roteiro
   de 15 minutos (parecer por bloco), registra se compareceu e decide. Não comparecer ou parecer
   negativo exclui e repesca a próxima.
6. **Fichas (Fase 4)** — as selecionadas aparecem como mini-cartões com toda a informação: pontuação,
   dados, interesse do patrocinador, mentor e resultado da entrevista.
7. **Dashboard** — visão geral em gráficos: situação, notas, regiões, mapa do Brasil, dias com mais
   inscrições, nuvem de cidades e o perfil das OSCs (uma pergunta por gráfico).

## Pontuação (Fase 1) — a régua
Sete blocos, total máximo **70 pontos**, com curva assimétrica (a nota máxima fica no perfil
intermediário de cada bloco e cai para os dois lados):

- **Elaboração** e **Execução** — número de mecanismos de incentivo já escritos/executados.
- **Equipe** — faixa de pessoas que atuam (alvo: 3 a 5).
- **Receita** — faixa de receita bruta anual (alvo: R$ 101 mil a R$ 250 mil).
- **Infra administrativa** — alvo: espaço cedido por parceiros.
- **Infra esportiva** — alvo: instalações públicas/cedidas.
- **Presença digital** — combinação de site e redes sociais.

**Eliminatórias** (zeram a nota → Inelegível): estatuto com finalidade esportiva, computador com
câmera/microfone, internet, disponibilidade de 1h30 por semana, trabalhar com modalidades esportivas
e mais de 1 ano de funcionamento. **Corte de teto** (→ Fora do perfil): perfil muito avançado
(3 ou mais mecanismos tanto elaborados quanto executados). O **motivo** de cada caso aparece na
tabela e na ficha da entidade.

## Conferência documental (Fase 2) — o que o sistema checa
O sistema lê os três documentos e aponta os pontos por gravidade (impede a aprovação / falta
providenciar / conferir com atenção). As regras confirmadas com a coordenação:

- **Cartão CNPJ:** emitido pela Receita Federal; mais de 1 ano de funcionamento (fundação e
  atualizações cadastrais, até a data de hoje); situação cadastral ativa; recência do cartão;
  natureza jurídica compatível com OSC; endereço confere com o estatuto.
- **Estatuto:** finalidade esportiva **como fim** (não como meio) — o sistema indica em quais artigos
  ela aparece; registrado em cartório (o selo às vezes está no verso ou em outra página, então vira
  pendência "confira o verso", não rejeição automática); etiqueta/certidão com data e selo exige
  **atenção redobrada**.
- **Ata de eleição/posse:** registrada em cartório e é mesmo de posse/eleição; mandato vigente
  (não vencido) e alerta se perto de vencer; duração do mandato bate com o estatuto; **averbações
  faltantes levam à rejeição**; parentesco na diretoria e datas incoerentes geram atenção.

Não são verificados (decisão da coordenação): CNAE esportiva, mandato vitalício, "quem representa/
assina", rito/convocação da assembleia, composição e acúmulo de cargos da diretoria, presidente
empossado.

A leitura funciona com PDFs de texto e escaneados. Para scans de baixo contraste ou girados, o
sistema corrige a orientação e binariza a imagem antes de ler. Scans realmente ilegíveis são
sinalizados para conferência manual. O OCR usa o Tesseract (idioma português).

## Arquitetura (onde está cada coisa)
- `app.py` — login e navegação entre as telas.
- `telas/` — uma tela por arquivo (`importar`, `resultado`, `analises`, `documental`, `entrevistas`,
  `fichas`, `dashboard`), mais `_ui` (peças visuais) e `_calculo` (ponte com as regras + estado).
- `regras/` — lógica de negócio: `pontuacao`, `classificacao`, `funil` (pool + repescagem),
  `processo` (estado por CNPJ), `base_dados` (base acumulada), `normalizacao`, `exportacao`,
  `regiao`, `cnpj`, `validacao`, `geo`, `nuvem` (Supabase).
- `leitura/` — motor de documentos: `texto` (extração + OCR), `documento` (classifica o PDF),
  `extratores`, `conferencia`, `parecer`, `regras_lie` (as regras da LIE), `cnpj_online`, `datas`.
- `base/` — `campos.py` (campos esperados no CSV) e `brasil_uf.geojson` (mapa).

## Como rodar
1. Instalar dependências: `pip install -r requirements.txt` (e o Tesseract-OCR para ler escaneados).
2. Rodar: `python -m streamlit run app.py --server.port=8593 --server.headless=true`.
3. Abrir `http://localhost:8593` e entrar com a senha de acesso.

## Guarda dos dados (LGPD)
- A base de inscrições e o estado do processo ficam na nuvem (Supabase) quando configurado, ou nesta
  máquina. **Nada disso vai para o Git** (está no `.gitignore`).
- Documentos reais (PDFs) não são guardados pelo app — na base fica só o resumo do parecer.
- Ao testar com documentos reais, trabalhe em pasta temporária e apague depois.

## Decisões e pendências conhecidas
- Ranking **nacional único** (sem cota por região). Vagas finais = 10; pool da Fase 2 = 30.
- Hospedagem gratuita pretendida: Streamlit Community Cloud.
- **Segurança:** o repositório é público e a senha está no código — deixar privado e mover a senha
  para os Secrets antes de abrir para a equipe.
- **Visual:** falta aplicar o logo oficial (PNG/SVG) e as cores oficiais (hoje azul provisório #1F4E79).
- Pequenos ajustes em aberto no classificador de atas de eleição e na checagem de cartório de posse.
