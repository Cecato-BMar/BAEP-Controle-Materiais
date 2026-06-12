# Módulo Frota — Arquitetura de Integração

> **Sistema**: SIS LOGÍSTICA 2º BAEP — Sistema Integrado de Controle Logístico  
> **Status atual**: App `viaturas` em produção (branch `feature/modulo-frota`)  
> **URL base**: `/frota/` → `viaturas.urls` (namespace `viaturas`)

---

## 1. Mapeamento do Sistema Existente

### 1.1 Apps Instalados (`settings.INSTALLED_APPS`)

| Módulo | App Django | Responsabilidade |
|---|---|---|
| Reserva de Armas | `materiais` | Armamentos, coletes, equipamentos táticos |
| Efetivo | `policiais` | Cadastro de policiais (RE, posto, situação) |
| Cautelas | `movimentacoes` | Retiradas, devoluções e movimentações de material |
| Munições | `municoes` | Lotes, retiradas e devoluções de munição |
| Usuários | `usuarios` | Auth, perfis e níveis de acesso |
| Relatórios | `relatorios` | Geração de PDFs centralizada (ReportLab) |
| Estoque de Consumo | `estoque` | Materiais de consumo, fornecedores, movimentações P4 |
| **Frota** | **`viaturas`** | **Viaturas, despachos, manutenção, abastecimento, peças** |
| Patrimônio | `patrimonio` | Bens permanentes, inventário |
| Telemática & TI | `telematica` | Ativos de TI, rádios, linhas móveis, suporte |
| Solicitações | `solicitacoes` | Pedidos de material de consumo |
| Licenciamento | `licenciamento` | Controle de licença do sistema (RSA/JWT) |
| Material Bélico | `material_belico` | Armas de fogo, acessórios, kits, auditoria P2 |

### 1.2 Models do App `viaturas` (Estado Atual — 15 models)

```
┌─────────────────────────┐
│   MarcaViatura          │──── 1:N ────▶ ModeloViatura
│   (nome, ativo)         │              (marca, nome, tipo, ativo)
└─────────────────────────┘                    │
                                               │ 1:N
                                               ▼
┌─────────────────────────────────────────────────────────┐
│                     Viatura                              │
│ prefixo, placa, chassi, renavam, patrimonio             │
│ modelo(FK), ano, cor, combustivel, tanque               │
│ odometro_atual, status, localizacao, observacoes        │
│ history(HistoricalRecords)                              │
└──────┬──────────┬──────────────┬────────────┬───────────┘
       │          │              │            │
       │ 1:N      │ 1:N          │ 1:N        │ 1:N
       ▼          ▼              ▼            ▼
 DespachoViatura  Abastecimento  Manutencao   ChecklistViatura
 (saida/retorno)  (litros,$)    (tipo,status) (inspeção)
       │                         │
       │                         │ 1:N        1:N         1:N
       │                         ▼            ▼            ▼
       │               ServicoManutencao  EvidenciaManutencao  RetiradaPeca
       │               (imutável)       (fotos,laudos)        │
       │                                                       │ 1:N
       │                                                       ▼
       │                                              RetiradaPecaItem
       │                                              (peca, qtd)
       │
       ▼
 SolicitacaoBaixaViatura      PecaViatura         Oficina
 (categoria, status, motivo)  (estoque, min)      (nome, cnpj)
                                                    
 PlanoManutencaoPreventiva    RegistroHistoricoManutencao
 (modelo, intervalo km/dias)  (append-only, auditoria)
```

### 1.3 Models de Outros Módulos com Relação à Frota

| Model | App | Relação com Frota |
|---|---|---|
| `Policial` | `policiais` | Motorista em despachos, abastecimentos, retiradas de peças |
| `User` (auth) | `django` | `registrado_por`, `aprovado_por`, `cancelado_por` |
| `OrgaoRequisitante` | `estoque` | Setor de lotação de equipamentos (Telemática) |
| `Relatorio` | `relatorios` | Tipos `FROTA_GERAL`, `FROTA_ABASTECIMENTO`, `FROTA_MANUTENCAO` |

---

## 2. Camada de Autenticação

### 2.1 Fluxo de Login
- **View**: `usuarios.views.login_view`
- **Autenticação primária**: Django `authenticate(username, password)`
- **Fallback RE**: Se falhar, tenta `RE + senha padrão` (`baep{RE}`)
  - Busca `Policial` pelo RE, cria `User` automaticamente se não existir
  - Vincula `Perfil.policial` e define `nivel_acesso = OPERADOR`
- **Sessão**: 8 horas (`SESSION_COOKIE_AGE = 28800`)

### 2.2 Perfil do Usuário (`usuarios.Perfil`)
- `OneToOneField(User)` criado via signal `post_save`
- Campos: `nivel_acesso` (ADMIN/GESTOR/OPERADOR/VISUALIZADOR), `policial`, `telefone`, `data_ultimo_acesso`

---

## 3. Sistema de Permissões

### 3.1 Decorator Central: `require_module_permission(module_name)`
- **Arquivo**: `reserva_baep/decorators.py`
- **Lógica**:
  1. Se não autenticado → redireciona para login
  2. Se `is_superuser` → acesso liberado
  3. Se usuário pertence ao grupo (`Group.name == module_name`) → acesso liberado
  4. Caso contrário → `PermissionDenied (403)`

### 3.2 Grupos Django em Uso

| Grupo | Módulo Controlado |
|---|---|
| `reserva_armas` | Reserva de Armas, Dashboard principal |
| `frota` | Frota de Viaturas (CRUD completo) |
| `telematica` | Telemática & TI |
| `materiais` | Estoque de Consumo (P4) |
| `patrimonio` | Patrimônio (Permanente) |
| `administracao` | Gestão de Usuários |
| `material_belico` | Material Bélico (P2) |

### 3.3 Permissões na Sidebar (`base.html`)
- Cada seção da sidebar verifica `{% if user.is_superuser or user|has_group:'nome_grupo' %}`
- Template tag customizada: `auth_extras.has_group`
- Serviços rápidos (solicitar material, suporte TI, baixa viatura) são acessíveis a todos os autenticados

### 3.4 Padrão no Módulo Frota
```python
FROTA_GROUPS = ['frota', 'reserva_armas']  # grupos com acesso

@login_required
@require_module_permission('frota')
def view_da_frota(request): ...
```
> **Nota**: Algumas views usam verificação manual via `_has_frota_permission()` que checa ambos os grupos. O decorator `require_module_permission('frota')` é o padrão predominante.

---

## 4. Auditoria e Rastreabilidade

### 4.1 `django-simple-history`
- Instalado e no middleware: `HistoryRequestMiddleware`
- Usado em: `Viatura`, `Manutencao`, `ChecklistViatura`
- Registra automaticamente: quem alterou, quando, quais campos e valores anteriores
- Admin: `SimpleHistoryAdmin` habilitado nos respectivos ModelAdmin

### 4.2 Histórico Append-Only de Manutenções
- **Service**: `viaturas/services/manutencao_historico.py`
- **Model**: `RegistroHistoricoManutencao` (nunca deleta/edita)
- **Model**: `ServicoManutencao` (imutável após criação)
- **Eventos**: ABERTURA, SERVICO, ATUALIZACAO, STATUS, CONCLUSAO, CANCELAMENTO, EVIDENCIA
- **Funções**: `registrar_abertura()`, `registrar_servico()`, `registrar_conclusao()`, `registrar_cancelamento()`, `registrar_evidencia()`, `registrar_alteracoes_form()`
- **Backfill**: `garantir_historico_estruturado()` cria evento de abertura para manutenções antigas

### 4.3 Padrão `registrado_por`
- Todos os models de registro operacional possuem `registrado_por = ForeignKey(User, on_delete=PROTECT)`
- Atribuído na view: `obj.registrado_por = request.user` antes do `save()`

---

## 5. Padrão de Templates

### 5.1 Estrutura
```
templates/
├── base.html                  ← Layout global (navbar + sidebar + main-content + footer)
├── modulo_dashboard.html      ← Seletor de módulos (home após login)
├── dashboard.html             ← Dashboard da Reserva de Armas
├── viaturas/
│   ├── dashboard.html         ← Dashboard da Frota (23KB, KPIs, alertas)
│   ├── lista_*.html           ← Listagens paginadas (Paginator, 20-25 itens)
│   ├── form_*.html            ← Formulários (crispy-bootstrap5)
│   ├── detalhe_*.html         ← Páginas de detalhe com abas/seções
│   └── historico_*.html       ← Linha do tempo append-only
```

### 5.2 Stack Frontend
- **CSS**: Bootstrap 5.3.0 (CDN) + Font Awesome 6.4.0 (CDN) + Select2 (CDN)
- **JS**: jQuery 3.6.0 + Bootstrap Bundle + Select2
- **Design tokens**: CSS variables em `base.html`
  - `--primary-color: #f1c40f` (Amarelo PMESP)
  - `--secondary-color: #2c3e50` (Azul Profundo)
  - `--sidebar-bg: #1e272e`
- **Componentes**: Glassmorphism (`backdrop-filter: blur`), cards com hover, badges semânticos

### 5.3 Padrão de Formulários
- **Biblioteca**: `django-crispy-forms` + `crispy_bootstrap5`
- **Layout**: `FormHelper` com `Layout(Row(Column(...), ...))` — `form_tag = False`
- **Renderização no template**:
```html
{% load crispy_forms_tags %}
<form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    {% crispy form %}
    <button type="submit" class="btn btn-primary">Salvar</button>
</form>
```

---

## 6. Dashboard da Frota (Atual)

### 6.1 KPIs Existentes
- Total de viaturas por status (Disponível, Em Uso, Manutenção, Baixada)
- Distribuição por tipo (4 rodas, Moto, Embarcação, Caminhão)
- Despachos ativos (sem retorno)
- Manutenções em aberto e agendamentos atrasados
- Últimos abastecimentos
- Peças com estoque baixo e últimas retiradas

### 6.2 Alertas Inteligentes (Fase 3)
- Garantias vencendo nos próximos 30 dias
- Garantias vencidas (últimos 60 dias)
- Manutenções abertas há mais de 30 dias
- Alertas de manutenção preventiva (baseado em `PlanoManutencaoPreventiva`)

### 6.3 KPIs Financeiros (Fase 4)
- Custo total da frota (peças + mão de obra)
- Custo médio por manutenção
- Tempo médio em oficina (dias)
- Top 5 viaturas mais custosas

---

## 7. APIs Existentes

| Endpoint | Módulo | Auth | Formato |
|---|---|---|---|
| `api_materiais` | `materiais` | `@login_required` | `JsonResponse` paginado |
| `api_material_detalhe` | `materiais` | `@login_required` | `JsonResponse` |
| `api_lotes_material` | `materiais` | `@login_required` | `JsonResponse` |
| `api_retirada_detalhe` | `movimentacoes` | `@login_required` | `JsonResponse` |
| `api_retiradas_pendentes` | `movimentacoes` | `@login_required` | `JsonResponse` |
| `api_policiais` | `policiais` | `@login_required` | `JsonResponse` |
| `api_policial_detalhe` | `policiais` | `@login_required` | `JsonResponse` |
| `api_lotes` | `municoes` | Público | `JsonResponse` |
| `api_retiradas_pendentes` | `municoes` | Público | `JsonResponse` |

> **Padrão**: APIs usam `JsonResponse` nativo (não DRF). Paginação manual com `Paginator`. Filtros via `request.GET`.

> **Frota**: Atualmente **não possui API dedicada**. Se necessário, seguir o mesmo padrão.

---

## 8. Relatórios

### 8.1 Motor de Relatórios
- **Engine**: ReportLab (PDF)
- **Abstração**: `relatorios/utils.py` → `PDFReportGenerator` (estilos, tabelas, cabeçalhos)
- **Providers**: `relatorios/providers.py` → classes por módulo
- **Persistência**: Model `Relatorio` salva metadata + PDF em `media/relatorios/`

### 8.2 Relatórios de Frota Já Implementados
| Provider | Tipo | Dados |
|---|---|---|
| `FrotaGeralProvider` | `FROTA_GERAL` | Inventário completo da frota |
| `FrotaAbastecimentoProvider` | `FROTA_ABASTECIMENTO` | Histórico de abastecimentos |
| `FrotaManutencaoProvider` | `FROTA_MANUTENCAO` | Histórico de manutenções |

---

## 9. Integrações Cruzadas (Cross-Module)

```
 ┌──────────┐        ┌──────────┐
 │ Policial  │◄───────│ Despacho  │ (motorista, encarregado)
 │ (policiais)│       │ Viatura  │
 └──────────┘        └──────────┘
      ▲                    │
      │                    │ atualiza
      │                    ▼
      │              ┌──────────┐
      │              │ Viatura   │── history ──▶ simple_history
      │              │ (status,  │
      │              │ odometro) │
      │              └────┬─────┘
      │                   │
      │         ┌─────────┼─────────┐
      │         ▼         ▼         ▼
      │   ┌─────────┐ ┌────────┐ ┌──────────────┐
      │   │Abasteci-│ │Manuten-│ │Checklist     │
      │   │mento    │ │ção     │ │Viatura       │
      │   └─────────┘ └───┬────┘ └──────────────┘
      │                   │
      │         ┌─────────┼──────────┐
      │         ▼         ▼          ▼
      │   ┌─────────┐ ┌─────────┐ ┌────────────┐
      │   │Servico  │ │Evidencia│ │RetiradaPeca│──▶ PecaViatura
      │   │Manuten- │ │Manuten- │ │            │    (estoque)
      │   │cao      │ │cao      │ └────────────┘
      │   └─────────┘ └─────────┘
      │
      │   ┌───────────┐       ┌──────────────┐
      └───│Solicitacao│       │Relatorio     │
          │Baixa      │       │(FROTA_*)     │
          └───────────┘       └──────────────┘
```

---

## 10. Padrões de Código Consolidados

### 10.1 Views
- **Tipo**: Function-Based Views (FBV) exclusivamente
- **Decorators**: `@login_required` + `@require_module_permission('modulo')` (sempre nessa ordem)
- **CRUD padrão**: `lista_*` (GET, paginada), `criar_*` (GET/POST), `editar_*` (GET/POST), `detalhe_*` (GET)
- **Mensagens**: `messages.success/error/warning` após cada ação
- **Redirect**: Sempre para lista ou detalhe após sucesso
- **Filtros server-side**: `request.GET.get('campo')` + `Q()` para busca textual
- **Paginação**: `Paginator(qs, 20)` → `paginator.get_page(request.GET.get('page'))`

### 10.2 Models
- **Campos de auditoria**: `data_cadastro (auto_now_add)`, `data_atualizacao (auto_now)`
- **Verbose names**: `_('Nome Amigável')` em todos os campos
- **`__str__`**: Sempre retorna identificação legível
- **Meta**: `verbose_name`, `verbose_name_plural`, `ordering`
- **`on_delete`**: `PROTECT` para FKs críticas, `SET_NULL` para opcionais, `CASCADE` para dependências
- **Status/Choices**: `STATUS_CHOICES` como lista de tuplas `('SIGLA', 'Descrição legível')`
- **Boolean fields**: `ativo = BooleanField(default=True)` para soft-delete

### 10.3 Forms
- **Base**: `ModelForm` com `FormHelper` e `Layout`
- **`form_tag = False`** (tag `<form>` fica no template)
- **Grid**: `Row(Column('campo', css_class='col-md-N'), ...)`
- **Seções**: `HTML('<h5>...</h5>')` + `HTML('<hr>')` para separar blocos

### 10.4 Admin
- **Registro**: `@admin.register(Model)` com `list_display`, `search_fields`, `list_filter`
- **Histórico**: `SimpleHistoryAdmin` quando o model possui `HistoricalRecords`
- **Inlines**: `TabularInline` para itens filhos

### 10.5 URLs
- **Padrão**: `path('prefixo/', views.lista, name='lista')`, `path('prefixo/novo/', views.criar, name='criar')`
- **Namespace**: `app_name = 'viaturas'` → referências como `viaturas:lista_viaturas`
- **Montagem**: `path('frota/', include('viaturas.urls', namespace='viaturas'))` em `reserva_baep/urls.py`

---

## 11. Recomendações para Evolução do Módulo Frota

### 11.1 Consistência Arquitetural
- **Manter FBVs**: Todo o projeto usa function-based views. Não introduzir CBVs sem motivo forte.
- **Manter o padrão de permissão**: `@login_required` + `@require_module_permission('frota')`
- **Novos models**: Seguir o padrão de `registrado_por`, `data_cadastro/data_atualizacao`, `ativo`
- **Auditoria**: Usar `HistoricalRecords` do simple_history para models com dados mutáveis sensíveis
- **Para dados imutáveis**: Seguir o padrão `ServicoManutencao` (append-only, sem update/delete)

### 11.2 Pontos de Atenção
- O grupo `reserva_armas` tem acesso ao módulo frota via `FROTA_GROUPS` nas views, mas o decorator `require_module_permission('frota')` só libera para o grupo `frota`. Há inconsistência potencial.
- A view `solicitar_baixa` não exige `require_module_permission('frota')` — é acessível a qualquer usuário logado (intencional, pois aparece em "Serviços Rápidos").
- `DespachoViatura.save()` e `Manutencao.save()` contêm lógica de negócio que atualiza automaticamente `Viatura.status` e `Viatura.localizacao`. Manter esse padrão de cascata.
- O odômetro é atualizado em múltiplos pontos (despacho, abastecimento, manutenção, checklist). Sempre usar `viatura.save(update_fields=['odometro_atual'])` para evitar race conditions.

### 11.3 Expansões Recomendadas
1. **API da Frota**: Criar endpoints `api_viaturas`, `api_viatura_detalhe`, `api_despachos_ativos` seguindo o padrão `JsonResponse` + `@login_required`
2. **Documentos de Viatura**: Model para CRLV, seguro, IPVA com alertas de vencimento
3. **Escala de Motoristas**: Vincular `Policial` a viaturas em turnos/escalas
4. **Consumo Médio**: Calcular km/litro automaticamente a partir de abastecimentos + odômetros
5. **Importação de Dados**: A view `importar_viaturas` já suporta XML/XLSX; manter e estender

---

## 12. Diagrama de Deploy

```
┌─────────────────────────────────────────────┐
│              Docker Container                │
│  Python 3.14-slim + Django 5.x              │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ Gunicorn  │  │WhiteNoise│  │  SQLite /  │ │
│  │ 3 workers │  │ (static) │  │ PostgreSQL │ │
│  │ :8000     │  │          │  │           │ │
│  └──────────┘  └──────────┘  └───────────┘ │
│                                              │
│  Media files: /app/media/viaturas/...        │
│  Logs: /app/logs/baep_sistema.log            │
└─────────────────────────────────────────────┘
```

---

*Documento gerado para orientar a evolução do módulo Frota dentro do SIS LOGÍSTICA 2º BAEP.*
