# Sistema CASE 2027

Ferramenta interna do Instituto Imaginação para a seleção do CASE 2027.
A equipe sobe o CSV das inscrições; o sistema valida, pontua e classifica.

## Como está organizado (blocos)

```
CASE 2027/
├── app.py            → esqueleto: login + navegação (junta as telas)
├── telas/            → o que a pessoa VÊ (uma tela por arquivo)
│   ├── login.py
│   ├── importar.py
│   ├── resultado.py
│   └── painel.py
├── regras/           → a LÓGICA (sem tela) — reaproveitável
│   └── auth.py
├── base/             → campos do formulário + CSV de exemplo (próximos passos)
├── tema.py           → cores e fontes (a "cara")
├── assets/           → logo do Instituto (assets/logo.png)
├── .streamlit/       → tema + senha (secrets.toml)
├── requirements.txt  → bibliotecas
└── .gitignore        → protege senha e dados reais
```

Regra de ouro: **telas** (o que se vê) ficam separadas das **regras** (a lógica).

## Como rodar no seu computador

```
pip install -r requirements.txt
streamlit run app.py
```

Abre em http://localhost:8501. Senha de teste: **case2027**

## Como configurar a senha real

1. Renomeie `.streamlit/secrets.toml.exemplo` para `.streamlit/secrets.toml`
2. Troque o valor de `senha_app` pela senha real
3. No Streamlit Community Cloud, a senha vai em **Settings > Secrets**

> Configure a senha real **antes** de divulgar o link — senão a senha de teste continua valendo.

## Onde você completa (marcado com TROCAR)

- **Senha real:** `.streamlit/secrets.toml`
- **Logo:** salve como `assets/logo.png`
- **Cores/fonte:** `.streamlit/config.toml` e `tema.py`

## Status das etapas

- [x] Passo 0 — Esqueleto: login + navegação das 4 telas
- [ ] Passo 1 — Importar CSV
- [ ] Passo 2 — Validação
- [ ] Passo 3–4 — Pontuação e classificação
- [ ] Passo 5 — Painel e download
- [x] Fase 2 — Conferência documental automática (sem IA paga)

## Conferência documental (tela 4)

O mentor sobe Cartão CNPJ, Estatuto(s) e Ata(s). O sistema lê o texto digital
ou faz OCR (Tesseract em português; a página vira imagem pelo pypdfium2, sem
poppler) e aplica as regras da *Especificação de conhecimento — Conferência
Documental LIE* (Trilha Gestão):

- `leitura/texto.py` — texto por página + OCR (e 2ª leitura dos carimbos)
- `leitura/documento.py` — páginas, artigos numerados, identidade da entidade
- `leitura/datas.py` — datas numéricas e por extenso, períodos de mandato
- `leitura/extratores.py` — campos do cartão, estatuto e ata (com artigo e página)
- `leitura/regras_lie.py` — regras HAB, REG e REP (status OK / ATENÇÃO / PENDÊNCIA / BLOQUEANTE / INFO)
- `leitura/parecer.py` — parecer no formato do modelo (resultado, tabelas, ajustes)

Parâmetros que dependem do edital (tempo mínimo, recência do cartão, CNAEs
esportivas…) ficam em `CONFIG_PADRAO` (`leitura/regras_lie.py`).

A regressão com dossiês reais (`testes/casos_reais.py`) fica só na máquina
(não vai ao GitHub, pois cita entidades reais). Rodar com
`CASE2027_PDFS="pasta1;pasta2" python testes/casos_reais.py`.
