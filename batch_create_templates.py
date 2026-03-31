import os

def create_if_missing(name, content):
    path = os.path.join('templates/estoque', name)
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"CREATED: {name}")

# FORMS
form_files = [
    'form_categoria.html', 'form_unidade_medida.html', 'form_unidade_fornecimento.html',
    'form_cor.html', 'form_conta_patrimonial.html', 'form_orgao.html',
    'form_local_fisico.html', 'form_militar.html', 'form_fornecedor.html',
    'form_inventario.html', 'form_localizacao.html'
]

for f in form_files:
    create_if_missing(f, '{% extends "estoque/form_generico.html" %}')


# LISTS (using the simple generic list style)
list_generic_content = """{% extends 'estoque/lista_generica.html' %}
{% block table_rows %}
{% for o in page_obj|default:objetos %}
<tr>
    {% if o.codigo %}<td><code>{{ o.codigo }}</code></td>{% endif %}
    {% if o.sigla %}<td><code>{{ o.sigla }}</code></td>{% endif %}
    {% if o.re %}<td><code>{{ o.re }}</code></td>{% endif %}
    <td>{{ o.nome|default:o.descricao|default:o.qra }}</td>
    {% if o.categoria_pai %}<td>{{ o.categoria_pai.nome }}</td>{% endif %}
    <td class="text-center">
        {% if o.ativo %}
            <span class="badge bg-success">Ativo</span>
        {% else %}
            <span class="badge bg-danger">Inativo</span>
        {% endif %}
    </td>
    <td class="text-end">
        <a href="#" class="btn btn-xs btn-outline-secondary btn-sm"><i class="fas fa-pencil-alt"></i></a>
    </td>
</tr>
{% endfor %}
{% endblock %}"""

list_files = [
    'lista_categorias.html', 'lista_unidades.html', 'lista_cores.html',
    'lista_fornecedores.html', 'lista_contas_patrimoniais.html',
    'lista_orgaos.html', 'lista_localizacoes.html'
]

for f in list_files:
    create_if_missing(f, list_generic_content)

# Special Lists
create_if_missing('lista_inventarios.html', """{% extends 'estoque/base.html' %}
{% block estoque_content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h4><i class="fas fa-clipboard-list me-2"></i>Inventários PAP</h4>
    <a href="{% url 'estoque:criar_inventario' %}" class="btn btn-primary btn-sm">Novo Inventário</a>
</div>
<div class="card border-0 shadow-sm">
    <div class="card-body p-0">
        <table class="table table-sm table-hover mb-0">
            <thead class="table-light"><tr><th>Número</th><th>Tipo</th><th>Status</th><th>Data Início</th><th>Ações</th></tr></thead>
            <tbody>
                {% for inv in page_obj %}
                <tr>
                    <td>{{ inv.numero }}</td>
                    <td>{{ inv.get_tipo_inventario_display }}</td>
                    <td><span class="badge bg-info">{{ inv.get_status_display }}</span></td>
                    <td>{{ inv.data_inicio|date:"d/m/Y"|default:"—" }}</td>
                    <td><a href="{% url 'estoque:detalhe_inventario' inv.pk %}" class="btn btn-xs btn-outline-primary btn-sm"><i class="fas fa-eye"></i></a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}""")

# Reports Placeholders (stubs)
report_stub = "{% extends 'estoque/relatorio_estoque.html' %}"
report_files = [
    'relatorio_baixas.html', 'relatorio_estoque_baixo.html',
    'relatorio_inventarios.html', 'relatorio_movimentacoes.html',
    'relatorio_situacao.html'
]
for f in report_files:
    create_if_missing(f, report_stub)
