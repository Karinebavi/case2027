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
- [ ] Fase 2 — Análise documental por IA
