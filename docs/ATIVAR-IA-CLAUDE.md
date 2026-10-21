# Ativar a análise de documentos por IA (Claude)

Este guia liga a **Leitura por IA** da aba *Documental*. O código já está pronto
(`leitura/ia.py` + integração em `telas/documental.py`); falta só a **chave da API**
e a **configuração**. Não precisa mexer no código.

Enquanto não for configurado, a tela mostra *"Leitura por IA desligada"* e o
sistema funciona normalmente com as regras de sempre.

---

## Como funciona (resumo)

- Depois do OCR ler os PDFs, a IA recebe **o texto já extraído** e devolve uma
  leitura estruturada: finalidade esportiva (+ artigo + trecho), mandato,
  registro em cartório, resumo e pontos de atenção.
- A IA **não decide sozinha**: as regras determinísticas continuam valendo e o
  mentor confirma. A IA é apoio.
- Ela roda **só quando o mentor clica em "Ler com IA"** (controle de custo).

## Custo

A conferência só roda nas ~30 do pool, uma vez por ciclo. Com o modelo
`claude-haiku-5-5`, conferir as 30 custa cerca de **US$ 0,10** (centavos).
Mesmo o modelo mais caro fica em poucos dólares. **Ponha um teto de gasto** na
conta (passo 1) para não haver surpresa.

## LGPD

A API da Anthropic **não treina** com os dados enviados. Para garantia extra,
dá para solicitar **zero-retenção** à Anthropic. Mesmo assim, só é enviado o
**texto necessário** dos documentos. (A alternativa 100% local é o Ollama —
ver o fim deste guia.)

---

## Passo 1 — Conta, crédito e teto de gasto

1. Acesse **console.anthropic.com** e crie/entre na conta.
2. Em **Billing** (Faturamento), adicione um crédito pequeno (ex.: US$ 5).
3. Ainda em Billing, defina um **limite de gasto mensal** (ex.: US$ 5) para
   nunca passar disso.

## Passo 2 — Criar a chave da API

1. No console, vá em **API Keys** → **Create Key**.
2. Dê um nome (ex.: `case2027`) e **copie a chave** (começa com `sk-ant-...`).
   Guarde — ela só aparece uma vez.
3. **Nunca** cole essa chave em chat, e-mail ou no código. Ela vai só no Secrets.

## Passo 3 — Configurar LOCAL (no seu computador)

1. Na pasta do projeto, abra `.streamlit/secrets.toml`
   (se não existir, copie de `.streamlit/secrets.toml.exemplo` e renomeie para
   `secrets.toml`). Esse arquivo **nunca** vai para o GitHub.
2. Adicione (ou ajuste) a seção `[ia]`:

   ```toml
   [ia]
   provedor = "claude"
   modelo = "claude-haiku-5-5"
   anthropic_api_key = "sk-ant-COLE-A-SUA-CHAVE-AQUI"
   ```

3. Instale o pacote da Anthropic (uma vez):

   ```bash
   pip install anthropic
   ```

   (Na nuvem isso é automático — já está no `requirements.txt`.)

## Passo 4 — Configurar na NUVEM (Streamlit Community Cloud)

1. Abra o painel do app em **share.streamlit.io** → seu app → **Settings** → **Secrets**.
2. Cole as mesmas linhas da seção `[ia]` (com a chave real) e salve.
3. O app reinicia sozinho. Pronto.

> Observação: a conferência de documentos lida com dados reais. O ideal por
> LGPD é fazer essa etapa **rodando o app local**. A IA da nuvem funciona nos
> dois casos, mas evite subir documentos reais para o app público sem necessidade.

## Passo 5 — Testar

1. Abra o app, entre, e vá em **3 · Documental**.
2. Escolha uma organização e suba os 3 PDFs (ou use **"Testar com exemplos"**).
3. Role até **"Leitura por IA (apoio)"** e clique em **"Ler com IA"**.
4. Em alguns segundos aparece o cartão com a leitura da IA. Se mudar os
   documentos, clique em **"Reler com IA"**.

---

## Se der erro

- **"Leitura por IA desligada"** → a seção `[ia]` não foi lida. Confira se está
  no `secrets.toml` certo (local) ou nos Secrets do Streamlit (nuvem), e se
  `provedor = "claude"`.
- **"O pacote 'anthropic' não está instalado"** → rode `pip install anthropic`
  (local). Na nuvem, confirme que `anthropic` está no `requirements.txt`.
- **Erro de autenticação / 401** → a chave está errada ou foi revogada. Gere
  outra no console.
- **Erro de crédito / 400 "credit balance"** → adicione crédito no Billing.
- **"respondeu num formato inesperado"** → tente **"Tentar de novo"**; se
  persistir, troque o `modelo` para `claude-sonnet-5-5` (um pouco mais caro,
  mais estável).

## Trocar o modelo

No `[ia]`, mude só a linha `modelo`:

- `claude-haiku-5-5` — mais barato (centavos). Padrão.
- `claude-sonnet-5-5` — mais preciso, ainda barato (~US$ 1,80 as 30).
- `claude-opus-5-5` — o melhor, ~US$ 3,60 as 30.

## Alternativa grátis e local (sem a nuvem)

Se preferir não usar a API paga, dá para rodar **grátis** com o **Ollama** na
sua máquina (nada sai do computador):

1. Instale o Ollama: `winget install Ollama.Ollama`
2. Baixe um modelo: `ollama pull qwen2.5:7b`
3. No `[ia]`, use:

   ```toml
   [ia]
   provedor = "ollama"
   modelo = "qwen2.5:7b"
   ```

Funciona **só rodando o app local** (não na nuvem) e é mais lento (CPU), mas é
grátis e 100% privado.

---

## Onde está o código (para quem for mexer)

- `leitura/ia.py` — o módulo. Lê a config de `st.secrets["ia"]`, monta o pedido
  e chama o provedor. Funções: `disponivel()`, `provedor_ativo()`,
  `analisar(arquivos, nome_entidade)` → `(resultado_dict, erro_str)`.
- `telas/documental.py` — função `_leitura_ia(...)` renderiza o botão e o cartão.
- O prompt e o formato JSON esperado estão em `leitura/ia.py` (`_SISTEMA` e
  `_FORMATO`).
