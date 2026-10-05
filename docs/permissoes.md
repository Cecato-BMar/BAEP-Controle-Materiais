# Sistema de Permissões por Módulo

## Visão Geral

O **Sistema de Permissões por Módulo** do SIS LOGÍSTICA 2º BAEP controla o acesso dos operadores aos diferentes setores operacionais e administrativos da unidade (como Reserva de Armas, Frota, Material Bélico e Inventário Semestral). Utilizado pelos gestores e administradores do batalhão, o sistema opera de forma declarativa e centralizada: cada policial autenticado visualiza no menu lateral e acessa nas URLs exclusivamente os módulos para os quais sua conta foi explicitamente autorizada, enquanto superusuários possuem visibilidade total e irrestrita.

---

## Modelo de Permissão

- **Baseado em Django Groups (`django.contrib.auth.models.Group`)**: Solução nativa do Django, dispensando tabelas customizadas de permissão.
- **1 Group por Módulo**: Cada subsistema operacional possui exatamente um grupo correspondente.
- **Pertencer ao Group = Ter acesso ao módulo**: A presença do usuário no grupo concede acesso tanto às telas (HTTP 200) quanto à exibição dos links no menu lateral.
- **Superuser irrestrito**: Usuários com `is_superuser=True` acessam qualquer rota e visualizam todos os menus automaticamente, sem necessidade de estarem vinculados a grupos individuais.
- **Master imutável**: O usuário de manutenção do sistema (`master`) possui permissões blindadas contra alterações ou bloqueios via interface web.

---

## Lista de Módulos e Groups

Abaixo estão os 10 módulos ativos no sistema com seus respectivos grupos e rotas de entrada:

| Módulo | Group | Descrição | Como Acessar (Menu / Rota) |
|---|---|---|---|
| **Reserva de Armas** | `reserva_armas` | Cautelas operacionais, armamentos convencionais e efetivo | Menu *Operacional* → *Reserva de Armas* (`/dashboard/`) |
| **Material Bélico** | `material_belico` | Arsenal tático, fuzis, calibres 12, pistolas Glock, munições químicas e kits | Menu *Apoio & Sistema* → *Material Bélico* (`/material-belico/`) |
| **Material de Consumo** | `materiais` | Almoxarifado, estoque de consumo, entradas, saídas e catálogo | Menu *Logística & Suprimentos* → *Estoque de Consumo* (`/estoque/`) |
| **Logística Geral** | `logistica` | Visão e gestão unificada da seção de suprimentos | Menu *Logística & Suprimentos* (`/estoque/dashboard/`) |
| **Frota de Viaturas** | `frota` | Despacho de viaturas, controle de hodômetro, abastecimento e manutenções | Menu *Operacional* → *Frota de Viaturas* (`/viaturas/`) |
| **Patrimônio Permanente** | `patrimonio` | Gestão de bens duráveis, tombamentos e termos de responsabilidade | Menu *Logística & Suprimentos* → *Patrimônio* (`/patrimonio/`) |
| **Inventário Semestral** | `inventario` | Ciclo semestral de conferência cega, resolução de divergências e termos | Menu *Logística & Suprimentos* → *Inventário Semestral* (`/inventario/`) |
| **Telemática & TI** | `telematica` | Radiocomunicação, linhas móveis, câmeras e suporte técnico | Menu *Operacional* → *Telemática & TI* (`/telematica/`) |
| **Relatórios Oficiais** | `relatorios` | Emissão de certidões, mapas de carga e exportações em PDF/Excel | Menu *Inteligência & Relatórios* → *Central de Relatórios* (`/relatorios/`) |
| **Administração Geral** | `administracao` | Painel de controle, gestão de usuários e permissões de módulos | Menu *Apoio & Sistema* → *Permissões de Módulos* (`/administracao/permissoes/`) |

---

## Como Conceder/Revogar Permissões (UI)

Administradores gerenciam os acessos pela interface web sem necessidade de abrir o console do Django:

1. **Acessar a Listagem de Usuários:**
   - No menu lateral esquerdo, expanda **Apoio & Sistema** e clique em **Permissões de Módulos** (`/administracao/permissoes/`).
   - A tela lista todos os usuários cadastrados com badges coloridos indicando os módulos liberados.
2. **Localizar o Usuário:**
   - Utilize a barra de busca para pesquisar por Nome, RE, Posto/Graduação ou Username.
   - Clique no botão **Gerenciar** do policial desejado.
3. **Ajustar os Acessos:**
   - Na tela de formulário, marque os checkboxes dos módulos que o operador deve acessar.
   - Desmarque os checkboxes dos módulos cujo acesso deva ser revogado.
4. **Salvar:**
   - Clique em **Salvar Permissões**.
   - As alterações têm efeito imediato na próxima requisição do usuário.

---

## Como Adicionar um Novo Módulo ao Sistema

Para criar um novo módulo e integrá-lo ao controle de acessos existente, siga esta receita em 5 passos:

1. **Adicionar o Group no Boot:**
   No arquivo `usuarios/apps.py`, insira o identificador do novo grupo na lista `grupos` da função `criar_grupos_padrao`:
   ```python
   grupos = [
       ...,
       'novo_modulo',
   ]
   ```
2. **Cadastrar em `MODULOS_SISTEMA`:**
   No arquivo `administracao/views_permissoes.py`, inclua a configuração visual na constante `MODULOS_SISTEMA`:
   ```python
   {
       'group': 'novo_modulo',
       'nome': 'Nome Amigável do Módulo',
       'descricao': 'Descrição detalhada do módulo.',
       'icone': 'fas fa-shield-alt',
       'destaque': False,
   },
   ```
3. **Proteger as Views:**
   Em todas as Function-Based Views do novo app, aplique o decorator abaixo de `@login_required`:
   ```python
   from django.contrib.auth.decorators import login_required
   from reserva_baep.decorators import require_module_permission

   @login_required
   @require_module_permission('novo_modulo')
   def minha_view(request):
       ...
   ```
4. **Atualizar o Menu Lateral:**
   Em `templates/base.html`, envolva o item de menu correspondente na condicional com o context processor:
   ```html
   {% if user.is_superuser or 'novo_modulo' in user_groups %}
   <li class="nav-item">
       <a class="nav-link" href="{% url 'novo_modulo:home' %}">Meu Novo Módulo</a>
   </li>
   {% endif %}
   ```
5. **Criar Testes Automatizados:**
   Em `administracao/tests.py`, crie métodos testando o bloqueio HTTP 403 sem o grupo, HTTP 200 com o grupo e a concessão/revogação via POST.

---

## Proteções Anti-Lockout

Para prevenir erros operacionais que poderiam paralisar o gerenciamento do sistema, duas regras estritas de segurança foram incorporadas na view `gerenciar_permissoes_usuario`:

1. **Auto-Proteção de Administrador:**
   - Um administrador não pode revogar seu próprio grupo `administracao`.
   - Se o administrador desmarcar essa opção para si mesmo, o sistema retém o grupo, exibe uma mensagem de erro (*"Você não pode remover sua própria permissão de administração."*) e mantém a atualização dos demais módulos solicitados.
2. **Imutabilidade do Usuário Master:**
   - O usuário master do sistema (`username == 'master'` ou variável `ADMIN_USERNAME`) tem suas permissões blindadas contra qualquer edição visual.
   - Qualquer tentativa de POST na tela de permissões do master é abortada imediatamente com o erro *"As permissões do usuário master não podem ser alteradas."*.

---

## Auditoria e Logs

- **Logs do Sistema em Arquivo:**
  As operações de concessão, revogação e tentativas de violação de auto-bloqueio são registradas em `logs/baep_sistema.log`.
- **Formato dos Registros:**
  - Atualização de permissões:
    `PERMISSÕES ATUALIZADAS | Usuário-alvo: '<alvo>' | Operador: '<admin>' | Concedidos: [...] | Revogados: [...]`
  - Tentativas bloqueadas (anti-lockout):
    `[PERMISSAO-BLOQUEIO] user=<admin> target=<username> motivo=<auto-bloqueio|master-protegido> ts=<ISO8601>`
- **Rastreamento via `django-simple-history`:**
  O `django-simple-history` é utilizado para auditar alterações nos modelos de domínio da aplicação (`ItemInventario`, `Viatura`, `Material`, etc.). A associação Many-to-Many nativa do Django (`User.groups`) é auditada através do log estruturado de permissões em `baep_sistema.log` e do histórico do `Perfil`.

---

## Perguntas Frequentes (FAQ)

### Por que não foi criado um modelo customizado de permissões?
O Django possui uma infraestrutura madura e altamente otimizada de grupos (`auth_group` e `auth_user_groups`). Criar tabelas customizadas geraria redundância, aumentaria a complexidade de queries e não aproveitaria os métodos nativos de autenticação e cache de sessões do framework.

### Por que usar Groups e não as Permissions nativas (`auth_permission`)?
No SIS LOGÍSTICA do 2º BAEP, o modelo de negócios adota granularidade **por módulo operacional** (o operador acessa ou não o módulo como um todo), e não por ação técnica atômica (`add_item`, `change_item`, `delete_item`). Um grupo único por módulo simplifica radicalmente a gestão pelo graduado de dia e elimina o risco de permissões parciais inconsistentes.

### Como funciona o bootstrap automático dos Groups?
No arquivo `usuarios/apps.py`, a classe `UsuariosConfig` conecta o sinal `post_migrate` à função `criar_grupos_padrao`. Toda vez que `python manage.py migrate` é executado ou a aplicação é inicializada, o sistema verifica a existência dos 10 grupos e cria apenas os que eventualmente não existirem, sem sobrescrever dados prévios.

---

## Referências de Código

- [reserva_baep/decorators.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/reserva_baep/decorators.py): Decorator `@require_module_permission`.
- [usuarios/apps.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/usuarios/apps.py): Bootstrap e inicialização dos grupos.
- [administracao/views_permissoes.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/administracao/views_permissoes.py): Constante `MODULOS_SISTEMA`, views administrativas e validações anti-lockout.
- [administracao/context_processors.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/administracao/context_processors.py): Context processor `user_groups` para templates.
- [templates/base.html](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/base.html): Renderização condicional do menu lateral.
- [administracao/tests.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/administracao/tests.py): Suíte de testes automatizados de permissões e segurança.
