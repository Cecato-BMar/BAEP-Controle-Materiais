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

## Seed Inicial da Planilha Nova (`--seed` e `--force`)

O comando `sync_full_sheets --seed` popula a planilha nova com todos os registros atuais do banco de dados (6 abas correspondentes a `PistolaGlock`, `PistolaTaurus`, `EspingardaCal12`, `EscudoBalistico`, `TASER`, `RadioHT`).

```bash
python manage.py sync_full_sheets --seed [--dry-run] [--force]
```

### Idempotência e Comportamento de Segurança:
- **Sem `--force`**: O seed recusa a execução caso `SheetRowSnapshot` já exista no banco de dados (disparando `RuntimeError`), ou se a aba na planilha nova já contiver dados. Isso previne duplicações acidentais.
- **Com `--force`**: Limpa as abas da planilha nova (`clear("new", "A:ZZ")`), remove snapshots anteriores e reescreve todos os dados a partir do Django. **Atenção:** formatação manual, cores ou notas adicionadas na planilha nova serão perdidas.
- **Com `--dry-run`**: Simula a operação de seed sem alterar a planilha ou criar registros no banco de dados.

## PULL: Sincronização Google Sheets → Django (`pull_from_sheets`)

O comando `pull_from_sheets` lê os dados da planilha nova e atualiza o banco de dados Django:

```bash
python manage.py pull_from_sheets --confirm [--dry-run] [--force] [--model PistolaGlock]
```

### Regras de Negócio e Segurança:
1. **Confirmação Obrigatória**: Requer `--confirm` para execução real ou `--dry-run` para simulação segura.
2. **Backup Automático**: Antes de aplicar alterações reais, gera um backup físico do banco de dados (tag `pull`).
3. **Bloqueio Concorrente e Anti-Loop**: Utiliza `select_for_update()` em `SheetSyncState` no início da transação atômica e ativa `set_syncing(True)` para impedir loops e concorrência.
4. **Sem Fabricação de Dados**: Campos obrigatórios vazios ou inválidos não recebem valores inventados; a linha é registrada com status `ERROR` em `SyncOperationRecord`.
5. **Criação de Linhas Sem ID**: Quando uma nova linha é criada diretamente na planilha sem `id`, o sistema cria o registro no Django e escreve imediatamente o ID gerado na célula `A{linha}` da planilha para evitar duplicações em ciclos subsequentes.
6. **Last Write Wins (LWW)**: Se a linha possui `id`, compara o campo `atualizado_em` da planilha com `data_atualizacao` do Django. Se o Django for mais recente, a alteração da planilha é ignorada com warning. Colunas marcadas como `read_only_columns` (como `atualizado_em`) não são sobrescritas.

## PUSH: Sincronização Django → Google Sheets (`push_to_sheets`)

O comando `push_to_sheets` envia registros novos ou modificados no Django para a planilha nova:

```bash
python manage.py push_to_sheets --confirm [--dry-run] [--since <ISO8601>] [--model PistolaGlock]
```

### Regras de Negócio e Segurança:
1. **Marco Temporal Preciso**: O marco temporal (`marco = since or state.last_push_at`) é capturado **antes** de qualquer leitura de objetos para não perder updates concorrentes.
2. **Atualização Atômica de Estado**: Ao finalizar, define `state.last_push_at = marco` (não `now()`), garantindo continuidade estrita para execuções seguintes.
3. **Batch Updates em Lote**: Registros já mapeados por `SheetRowSnapshot` são atualizados via `values.batchUpdate` em lotes de 100 linhas com range explícito `A{row}:{last_col}{row}` (uma única chamada HTTP para até 100 alterações).
4. **Novos Registros (`append_row`)**: Registros novos no Django que ainda não possuem snapshot utilizam `append_row` e registram o novo `SheetRowSnapshot` com `update_or_create`. Se o range retornado não fornecer o número da linha, faz fallback para `len(read_all) + 1` com warning log.
5. **Atualização do Snapshot**: Após cada escrita, o `content_hash` do snapshot é recalculado e persistido para evitar que o pull seguinte interprete como modificação externa.



