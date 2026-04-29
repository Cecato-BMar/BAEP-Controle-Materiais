from django.utils import timezone
from django.db.models import Count, Sum, Q, F
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import cm
from .utils import PDFReportGenerator
from materiais.models import Material
from estoque.models import Produto, MovimentacaoEstoque
from viaturas.models import Viatura, Manutencao
from patrimonio.models import ItemPatrimonial
from movimentacoes.models import Movimentacao
from telematica.models import Equipamento, SolicitacaoSuporteTI, LinhaMovel, ServicoTI, CategoriaEquipamento

class ReportProvider:
    def __init__(self, generator=None):
        self.gen = generator

    def get_data_and_columns(self, filters=None):
        """Retorna uma lista de dicionários com 'title', 'columns' e 'data'"""
        raise NotImplementedError("Subclasses devem implementar get_data_and_columns")

    def get_elements(self, filters=None):
        if not self.gen:
            return []
        
        report_data_list = self.get_data_and_columns(filters)
        elements = []
        
        for report in report_data_list:
            if report.get('title'):
                elements.append(Paragraph(report['title'], self.gen.styles['SectionHeader']))
            
            # Converte dados para PDF (adiciona cabeçalho)
            table_data = [report['columns']] + report['data']
            
            # Estilos especiais se necessário
            style = report.get('style', 'NORMAL')
            elements.append(self.gen.create_table(table_data, col_widths=report.get('col_widths'), style_type=style))
            elements.append(Spacer(1, 10))
            
        return elements

class TelematicaProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        results = []
        filters = filters or {}
        tipo = filters.get('tipo_relatorio', 'TELEMATICA_GERAL')
        
        if tipo == 'TELEMATICA_GERAL' or tipo == 'TELEMATICA_INVENTARIO':
            equips = Equipamento.objects.select_related('categoria').all().order_by('categoria__nome', 'hostname')
            if filters.get('categoria'): equips = equips.filter(categoria_id=filters['categoria'])
            if filters.get('status'): equips = equips.filter(status=filters['status'])
            if filters.get('codigo_unidade'): equips = equips.filter(codigo_unidade__icontains=filters['codigo_unidade'])

            data = []
            for e in equips:
                data.append([
                    e.numero_serie, 
                    e.hostname or '-', 
                    e.categoria.nome, 
                    e.get_status_display(), 
                    f"{e.setor.sigla if e.setor else '-'} | {e.policial_responsavel.nome if e.policial_responsavel else e.usuario_responsavel or 'Uso Geral'}"
                ])
            
            results.append({
                'title': "Inventário Geral de Ativos Tecnológicos",
                'columns': ['ID/Série', 'Hostname', 'Categoria', 'Status', 'Local/Setor'],
                'data': data,
                'col_widths': [3.5*cm, 4*cm, 3.5*cm, 2.5*cm, 4*cm]
            })
            
        elif tipo == 'TELEMATICA_MANUTENCAO':
            manuts = SolicitacaoSuporteTI.objects.select_related('equipamento', 'tecnico_atribuido').all().order_by('-data_solicitacao')
            if filters.get('data_inicio'): manuts = manuts.filter(data_solicitacao__gte=filters['data_inicio'])
            if filters.get('data_fim'): manuts = manuts.filter(data_solicitacao__lte=filters['data_fim'])

            data = []
            for m in manuts:
                data.append([
                    str(m.equipamento) if m.equipamento else "S/ Equipamento",
                    m.get_tipo_servico_display(),
                    m.data_solicitacao.strftime('%d/%m/%Y'),
                    m.get_status_display(),
                    str(m.tecnico_atribuido or m.tecnico_externo or '-')
                ])
            
            results.append({
                'title': "Relatório de Manutenções e Suporte Técnico",
                'columns': ['Equipamento', 'Tipo', 'Abertura', 'Status', 'Técnico'],
                'data': data,
                'col_widths': [5*cm, 3.5*cm, 2.5*cm, 2.5*cm, 4*cm]
            })

        elif tipo == 'TELEMATICA_LINHAS':
            linhas = LinhaMovel.objects.select_related('equipamento_vinculado').all().order_by('numero')
            data = []
            for l in linhas:
                vinculo = str(l.equipamento_vinculado) if l.equipamento_vinculado else 'Disponível'
                data.append([l.numero, l.operadora, l.iccid, vinculo, 'Ativa' if l.ativo else 'Inativa'])
            
            results.append({
                'title': "Relatório de Linhas Móveis e Chips",
                'columns': ['Número', 'Operadora', 'ICCID (Chip)', 'Vínculo', 'Status'],
                'data': data,
                'col_widths': [3.5*cm, 3*cm, 4.5*cm, 4.5*cm, 2*cm]
            })

        return results

class SituacaoAtualProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        results = []
        
        total = Material.objects.count()
        disp = Material.objects.filter(status='DISPONIVEL').count()
        uso = Material.objects.filter(status='EM_USO').count()
        manut = Material.objects.filter(status='MANUTENCAO').count()
        inat = Material.objects.filter(status='INATIVO').count()
        
        results.append({
            'title': "Resumo Consolidado de Carga",
            'columns': ['Status de Operacionalidade', 'Quantidade'],
            'data': [
                ['Total de Itens em Carga', str(total)],
                ['Disponíveis para Emprego Imediato', str(disp)],
                ['Em Uso / Cautelados no Efetivo', str(uso)],
                ['Em Manutenção / Indisponíveis', str(manut)],
                ['Inativos / Baixados', str(inat)],
            ],
            'col_widths': [12*cm, 4*cm]
        })
        
        tipos = Material.objects.values('tipo').annotate(
            total=Count('id'),
            disp=Count('id', filter=Q(status='DISPONIVEL')),
            uso=Count('id', filter=Q(status='EM_USO')),
            manut=Count('id', filter=Q(status='MANUTENCAO'))
        ).order_by('tipo')
        
        tipo_map = dict(Material.TIPO_CHOICES)
        detalhe_data = []
        for t in tipos:
            detalhe_data.append([
                tipo_map.get(t['tipo'], t['tipo']),
                str(t['total']), str(t['disp']), str(t['uso']), str(t['manut'])
            ])
            
        results.append({
            'title': "Detalhamento por Classe de Material",
            'columns': ['Classe de Material', 'Total', 'Disp.', 'Uso', 'Manut.'],
            'data': detalhe_data,
            'col_widths': [6*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm]
        })
        return results

class MateriaisProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        materiais = Material.objects.all().order_by('tipo', 'numero')
        if filters:
            if filters.get('tipo_material'): materiais = materiais.filter(tipo=filters['tipo_material'])
            if filters.get('status'): materiais = materiais.filter(status=filters['status'])
            
        data = []
        for m in materiais:
            data.append([m.identificacao, m.nome, m.get_tipo_display(), m.get_status_display(), m.get_estado_display()])
            
        return [{
            'title': "Relatório Detalhado de Material Bélico",
            'columns': ['ID / Prefixo', 'Nome do Material', 'Tipo', 'Status', 'Estado'],
            'data': data,
            'col_widths': [3*cm, 5*cm, 3*cm, 3*cm, 2*cm]
        }]

class MovimentacoesProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        movs = Movimentacao.objects.select_related('material', 'policial').all().order_by('-data_hora')
        if filters:
            if filters.get('data_inicio'): movs = movs.filter(data_hora__date__gte=filters['data_inicio'])
            if filters.get('data_fim'): movs = movs.filter(data_hora__date__lte=filters['data_fim'])
            
        data = []
        for mov in movs[:100]:
            data.append([
                timezone.localtime(mov.data_hora).strftime('%d/%m/%Y %H:%M'), 
                mov.tipo, 
                mov.material.identificacao, 
                mov.policial.nome, 
                str(mov.quantidade)
            ])
            
        return [{
            'title': "Histórico de Fluxo de Arsenal",
            'columns': ['Data/Hora', 'Tipo', 'Material', 'Militar', 'Qtd'],
            'data': data,
            'col_widths': [3.5*cm, 2.5*cm, 3*cm, 5*cm, 2*cm]
        }]

class EstoqueCriticoProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        produtos = Produto.objects.filter(estoque_atual__lte=F('estoque_minimo'))
        if not produtos.exists():
            return [{
                'title': "Itens com Estoque Abaixo do Mínimo",
                'columns': ['Aviso'],
                'data': [['Não há itens em nível crítico no momento.']],
            }]
            
        data = []
        for p in produtos:
            data.append([
                p.codigo, p.nome, str(p.estoque_atual), str(p.estoque_minimo), 
                p.unidade_medida.sigla if p.unidade_medida else 'un'
            ])
            
        return [{
            'title': "Itens com Estoque Abaixo do Mínimo",
            'columns': ['Código', 'Material', 'Qtd. Atual', 'Qtd. Mínima', 'Unidade'],
            'data': data,
            'style': 'DANGER'
        }]

class FrotaGeralProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        viaturas = Viatura.objects.select_related('modelo', 'modelo__marca').all().order_by('prefixo')
        data = []
        for v in viaturas:
            data.append([v.prefixo, v.placa, str(v.modelo), v.get_status_display(), str(v.odometro_atual)])
            
        return [{
            'title': "Relatório Geral de Frota",
            'columns': ['Prefixo', 'Placa', 'Modelo', 'Status', 'KM Atual'],
            'data': data,
        }]

class FrotaAbastecimentoProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        from viaturas.models import Abastecimento
        abast = Abastecimento.objects.select_related('viatura', 'motorista').all().order_by('-data_abastecimento')
        if filters:
            if filters.get('data_inicio'): abast = abast.filter(data_abastecimento__date__gte=filters['data_inicio'])
            if filters.get('data_fim'): abast = abast.filter(data_abastecimento__date__lte=filters['data_fim'])

        data = []
        for a in abast:
            data.append([
                a.data_abastecimento.strftime('%d/%m/%Y'),
                a.viatura.prefixo,
                a.get_combustivel_display(),
                str(a.quantidade_litros),
                f"R$ {a.valor_total:,.2f}" if a.valor_total else '-',
                a.motorista.nome if a.motorista else '-'
            ])
            
        return [{
            'title': "Relatório de Abastecimentos por Período",
            'columns': ['Data', 'Viatura', 'Combustível', 'Litros', 'Valor (R$)', 'Motorista'],
            'data': data,
            'col_widths': [3*cm, 3*cm, 3*cm, 2*cm, 2.5*cm, 3.5*cm]
        }]

class FrotaManutencaoProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        manut = Manutencao.objects.select_related('viatura', 'oficina_fk').all().order_by('-data_inicio')
        if filters:
            if filters.get('data_inicio'): manut = manut.filter(data_inicio__gte=filters['data_inicio'])
            if filters.get('data_fim'): manut = manut.filter(data_inicio__lte=filters['data_fim'])

        data = []
        for m in manut:
            data.append([
                m.viatura.prefixo,
                m.get_tipo_display(),
                m.data_inicio.strftime('%d/%m/%Y'),
                m.data_conclusao.strftime('%d/%m/%Y') if m.data_conclusao else 'Em andamento',
                m.oficina_fk.nome if m.oficina_fk else (m.oficina or '-'),
                f"R$ {m.custo_total:,.2f}"
            ])
            
        return [{
            'title': "Relatório de Manutenções por Período",
            'columns': ['Viatura', 'Tipo', 'Início', 'Conclusão', 'Oficina', 'Custo Total'],
            'data': data,
            'col_widths': [2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 4.5*cm, 2.5*cm]
        }]

class PatrimonioProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        itens = ItemPatrimonial.objects.select_related('bem', 'localizacao').all().order_by('numero_patrimonio')
        data = []
        for it in itens:
            data.append([
                it.numero_patrimonio, 
                it.bem.nome, 
                it.localizacao.nome if it.localizacao else 'Não Localizado', 
                it.get_status_display()
            ])
            
        return [{
            'title': "Inventário Geral de Patrimônio",
            'columns': ['Nº Patrimônio', 'Descrição do Bem', 'Localização', 'Estado'],
            'data': data,
            'col_widths': [3.5*cm, 6.5*cm, 3.5*cm, 2.5*cm]
        }]

class EstoqueMovimentacoesProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        movs = MovimentacaoEstoque.objects.select_related('produto', 'militar_requisitante', 'fornecedor').all().order_by('-data_movimentacao', '-data_hora')
        if filters:
            if filters.get('tipo_movimentacao'): movs = movs.filter(tipo_movimentacao=filters['tipo_movimentacao'])
            if filters.get('produto'): movs = movs.filter(produto=filters['produto'])
            if filters.get('data_inicio'): movs = movs.filter(data_movimentacao__gte=filters['data_inicio'])
            if filters.get('data_fim'): movs = movs.filter(data_movimentacao__lte=filters['data_fim'])

        data = []
        for m in movs:
            requisitante = str(m.militar_requisitante) if m.militar_requisitante else (str(m.fornecedor) if m.fornecedor else '-')
            data.append([
                m.data_movimentacao.strftime('%d/%m/%Y'),
                m.get_subtipo_display(),
                m.produto.nome,
                f"{'+' if m.tipo_movimentacao == 'ENTRADA' else '-'}{m.quantidade:.2f}",
                f"R$ {m.valor_unitario:,.2f}",
                requisitante
            ])
            
        return [{
            'title': "Relatório de Fluxo de Insumos (Estoque)",
            'columns': ['Data', 'Tipo', 'Material', 'Qtd', 'V. Unit', 'Militar / Fornecedor'],
            'data': data,
            'col_widths': [2.5*cm, 2.5*cm, 4*cm, 2*cm, 2.5*cm, 5*cm]
        }]

class EstoqueSituacaoProvider(ReportProvider):
    def get_data_and_columns(self, filters=None):
        produtos = Produto.objects.select_related('categoria', 'unidade_medida').all().order_by('categoria__nome', 'nome')
        
        data = []
        for p in produtos:
            data.append([
                p.nome,
                p.categoria.nome if p.categoria else '-',
                f"{p.estoque_atual:.2f}",
                f"{p.estoque_minimo:.2f}",
                p.unidade_medida.sigla if p.unidade_medida else 'un'
            ])
            
        return [{
            'title': "Inventário Geral de Consumo - Situação Atual",
            'columns': ['Material', 'Categoria', 'Estoque Atual', 'E. Mínimo', 'Unidade'],
            'data': data,
            'col_widths': [7*cm, 3.5*cm, 2*cm, 2*cm, 2*cm]
        }]
