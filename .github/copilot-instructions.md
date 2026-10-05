

<!-- AGENTHANDOFF:BEGIN -->
## AgentHandoff — Autonomous Context Transfer

This project has an **agenthandoff** MCP server configured in .vscode/mcp.json.

On session start, call `get_task_state` and `get_decisions` from the agenthandoff MCP server. Push decisions and warnings via MCP tools as you work.
<!-- AGENTHANDOFF:END -->

## Sistema de Permissões por Módulo

### a) Mecanismo Oficial
- **Django Groups (`django.contrib.auth.models.Group`)**: Controle de acesso granular baseado na associação do usuário a grupos.
- **Sem modelos customizados**: Não utilizar tabelas/models customizados de permissão.
- **Bootstrap automático**: Os grupos são garantidos automaticamente no boot/pós-migração em [usuarios/apps.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/usuarios/apps.py).

### b) Lista Completa de Groups de Módulo Ativos
1. `reserva_armas` — Armamentos convencionais, cautelas e efetivo policial.
2. `material_belico` — Arsenal tático, fuzis, calibres 12, pistolas Glock, munições químicas e kits operacionais.
3. `materiais` — Almoxarifado e estoque de consumo.
4. `logistica` — Módulo geral de logística e suprimentos.
5. `frota` — Gestão e despacho de viaturas, manutenções e checklists.
6. `patrimonio` — Gestão de bens permanentes e tombamento.
7. `inventario` — Ciclo de inventário semestral com conferência cega e termo oficial.
8. `telematica` — TI, radiocomunicação, linhas móveis e suporte técnico.
9. `relatorios` — Geração e exportação de relatórios gerenciais e mapas.
10. `administracao` — Gestão de usuários, permissões e painel administrativo.

### c) Padrão Obrigatório nas Views
Toda Function-Based View (FBV) vinculada a um módulo deve utilizar obrigatoriamente:
```python
from django.contrib.auth.decorators import login_required
from reserva_baep.decorators import require_module_permission

@login_required
@require_module_permission('<nome_do_group>')
def minha_view(request):
    ...
```

### d) Padrão Obrigatório nos Templates (Menu Lateral)
Utilizar a lista `user_groups` injetada pelo context processor oficial (`administracao.context_processors.user_groups`):
```html
{% if user.is_superuser or '<nome_do_group>' in user_groups %}
<li class="nav-item">
    <a class="nav-link" href="...">...</a>
</li>
{% endif %}
```
> **Regra Estrita:** NUNCA utilizar o filtro `user|has_group:'x'`. Sempre utilizar o formato `'<group>' in user_groups`.

### e) Registro de Módulos na Tela de Administração
- Configurado centralmente em [administracao/views_permissoes.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/administracao/views_permissoes.py) através da constante `MODULOS_SISTEMA`.
- As telas `permissoes_lista.html` e `permissoes_form.html` iteram dinamicamente sobre essa lista. Para expor um novo módulo na gestão de acessos, basta adicioná-lo em `MODULOS_SISTEMA`.

### f) Proteções Anti-Lockout (Segurança Operacional)
1. **Auto-Proteção de Administrador:** A view `gerenciar_permissoes_usuario` impede que um administrador revogue seu próprio grupo `administracao`. Caso desmarcado, o grupo é retido, um aviso de erro é exibido e a tentativa é registrada em log.
2. **Imutabilidade do Usuário Master:** O usuário master (`username == 'master'` ou `os.getenv('ADMIN_USERNAME')`) não pode ter suas permissões alteradas via interface web; qualquer POST é rejeitado e registrado em log.
3. **Auditoria em Log:** Bloqueios são registrados em `logs/baep_sistema.log` no formato:
   `[PERMISSAO-BLOQUEIO] user=<admin> target=<username> motivo=<auto-bloqueio|master-protegido> ts=<ISO8601>`

### g) Comandos de Teste Recomendados
```bash
# Execução padrão recomendada (paralela - ganho > 55% de velocidade):
python manage.py test --parallel

# Testes de módulos específicos (exemplo: administracao e inventario):
python manage.py test administracao inventario --parallel

# Depuração serial com verbosidade:
python manage.py test administracao inventario --verbosity 2
```

### h) Receita: Como Adicionar um Novo Módulo ao Sistema (5 Passos)
1. **Adicionar o Group no Boot:** Incluir o identificador em `grupos` em [usuarios/apps.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/usuarios/apps.py).
2. **Cadastrar em `MODULOS_SISTEMA`:** Adicionar a entrada com `group`, `nome`, `descricao`, `icone` em [administracao/views_permissoes.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/administracao/views_permissoes.py).
3. **Proteger as Views:** Importar e decorar todas as views do novo app com `@require_module_permission('<group>')` abaixo de `@login_required`.
4. **Atualizar o Menu:** Envolver o link/seção correspondente em [templates/base.html](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/base.html) com `{% if user.is_superuser or '<group>' in user_groups %}`.
5. **Escrever Testes Automatizados:** Adicionar classe de testes de permissão em `administracao/tests.py` validando bloqueio 403 sem grupo, liberação 200 com grupo, acesso de superusuário e concessão/revogação via POST.


