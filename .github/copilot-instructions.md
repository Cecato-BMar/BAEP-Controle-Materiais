

<!-- AGENTHANDOFF:BEGIN -->
## AgentHandoff — Autonomous Context Transfer

This project has an **agenthandoff** MCP server configured in .vscode/mcp.json.

On session start, call `get_task_state` and `get_decisions` from the agenthandoff MCP server. Push decisions and warnings via MCP tools as you work.
<!-- AGENTHANDOFF:END -->

## Execução de Testes Automatizados

Para executar a suite de testes com performance otimizada, utilize sempre a flag `--parallel` (reduz o tempo de execução em > 55%):

```bash
# Execução padrão recomendada (paralela):
python manage.py test --parallel

# Testes de módulos específicos (exemplo: administracao e inventario):
python manage.py test administracao inventario --parallel

# Depuração serial com verbosidade:
python manage.py test administracao inventario --verbosity 2
```

