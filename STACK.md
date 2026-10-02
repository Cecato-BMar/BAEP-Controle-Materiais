# STACK.md — SIS LOGÍSTICA 2º BAEP

**Gerado por:** Antigravity  
**Data:** 2026-10-02T11:46:00-03:00  
**Commit atual:** 7e187c7e7f118b17e86f65af33d8053447bdd6b8  
**Branch atual:** feature/inventario-fluxo-completo  

---

## 1. Resumo Executivo
O **SIS LOGÍSTICA 2º BAEP** (também denominado `reserva_baep` / `BAEP-Controle-Materiais`) é uma plataforma web corporativa desenvolvida para a Seção de Logística do 2º Batalhão de Ações Especiais de Polícia (PMESP), sediado em Santos/SP. O sistema gerencia o ciclo completo de controle patrimonial, armamento bélico (fuzis, calibres 12, pistolas, armas de incapacitação neuromuscular, munições químicas e convencionais), kits operacionais de viaturas, frota automotiva com checklists e manutenções, telemática (rádios HT e câmeras operacionais) e inventário semestral com conferência cega. A stack principal consiste em **Python 3.12 + Django 5.2**, interface renderizada via Django Templates com Bootstrap 5.3 e tema tático institucional, persistência mista (SQLite local / PostgreSQL em produção via Docker/Gunicorn) e camadas integradas de auditoria (`django-simple-history`) e licenciamento criptográfico RSA-2048. O repositório abriga também um subprojeto protótipo multitenant denominado `sentinela_saas`.

---

## 2. Linguagens e Runtime

| Item | Valor | Evidência (arquivo) |
|---|---|---|
| **Linguagem Backend** | Python 3.12 (3.12.8 no ambiente virtual local) | [Dockerfile:1](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/Dockerfile#L1), [.venv/Scripts/python.exe](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/.venv) |
| **Linguagem Frontend** | HTML5, CSS3 (Vanilla + Custom CSS Variables), JavaScript (ES6+) | [templates/base.html:1-60](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/base.html#L1-L60), [static/sw.js](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/static/sw.js) |
| **Scripts de Automação** | Windows Batch Script (.bat) e Shell Script (Docker CMD) | [iniciar.bat](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/iniciar.bat), [run_app.bat](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/run_app.bat), [run_app_https.bat](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/run_app_https.bat), [Dockerfile:22](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/Dockerfile#L22) |
| **Gerenciador de Pacotes** | pip | [requirements.txt](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt), [Dockerfile:14-15](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/Dockerfile#L14-L15) |
| **Runtime de Execução** | CPython 3.12 / WSGI Server Gunicorn 26.2.0 | [Dockerfile:22](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/Dockerfile#L22), [requirements.txt:8](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt#L8) |
| **Containerização Principal** | Imagem base `python:3.12-slim-bookworm` (Debian Linux) | [Dockerfile:1](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/Dockerfile#L1) |
| **Containerização Subprojeto SaaS** | Dockerfile + docker-compose.yml (`web` + `db: postgres:15-alpine`) | [sentinela_saas/Dockerfile](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/sentinela_saas/Dockerfile), [sentinela_saas/docker-compose.yml:1-31](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/sentinela_saas/docker-compose.yml#L1-L31) |

---

## 3. Frameworks e Versões

| Camada | Framework | Versão | Evidência |
|---|---|---|---|
| **Backend Web** | Django | `>=5.0,<6.0` (instalado: `5.2.17`) | [requirements.txt:1](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt#L1), [reserva_baep/settings.py:1-5](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L1-L5) |
| **WSGI HTTP Server** | Gunicorn | `26.2.0` | [requirements.txt:8](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt#L8), [Dockerfile:22](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/Dockerfile#L22) |
| **Servidor SSL Dev/Local** | django-sslserver | `0.22` | [requirements.txt:2](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt#L2), [run_app_https.bat:25](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/run_app_https.bat#L25) |
| **Frontend UI (CSS)** | Bootstrap | `5.3.0` (via jsDelivr CDN) | [templates/base.html:24](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/base.html#L24) |
| **Frontend Form Rendering** | django-crispy-forms + crispy-bootstrap5 | crispy-forms `2.7`, crispy-bootstrap5 `2026.9` | [requirements.txt:3-4](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt#L3-L4), [reserva_baep/settings.py:134-135, 281-282](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L134-L135) |
| **Frontend Ícones** | Font Awesome Free | `6.4.0` (via cdnjs CDN) | [templates/base.html:26](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/base.html#L26) |
| **Frontend Selects** | Select2 + Select2 Bootstrap 5 Theme | `4.1.0-rc.0` (via jsDelivr CDN) | [templates/base.html:28-30, 968](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/base.html#L28-L30) |
| **Frontend Gráficos** | Chart.js | `latest` (via jsDelivr CDN) | [templates/patrimonio/dashboard.html:226](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/patrimonio/dashboard.html#L226) |
| **Frontend Utilitários** | jQuery | `3.6.0` (via code.jquery.com) | [templates/base.html:966](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/base.html#L966) |
| **Mobile** | Progressive Web App (PWA) | Service Worker próprio + Web Manifest | [static/sw.js](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/static/sw.js), [static/manifest.json](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/static/manifest.json), [templates/base.html:9-16, 1003-1011](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/base.html#L9-L16) |
| **Desktop** | NÃO IDENTIFICADO | NÃO IDENTIFICADO (aplicação acessada via browser) | — |

---

## 4. Banco de Dados e ORM

| Item | Valor | Evidência |
|---|---|---|
| **Bancos Suportados** | SQLite 3 (desenvolvimento/local) e PostgreSQL (produção/container) | [reserva_baep/settings.py:199-240](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L199-L240), [.env.example:24-27](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/.env.example#L24-L27) |
| **Arquivo SQLite Local** | `db.sqlite3` (tamanho: ~2.3 MB) na raiz do projeto | [db.sqlite3](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/db.sqlite3), [reserva_baep/settings.py:235](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L235) |
| **Driver PostgreSQL** | `psycopg` (v3) e `psycopg[binary]` v3.3.6 | [requirements.txt:7](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt#L7), [.venv pip list](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais) |
| **Configurador de URL do DB** | `dj-database-url` v3.1.2 | [requirements.txt:9](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt#L9), [reserva_baep/settings.py:12, 208](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L12) |
| **ORM** | Django ORM (`django.db.models`) | Todos os `models.py` dos aplicativos |
| **Auditoria e Histórico de Modelos** | `django-simple-history` v3.13.0 | [requirements.txt:17](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt#L17), [reserva_baep/settings.py:136, 171](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L136) |
| **Total de Migrations no Projeto Raiz** | **77 migrations** distribuídas em 16 pastas | Contagem via sistema de arquivos (detalhe abaixo) |
| **Total de Migrations em `sentinela_saas`** | **6 migrations** distribuídas em 6 pastas | [sentinela_saas/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/sentinela_saas) |

### Detalhamento das Migrations por Módulo (Projeto Raiz):
1. `estoque/migrations`: 17 migrations
2. `integracoes/migrations`: 1 migration
3. `inventario/migrations`: 2 migrations
4. `licenciamento/migrations`: 2 migrations
5. `materiais/migrations`: 4 migrations
6. `material_belico/migrations`: 2 migrations
7. `movimentacoes/migrations`: 3 migrations
8. `municoes/migrations`: 4 migrations
9. `patrimonio/migrations`: 1 migration
10. `policiais/migrations`: 2 migrations
11. `relatorios/migrations`: 5 migrations
12. `solicitacoes/migrations`: 5 migrations
13. `telematica/migrations`: 10 migrations
14. `tutorial/migrations`: 1 migration
15. `usuarios/migrations`: 1 migration
16. `viaturas/migrations`: 17 migrations

---

## 5. Autenticação e Autorização

### Mecanismo de Autenticação
- **Framework Base:** `django.contrib.auth` com sessões HTTP salvas em banco de dados (`django.contrib.sessions.middleware.SessionMiddleware`).
- **Validação de Credenciais:** `AuthenticationMiddleware` do Django.
- **Duração de Sessão:** 8 horas (`SESSION_COOKIE_AGE = 28800`), compatível com turnos operacionais militares ([reserva_baep/settings.py:312](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L312)).
- **URLs de Autenticação:**
  - Login: `/usuarios/login/` (`LOGIN_URL = 'usuarios:login'`)
  - Redirect pós-login: `/` (`LOGIN_REDIRECT_URL = 'home'`)
  - Redirect pós-logout: `/usuarios/login/` (`LOGOUT_REDIRECT_URL = 'usuarios:login'`)
  - Evidência: [reserva_baep/settings.py:287-289](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L287-L289), [usuarios/urls.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/usuarios/urls.py).

### Modelo de Usuário e Perfis (RBAC)
- **User Model:** Utiliza o modelo padrão `django.contrib.auth.models.User`.
- **Extensão de Perfil:** Modelo `Perfil` com relação `OneToOneField` vinculada a `User` e sinais `post_save` automáticos.
- **Níveis de Acesso (`nivel_acesso`):**
  - `ADMIN`: Administrador
  - `GESTOR`: Gestor
  - `OPERADOR`: Operador
  - `VISUALIZADOR`: Visualizador (default)
- **Vínculo Militar:** Campo opcional `policial = models.OneToOneField(Policial, ...)` ligando a conta ao registro militar de efetivo do 2º BAEP.
- **Evidência:** [usuarios/models.py:8-39](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/usuarios/models.py#L8-L39).

### Controle de Permissões por Módulos
- **Decorator de Permissão Modular:** `@require_module_permission(module_name)` em [reserva_baep/decorators.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/decorators.py#L5-L22).
  - Libera superusuários (`request.user.is_superuser`).
  - Para usuários comuns, valida se o usuário pertence ao grupo correspondente ao módulo via `request.user.groups.filter(name=module_name).exists()`.
  - Caso negado, dispara `PermissionDenied(f"Acesso negado ao módulo: {module_name}")`.
- **Criação de Grupos no Boot:** [usuarios/apps.py:16](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/usuarios/apps.py#L16) garante a existência dos grupos correspondentes aos módulos do sistema.
- **Comando de Auto-Recuperação Master:** [usuarios/management/commands/garantir_master.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/usuarios/management/commands/garantir_master.py) executado automaticamente no deploy do Dockerfile ([Dockerfile:22](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/Dockerfile#L22)).

### Licenciamento Criptográfico e Integridade (Anti-Pirataria / Contrato)
- **Middleware:** `licenciamento.middleware.LicenseCheckMiddleware` ([reserva_baep/settings.py:168](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L168)).
- **Criptografia:** Algoritmo assimétrico RSA-2048 (`RS256`) utilizando `PyJWT` e `cryptography`. Validação de chaves públicas/privadas, expiração de contrato, tolerância de dias e emissão de tokens.
- **Evidência:** [licenciamento/license_core.py:1-60](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/licenciamento/license_core.py#L1-L60), [licenciamento/models.py:1-18](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/licenciamento/models.py#L1-L18).

---

## 6. Estrutura de Pastas

Árvore real gerada via PowerShell (`Get-ChildItem -Directory` filtrando `.git`, `.venv`, `__pycache__`, `python`, `staticfiles`):

```text
├── .agenthandoff/
├── .antigravity/
├── .claude/
│   ├── commands/
├── .codex/
│   ├── commands/
├── .cursor/
│   ├── rules/
├── .gemini/
│   ├── commands/
├── .github/
├── .vscode/
├── administracao/
├── BAEP-Controle-Materiais/
├── docs/
├── estoque/
│   ├── migrations/
│   ├── templatetags/
├── integracoes/
│   ├── management/
│   │   ├── commands/
│   ├── migrations/
│   ├── services/
│   ├── tests/
├── inventario/
│   ├── migrations/
├── licenciamento/
│   ├── management/
│   │   ├── commands/
│   ├── migrations/
├── logs/
├── materiais/
│   ├── migrations/
├── material_belico/
│   ├── management/
│   │   ├── commands/
│   ├── migrations/
├── movimentacoes/
│   ├── migrations/
├── municoes/
│   ├── migrations/
├── patches/
│   ├── remote/
├── patrimonio/
│   ├── migrations/
├── policiais/
│   ├── migrations/
├── relatorios/
│   ├── migrations/
├── reserva_baep/
├── scratch/
├── secrets/
├── sentinela_saas/
│   ├── accounts/
│   │   ├── migrations/
│   ├── almoxarifado/
│   │   ├── migrations/
│   ├── armaria/
│   │   ├── migrations/
│   ├── cautelas/
│   │   ├── migrations/
│   ├── frotas/
│   │   ├── migrations/
│   ├── marketing/
│   ├── sentinela_core/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   ├── telematica/
│   │   ├── migrations/
│   ├── templates/
│   │   ├── accounts/
│   │   ├── almoxarifado/
│   │   ├── armaria/
│   │   ├── cautelas/
│   │   ├── dashboard/
│   │   ├── frotas/
│   │   ├── landing/
│   │   ├── telematica/
├── solicitacoes/
│   ├── migrations/
├── static/
│   ├── img/
├── telematica/
│   ├── migrations/
├── templates/
│   ├── administracao/
│   ├── estoque/
│   │   ├── categorias/
│   │   ├── fornecedores/
│   │   ├── inventarios/
│   │   ├── movimentacoes/
│   │   ├── produtos/
│   │   ├── relatorios/
│   │   ├── unidades_medida/
│   ├── inventario/
│   ├── licenciamento/
│   ├── materiais/
│   ├── material_belico/
│   ├── movimentacoes/
│   ├── municoes/
│   ├── patrimonio/
│   ├── policiais/
│   ├── relatorios/
│   ├── solicitacoes/
│   ├── telematica/
│   ├── tutorial/
│   ├── usuarios/
│   ├── viaturas/
├── tutorial/
│   ├── management/
│   │   ├── commands/
│   ├── migrations/
├── usuarios/
│   ├── management/
│   │   ├── commands/
│   ├── migrations/
│   ├── templatetags/
├── viaturas/
│   ├── migrations/
│   ├── services/
│   ├── templatetags/
```

### Destaques de Localização:
- **Configurações Centrais (Settings & WSGI):** [reserva_baep/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep) (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `decorators.py`).
- **Rotas Centrais:** [reserva_baep/urls.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/urls.py).
- **Módulos/Apps Django:** Na raiz do projeto (`administracao/`, `estoque/`, `integracoes/`, `inventario/`, `licenciamento/`, `materiais/`, `material_belico/`, `movimentacoes/`, `municoes/`, `patrimonio/`, `policiais/`, `relatorios/`, `solicitacoes/`, `telematica/`, `tutorial/`, `usuarios/`, `viaturas/`).
- **Templates:** Diretório centralizado em [templates/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates), organizado em subpastas por módulo.
- **Arquivos Estáticos:** [static/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/static) (`manifest.json`, `sw.js`, `offline.html`, imagens).
- **Scripts de Importação e Carga:** Raiz do projeto (`importar_material_belico.py`, `importar_planilha_oficial.py`, `importar_kits_operacionais.py`, `importar_inventario_oficial.py`, `sincronizar_municoes.py`).
- **Logs do Sistema:** Diretório [logs/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/logs) (`baep_sistema.log`, rotativo até 10 MB, 5 backups).

---

## 7. Módulos e Funcionalidades Identificados

Baseado na inspeção de `models.py`, `views.py` e `urls.py`:

| Módulo / App | Qtd Models | Funcionalidade Principal |
|---|---|---|
| **material_belico** | 23 (+ 16 audit) | Gestão do arsenal operacional do 2º BAEP: fuzis (5.56 e 7.62), espingardas cal. 12, pistolas Glock e Taurus, miras RedDot, supressores, rádios HT, lançadores AM-640/AM-600, taser, escudos/capacetes balísticos e montagem de Kits Operacionais. |
| **viaturas** | 15 (+ 4 audit) | Gestão da frota automotiva: despachos operacionais, hodômetro, abastecimento, oficinas, checklists pré/pós turno, solicitações de baixa, controle de peças e planos de manutenção preventiva. |
| **estoque** | 18 | Almoxarifado central e materiais de consumo: controle de saldo, lotes, números de série, requisições, fornecedores, localização física e inventário. |
| **inventario** | 7 | Ciclos de inventário semestral da unidade: contas contábeis, comissões examinadoras, conferência cega e apuração de divergências físicas vs contábeis. |
| **telematica** | 6 | Equipamentos de comunicação e tecnologia: cadastro de rádios HT, frequências/canais, linhas móveis, câmeras corporais (bodycams) e chamados de suporte técnico de TI. |
| **municoes** | 5 | Gestão detalhada de munições convencionais e de treinamento: controle quantitativo por lote/calibre, retiradas, devoluções, contagem de estojos deflagrados e remessa de devolução ao CPI. |
| **movimentacoes** | 4 | Fluxo de cautelas diárias de armamentos e equipamentos para serviço operacional ou instrução, com registro de disparo e devolução. |
| **patrimonio** | 4 | Gestão de bens permanentes e tombamento: número de patrimônio, classificação por conta patrimonial, localização física e transferências de carga. |
| **solicitacoes** | 3 | Portal de autoatendimento para policiais solicitarem materiais com carrinho de pedidos, fluxo de deferimento por gestores e recibo digital de entrega. |
| **tutorial** | 2 | Manual interativo e onboarding embarcado: módulos e seções com passo-a-passo operacional para armeiros e operadores. |
| **integracoes** | 2 | Sincronização em segundo plano com Google Sheets API v4 via Service Account, mantendo snapshots e estados de sincronização de planilhas operacionais. |
| **licenciamento** | 1 | Proteção do sistema com validação de tokens JWT assinados via RSA-2048, controle de expiração, tolerância e painel Master. |
| **materiais** | 2 | Catálogo base inicial e materiais genéricos (mantido para compatibilidade com registros legados). |
| **policiais** | 1 | Cadastro central do efetivo policial do 2º BAEP (RE, Dígito, Nome de Guerra, Posto/Graduação, Companhia, Pelotão e status). |
| **usuarios** | 1 | Perfis de acesso ao sistema (Perfil 1:1 User), níveis de permissão (ADMIN, GESTOR, OPERADOR, VISUALIZADOR) e auditoria de último login. |
| **relatorios** | 1 | Registro, rastreabilidade e geração de certidões e relatórios analíticos em PDF (ReportLab) e planilhas Excel (OpenPyXL/Pandas). |
| **administracao** | 0 | Painel central administrativo: dashboard consolidado da unidade, busca unificada de itens em carga e relatórios para comando. |
| **sentinela_saas** | 6 (subprojeto) | Protótipo independente de produto SaaS B2B/GovTech multi-tenant (SentinelaOps Cloud) para empresas de segurança privada e GCMs. |

---

## 8. Configuração e Ambiente

### Arquivos de Configuração
- `.env`: Arquivo local ativo de variáveis de ambiente ([.env](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/.env)).
- `.env.example`: Modelo oficial versionado ([.env.example](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/.env.example)).

### Variáveis Críticas Identificadas
- `SECRET_KEY`: Chave secreta de criptografia e assinatura de sessão do Django (obrigatória, dispara `ImproperlyConfigured` se ausente).
- `DEBUG`: Booleano (`True` em dev, `False` em produção).
- `ALLOWED_HOSTS`: Suporta listas e expansão dinâmica de sub-redes (ex: `10.43.19.*` ou `10.43.19.0/24`) implementada via `ipaddress` em [reserva_baep/settings.py:68-87](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/settings.py#L68-L87).
- `CSRF_TRUSTED_ORIGINS`: Origens confiáveis para proteção CSRF, com suporte a expansão de faixa de IPs locais.
- `DATABASE_URL` / `DJANGO_DATABASE_URL`: String de conexão para PostgreSQL ou SQLite.
- `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`: Configurações de fallback para Postgres.
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Credencial da conta de serviço Google em Base64 para integração com Google Sheets API.
- `GOOGLE_SHEETS_SPREADSHEET_ID`: ID da planilha do Google Sheets para sincronização.
- `SHEETS_SYNC_ENABLED`: Flag booleana (`true`/`false`) para ligar/desligar sync.
- `IMPORT_ENABLED`: Flag booleana para habilitar/desabilitar importadores em massa via UI.
- `LICENSE_PRIVATE_KEY`: Chave privada RSA PEM para emissão interna de licenças pelo usuário Master.

### Portas e Conectividade
- `8000`: Porta HTTP padrão (usada pelo Django runserver local e pelo container Docker).
- `8443`: Porta HTTPS com SSL local em desenvolvimento/intranet via `runsslserver` ([run_app_https.bat:25](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/run_app_https.bat#L25)).
- `3000`: Porta adicional exposta no Dockerfile ([Dockerfile:20](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/Dockerfile#L20)).
- `8080`: Porta padrão configurada para o protótipo [sentinela_saas/README.md:50](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/sentinela_saas/README.md#L50).

### Middlewares Ativos (em ordem de execução)
1. `django.middleware.security.SecurityMiddleware`
2. `whitenoise.middleware.WhiteNoiseMiddleware` (compressão e cache de arquivos estáticos)
3. `django.contrib.sessions.middleware.SessionMiddleware`
4. `django.middleware.common.CommonMiddleware`
5. `django.middleware.csrf.CsrfViewMiddleware`
6. `django.contrib.auth.middleware.AuthenticationMiddleware`
7. `licenciamento.middleware.LicenseCheckMiddleware` (bloqueio por expiração de licença contratual)
8. `django.contrib.messages.middleware.MessageMiddleware`
9. `django.middleware.clickjacking.XFrameOptionsMiddleware` (`SAMEORIGIN`)
10. `simple_history.middleware.HistoryRequestMiddleware` (atribuição automática de `history_user` em auditorias)

---

## 9. Build, Deploy e CI/CD

### Pipeline e CI/CD
- **GitHub Workflows / GitLab CI / Jenkins:** NÃO IDENTIFICADO (não existem diretórios `.github/workflows` ou arquivos de pipeline).
- **Instruções de IA na pasta .github:** [copilot-instructions.md](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/.github/copilot-instructions.md).

### Estratégia de Build e Deploy
1. **Ambiente em Container (Linux / Servidor Produção):**
   - Imagem: `python:3.12-slim-bookworm` ([Dockerfile](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/Dockerfile)).
   - Passos no entrypoint:
     ```bash
     python manage.py migrate --noinput && \
     python manage.py garantir_master && \
     python manage.py collectstatic --noinput && \
     gunicorn reserva_baep.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120
     ```
2. **Ambiente Local Windows (Intranet / Standalone 2º BAEP):**
   - Scripts dedicados em Batch:
     - `iniciar.bat`: Inicializa na porta 8000 usando Python portátil (`.\python_env\tools\python.exe`).
     - `run_app.bat`: Inicializa apontando para a rede local (`10.43.19.224:8000`).
     - `run_app_https.bat`: Inicializa via SSL (`10.43.19.224:8443`) com `runsslserver`.

---

## 10. Testes e Qualidade

| Item | Status / Ferramenta | Evidência |
|---|---|---|
| **Framework de Testes** | Django Test Runner (`django.test.TestCase` baseado em `unittest`) | [inventario/tests.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/inventario/tests.py), [integracoes/tests/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/integracoes/tests) |
| **Suíte de Testes Implementada** | - `inventario/tests.py` (testes de ciclo, apuração e divergências de inventário)<br>- `integracoes/tests/test_loops.py`, `test_pull.py`, `test_push.py` (testes da sync Sheets)<br>- `scratch/test_reports.py` | [inventario/tests.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/inventario/tests.py), [integracoes/tests/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/integracoes/tests) |
| **Apps com `tests.py` padrão (sem testes adicionados)** | `materiais`, `movimentacoes`, `municoes`, `patrimonio`, `policiais`, `relatorios`, `solicitacoes`, `telematica`, `usuarios`, `viaturas` | Arquivos `tests.py` com tamanho de 63 bytes |
| **Linters e Formatters** | NÃO IDENTIFICADO (não há arquivos `.flake8`, `.ruff.toml`, `pyproject.toml` ou `.prettierrc` no repositório) | Busca recursiva por configs de linter |
| **Cobertura de Código** | NÃO IDENTIFICADO (sem `.coveragerc` ou flags de pytest-cov) | Busca no repositório |

---

## 11. Dependências-Chave

Extraídas de [requirements.txt](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/requirements.txt) e validadas com o ambiente instalado via `.venv`:

| Pacote | Versão Instalada | Categoria / Finalidade |
|---|---|---|
| **Django** | `5.2.17` | Framework Web MVC / Backend central |
| **gunicorn** | `26.2.0` | Servidor HTTP WSGI para produção Linux/Docker |
| **psycopg** / **psycopg-binary** | `3.3.6` | Driver PostgreSQL nativo de alta performance |
| **dj-database-url** | `3.1.2` | Parser de URL de conexão de banco (`DATABASE_URL`) |
| **whitenoise** | `6.12.0` | Servidor e compactador de assets estáticos em produção |
| **django-crispy-forms** | `2.7` | Renderizador dinâmico e padronizado de formulários |
| **crispy-bootstrap5** | `2026.9` | Pacote de temas Bootstrap 5 para o Crispy Forms |
| **django-simple-history** | `3.13.0` | Rastreabilidade e auditoria temporal de alterações nos models |
| **django-sslserver** | `0.22` | Servidor de desenvolvimento com suporte nativo a HTTPS |
| **PyJWT** | `2.15.0` | Geração e decodificação de tokens JWT no licenciamento |
| **cryptography** | `50.0.1` | Criptografia de baixo nível para chaves RSA-2048 |
| **openpyxl** | `3.1.5` | Leitura e escrita de planilhas Excel modernas (.xlsx) |
| **xlrd** | `2.0.2` | Leitura de planilhas legadas de efetivo (.xls) |
| **pandas** | `3.0.6` | Manipulação e transformação de dados de inventários e planilhas |
| **reportlab** | `5.0.1` | Geração programática de relatórios, cautelas e certidões em PDF |
| **Pillow** | `12.3.0` | Processamento e validação de imagens (fotos de viaturas e avarias) |
| **python-dotenv** | `1.2.3` | Leitura automática do arquivo `.env` |
| **google-api-python-client** | `>=2.100` | Cliente oficial Google para API do Google Sheets v4 |
| **google-auth** | `>=2.20` | Autenticação Google Service Account para integrações |
| **google-auth-httplib2** | `>=0.1.1` | Transporte HTTP de autenticação da Google |

---

## 12. Padrões de Código Observados

1. **Convenção de Nomenclatura dos Modelos e Campos:**
   - **Idioma:** Predominantemente em **Português do Brasil** para regras de domínio (`Policial`, `Viatura`, `Manutencao`, `MunicaoQuimica`, `KitOperacional`, `numero_serie`, `lote_fabricacao`, `data_despacho`).
   - Termos em inglês são reservados a modelos de infraestrutura ou bibliotecas de terceiros (`User`, `LicenseRecord`, `SheetRowSnapshot`, `SheetSyncState`).
2. **Paradigma das Views (FBV vs CBV):**
   - **100% Function-Based Views (FBV):** O projeto adota funções (`def lista_viaturas(request):`, `def dashboard_frota(request):`, etc.) em vez de Class-Based Views (CBV).
   - Uso intensivo de decoradores: `@login_required` e `@require_module_permission('nome_do_modulo')`.
3. **Localização da Lógica de Negócios:**
   - **Mista:**
     - Validações de integridade e constraints no próprio modelo (`.clean()` e `.save()`).
     - Lógica de orquestração de formulários e redirects direta nas views.
     - Módulos de serviços dedicados em casos complexos: [viaturas/services/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/viaturas/services) e [integracoes/services/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/integracoes/services).
     - Scripts na raiz dedicados a parsers de carga inicial e saneamento de dados de planilhas militares.
4. **Tratamento de Dados de Planilhas Militares:**
   - Funções utilitárias defensivas (ex: `clean_val()`) para contornar caracteres nulos, traços (`────────`), fórmulas com erro (`#REF!`, `#N/A`) e dotações incompletas com salvamento bruto (`save_base(raw=True)`).

---

## 13. Pontos de Atenção e Dívidas Técnicas Visíveis

1. **Caminhos Absolutos Hardcoded (Quebra de Portabilidade):**
   - [importar_kits_operacionais.py:41](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/importar_kits_operacionais.py#L41): `EXCEL_PATH = '/home/servidor-sys-baep/BAEP-Controle-Materiais/BAEP-Controle-Materiais-2/PLANILHA DE MATERIAS - Atualizada .xlsx'`
   - [sincronizar_municoes.py:10](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/sincronizar_municoes.py#L10): `sys.path.insert(0, '/home/servidor-sys-baep/BAEP-Controle-Materiais')`
   - [importar_inventario_oficial.py:11](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/importar_inventario_oficial.py#L11): `EXCEL_FILE = r'c:\Users\2BAEP\.antigravity-ide\BAEP-Controle-Materiais\INVENTÁRIO - 2ºBAEP - EM - 2025..xlsx'`
   - [sentinela_saas/iniciar_saas.bat:15-16](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/sentinela_saas/iniciar_saas.bat#L15-L16): `C:\Users\2BAEP\.antigravity-ide\StockFlow\.venv\Scripts\python.exe`
   - [scratch/fix_relatorios.py:3](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/scratch/fix_relatorios.py#L3) e [scratch/refactor_views.py:4](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/scratch/refactor_views.py#L4): referenciam `c:\Users\2BAEP-32KVB92\Desktop\Projetos\...`
2. **Comentários TODO Identificados no Código da Aplicação:**
   - [integracoes/management/commands/check_sheets_setup.py:55](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/integracoes/management/commands/check_sheets_setup.py#L55): `# 4) TODO: abrir planilha e listar abas (próxima fase - google_client)`
   - [integracoes/management/commands/check_sheets_setup.py:61](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/integracoes/management/commands/check_sheets_setup.py#L61): `"[TODO] Conexão com a planilha (listar abas) - próxima fase."`
3. **Diretório Aninhado Vazio:**
   - Existe uma pasta vazia [BAEP-Controle-Materiais/](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/BAEP-Controle-Materiais) na raiz do projeto (resíduo de descompactação ou clone aninhado).
4. **Arquivos Pesados e Binários Versionados na Raiz:**
   - `lcm_diversos_categorizado.xml` (10.9 MB)
   - `LCM-Diversos.pdf` (2.67 MB)
   - `db.sqlite3` (2.3 MB)
   - `lcm_diversos_categorizado.xlsx` (2.16 MB)
   - `PAP_CONTROLE_ESTOQUE.docx` (1.36 MB)
5. **Configurações de Produção em `iniciar.bat` e `run_app.bat`:**
   - Utilizam o comando `migrate --run-syncdb` em vez de `migrate` padrão, o que pode mascarar inconsistências de estado entre migrations existentes e novas tabelas.
