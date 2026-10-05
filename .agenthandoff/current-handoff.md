# Handoff Context: BAEP-Controle-Materiais

**Target Agent:** generic  
**Source Agent:** Gemini  
**Data/Hora:** 2026-10-05T11:27:00-03:00  
**Branch:** `feature/inventario-fluxo-completo`  

---

## Task State

- **Goal:** Implementar o controle de permissões por Groups para o módulo "Inventário Semestral" (Conferência Cega), aplicar proteções contra auto-bloqueio de admin e proteção do usuário master, limpar condicionais do menu lateral e otimizar execução dos testes.
- **Current Step:** Todos os 3 ajustes concluídos com sucesso e validados:
  1. Menu lateral `templates/base.html` totalmente limpo de `has_group` (0 ocorrências), padronizado no formato `'x' in user_groups` e "Logística & Suprimentos" expandido com `logistica`.
  2. Proteção contra auto-bloqueio do admin e proteção integral do usuário master implementadas em `administracao/views_permissoes.py` com registro em log e 2 testes dedicados.
  3. Performance dos testes otimizada com `--parallel` (> 55% de redução de tempo: 92s -> 37s), com 26/26 testes aprovados e comando documentado em `.github/copilot-instructions.md`.
- **Next Action:** Concluir commit e validação final.

---

## Decisions

1. **Critério Canônico do Usuário Master:**
   - O usuário master é definido por `user.username == os.getenv('ADMIN_USERNAME', 'master') or user.username == 'master'` (conforme [garantir_master.py:14](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/usuarios/management/commands/garantir_master.py#L14)).
   - Qualquer tentativa de alterar suas permissões via POST é rejeitada com erro amigável e registradas em log de auditoria.

2. **Auto-Proteção do Administrador:**
   - Se um administrador editar suas próprias permissões e desmarcar `'administracao'`, o sistema força a retenção do grupo, exibe erro e registra `motivo=auto-bloqueio` em `logs/baep_sistema.log`, sem abortar a atualização de outros grupos.

3. **Padronização das Condicionais do Menu:**
   - Eliminado o filtro redundante `user|has_group:'x'` em `templates/base.html`, unificando no context processor `'x' in user_groups`.

4. **Uso Padrão de `--parallel` nos Testes:**
   - A execução paralela do Django reduziu o tempo de suíte de 95s para 37s (ganho de ~60%), documentada em `.github/copilot-instructions.md`.

---

## Warnings

1. **Nunca executar `flush` ou `migrate --run-syncdb`:**
   - O banco local `db.sqlite3` armazena dados de homologação do 2º BAEP.
2. **LicenseCheckMiddleware:**
   - Testes unitários com requisições HTTP autenticadas devem registrar licença de teste no `setUp`.

---

## Related Files

- [templates/base.html](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/templates/base.html)
- [administracao/views_permissoes.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/administracao/views_permissoes.py)
- [administracao/tests.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/administracao/tests.py)
- [inventario/views.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/inventario/views.py)
- [inventario/tests.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/inventario/tests.py)
- [usuarios/apps.py](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/usuarios/apps.py)
- [.github/copilot-instructions.md](file:///c:/Users/2BAEP/.antigravity-ide/BAEP-Controle-Materiais/.github/copilot-instructions.md)
