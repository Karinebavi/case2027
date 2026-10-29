# Revisão automática do código

O GitHub confere o código do CASE 2027 sozinho, em duas camadas.

## 1. Verificação automática (grátis, sempre ligada)

Roda a cada envio para o GitHub e toda segunda-feira às 8h.
Arquivo: `.github/workflows/verificacao.yml`.

| O que confere | Para quê |
|---|---|
| **Erros de código** | Nome escrito errado, variável que não existe, bug comum |
| **Regras do projeto** | Testes em `testes/test_regras.py`: a Fase 1 nunca exclui, pendência vira "Atenção", pergunta ausente pontua 0, foto incompleta não vira "sem finalidade" |
| **Segurança do código** | Brechas conhecidas em Python |
| **Bibliotecas com falha** | Se alguma biblioteca usada (ex.: a que abre PDF e foto) tem falha de segurança já descoberta |
| **Chaves vazadas** | Se alguma senha ou chave foi parar no código — o repositório é público |

**Como ver o resultado:** no GitHub, aba **Actions**, ou o símbolo ao lado de cada envio:
verde = tudo certo · vermelho = algo precisa de atenção (clique para ver o quê).
Se ficar vermelho, o GitHub também avisa por e-mail.

## 2. Revisão pelo Claude (opcional, usa créditos)

Cada **proposta de mudança** (pull request) é lida pelo Claude **uma vez, quando é
aberta**. Correções enviadas depois não disparam outra revisão (cada revisão gasta
créditos). Para revisar de novo, ponha a etiqueta **revisar** na proposta
(lado direito da página da proposta, em *Labels*). Ele comenta na linha exata o que pode dar problema e termina com
"Pode entrar", "Pode entrar com ressalvas" ou "Precisa corrigir antes".
Ele conhece as regras do projeto (lê `docs/LOGICA-DO-SISTEMA.md`).
Arquivo: `.github/workflows/revisao-claude.yml`.

### Para ligar (uma vez só)

1. Abra https://github.com/Karinebavi/case2027/settings/secrets/actions
2. Clique em **New repository secret**.
3. Em **Name**, escreva exatamente: `ANTHROPIC_API_KEY`
4. Em **Secret**, cole a chave do Claude (a mesma da seção `[ia]` dos Secrets do
   Streamlit, ou crie uma nova em https://console.anthropic.com).
5. Clique em **Add secret**.

Sem essa chave, a revisão do Claude é pulada (sem erro) e só a verificação
gratuita roda.

**Custo:** cada revisão consome créditos da conta Anthropic. Dá para acompanhar o
gasto em https://console.anthropic.com. Só revisa propostas feitas dentro do
repositório — se alguém de fora abrir uma proposta, a chave não é usada.

### Como fica o fluxo

1. A mudança é feita num ramo à parte e vira uma **proposta de mudança** (pull request).
2. A verificação automática e o Claude comentam a proposta.
3. Você lê os comentários e aprova (botão **Merge**).
4. Só então a mudança entra no `main` — e o app online se atualiza sozinho.

## Rodar as verificações no computador

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
bandit -r . -x ./testes -ll -q
pip-audit -r requirements.txt
```
