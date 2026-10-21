# Sincronizar inscrições do Wix

Liga o botão **"Sincronizar com o Wix"** na aba *Importar*: ele puxa as
inscrições do formulário direto pela API do Wix e soma à base — o mesmo que o
upload de CSV faz, só que automático. O código já está pronto (`regras/wix.py`);
falta só a **chave da API** e o **ID do site** no Secrets.

Sem a seção `[wix]` no Secrets, o botão fica desligado e nada muda (continua
valendo o upload de CSV).

---

## O que vem e o que NÃO vem

- **Vêm:** as respostas do formulário (os dados da inscrição), que viram as
  colunas que o sistema já conhece.
- **NÃO vêm os documentos.** No formulário final, os documentos (cartão,
  estatuto, ata) são enviados por um **link externo** (pergunta 32), não
  anexados no formulário do Wix. Então não há o que puxar do Wix para os
  documentos — eles continuam sendo conferidos na aba Documental, a partir de
  onde esse link guarda os arquivos (ex.: uma pasta no Drive).
  - Se um dia quiser que os documentos também venham automáticos, a forma é
    trocar a pergunta 32 por um **campo de upload de arquivo** dentro do Wix
    Forms — aí dá para puxar junto.

## Pré-requisitos no Wix

- O formulário precisa ser do **Wix Forms** (app instalado no site). A API de
  submissões funciona em sites **Wix Studio / Editor X** com o Wix Forms.
- Se as inscrições forem feitas por outro tipo de formulário (um app de
  terceiros, por exemplo), esta sincronização não se aplica — me avise que a
  gente vê outro caminho.

---

## Passo 1 — Pegar a API key e o Site ID

1. **API key:** entre em **manage.wix.com** → **API Keys Manager** (Gerenciador
   de chaves de API) → crie uma chave com permissão de **ler formulários e
   submissões** (Forms / Read Submissions). Copie a chave (aparece uma vez).
2. **Site ID:** no painel do site, em **Configurações** → há o ID do site
   (ou pegue pela URL do editor/dashboard). É um código no formato
   `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`.
3. **Nunca** cole a chave em chat/e-mail/código — ela vai só no Secrets.

## Passo 2 — Configurar

No `.streamlit/secrets.toml` (local) e nos **Secrets do Streamlit** (nuvem):

```toml
[wix]
api_key = "COLE-A-API-KEY"
site_id = "COLE-O-SITE-ID"
# opcionais (se houver mais de um formulário no site):
# form_id = "ID-DO-FORMULARIO"
# form_nome = "Inscrição"
```

## Passo 3 — Testar

1. Abra o app → **1 · Importar**.
2. Em **"Sincronizar com o Wix"**, clique em **"Buscar inscrições do Wix"**.
3. Aparece quantas inscrições vieram e de qual formulário. Confira o mapeamento
   e clique em **"Somar à base"**.
4. As inscrições entram na base igual ao CSV (sem duplicar — o CNPJ é a chave).

---

## Se der erro

- **"Sincronização com o Wix desligada"** → a seção `[wix]` não foi lida.
  Confira o `secrets.toml` (local) ou os Secrets do Streamlit (nuvem).
- **HTTP 403** → a API key não tem permissão, ou falta o `site_id`, ou a chave
  não é do site certo. Gere a chave com permissão de ler submissões.
- **"Permissions for given namespace not found"** → o app **Wix Forms** não
  está instalado nesse site. Instale-o ou confirme que o formulário é do Wix
  Forms.
- **"Há vários formulários — defina form_id"** → o site tem mais de um
  formulário; copie o ID mostrado e ponha em `form_id` no Secrets (ou use
  `form_nome`).
- **Veio inscrição mas faltou alguma coluna** → o app pede para você indicar a
  coluna certa na hora (como no CSV). Se acontecer muito, me avise o nome exato
  da pergunta no Wix que eu ajusto o reconhecimento.

---

## Como funciona por dentro (para quem for mexer)

- `regras/wix.py`:
  - `ativo()` — liga/desliga pela presença de api_key + site_id.
  - `listar_formularios()` — `GET /form-schema-service/v4/forms`.
  - `sincronizar()` — resolve o formulário, lê o schema (para traduzir os
    campos em rótulos), percorre as submissões paginadas
    (`POST /form-submission-service/v4/submissions/namespace/query`) e devolve
    um DataFrame no formato do CSV.
- `telas/importar.py`:
  - `_processar_df(...)` — núcleo compartilhado (mapeia → confirma → soma).
  - `_sincronizar_wix()` — o botão.
- Autenticação: header `Authorization: <api_key>` + `wix-site-id: <site_id>`.

Referências: dev.wix.com — "Make REST API Calls with an API Key" e
"Read Forms and Submissions".
