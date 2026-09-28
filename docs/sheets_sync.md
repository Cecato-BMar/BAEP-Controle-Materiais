# Sincronização Google Sheets ↔ material_belico

Configuração da base (Service Account + variáveis de ambiente + Coolify).
A lógica de pull/push será implementada em fase seguinte.

## Pré-requisitos

1. Service Account criada no Google Cloud.
2. Planilha compartilhada com o e-mail da SA como **Editor**.
3. Arquivo JSON de credenciais baixado (ex.: `creds.json`).

## Onde colocar o `creds.json`

Coloque o arquivo baixado em:

```text
secrets/google_creds.json
```

Na raiz do projeto (`BAEP-Controle-Materiais/secrets/google_creds.json`).

O diretório `secrets/` está no `.gitignore` (raiz e interno). **Nunca** versionar esse arquivo.

## Gerar o base64 das credenciais

### Linux

```bash
base64 -w0 secrets/google_creds.json > secrets/creds.b64.txt
wc -c secrets/creds.b64.txt
```

### macOS

```bash
base64 -i secrets/google_creds.json | tr -d '\n' > secrets/creds.b64.txt
wc -c secrets/creds.b64.txt
```

### Windows (PowerShell)

```powershell
$bytes = [System.IO.File]::ReadAllBytes("$PWD\secrets\google_creds.json")
$b64 = [Convert]::ToBase64String($bytes)
[System.IO.File]::WriteAllText("$PWD\secrets\creds.b64.txt", $b64)
(Get-Item secrets\creds.b64.txt).Length
```

O conteúdo de `secrets/creds.b64.txt` é **secreto**. Não cole em chats, issues ou commits.
Use-o apenas para colar em variáveis de ambiente (Coolify / `.env` local).

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Conteúdo de `secrets/creds.b64.txt` (uma linha, base64) |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | ID da planilha (trecho entre `/d/` e `/edit` na URL) |
| `SHEETS_SYNC_ENABLED` | `true` ou `false` (default `false`) |

Exemplo de URL:

```text
https://docs.google.com/spreadsheets/d/ABCDEF1234567890xyz/edit#gid=0
                                 └──────── ID ────────┘
```

Referência local: `.env.example`.

## Configurar no Coolify (manual)

1. Abra o Coolify → projeto/serviço do **SIS LOGÍSTICA / reserva_baep**.
2. Vá em **Environment Variables** (ou **Environment** / **Secrets**).
3. Adicione (ou edite) as três variáveis:

| Key | Value (placeholder) |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | *(colar o conteúdo inteiro de `secrets/creds.b64.txt`)* |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | *(colar o ID da planilha)* |
| `SHEETS_SYNC_ENABLED` | `false` *(use `true` só quando a sync estiver pronta)* |

4. Salve e **redeploy** / restart do container para o Django recarregar o settings.
5. Confirme que o build instala as deps novas (`google-auth`, `google-auth-httplib2`, `google-api-python-client`) — o Coolify deve reinstalar a partir de `requirements.txt` no próximo deploy.

### Screenshot descritivo (textual)

```text
Coolify → Application → Environment
┌─────────────────────────────────────────────────────────────┐
│  GOOGLE_SERVICE_ACCOUNT_JSON = eyJ0eXBlIjoi...   (longo)   │
│  GOOGLE_SHEETS_SPREADSHEET_ID = 1abc...xyz                  │
│  SHEETS_SYNC_ENABLED         = false                        │
└─────────────────────────────────────────────────────────────┘
→ Save → Redeploy
```

## Validar localmente

Com `.env` preenchido (ou variáveis exportadas):

```bash
python manage.py check_sheets_setup
```

Esperado nesta fase:

- `[OK] Service Account carregada: ...@....iam.gserviceaccount.com`
- `[OK] Spreadsheet ID configurado: …`
- `[TODO] Conexão com a planilha (listar abas) — próxima fase.`

## Estrutura do app `integracoes`

```text
integracoes/
├── google_client.py          # cliente API (próxima fase)
├── mapping.py                # mapa aba ↔ model (próxima fase)
├── services/pull.py          # Sheets → Django
├── services/push.py          # Django → Sheets
├── management/commands/
│   ├── check_sheets_setup.py
│   └── sync_full_sheets.py
└── models.py                 # SheetRowSnapshot, SheetSyncState
```

## Rede corporativa

Ambiente atual: `10.43.19.224:8002` (sem domínio público).
A sync por **polling** (management command / cron Coolify) não exige webhook nem IP público — apenas saída HTTPS do servidor para `googleapis.com`.
