from django.utils import timezone
from django.db.models import Count, Sum, Q, F
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import cm
from .utils import PDFReportGenerator
from materiais.models import Material
from estoque.models import Produto, MovimentacaoEstoque
from viaturas.models import Viatura, Manutencao, DespachoViatura, Abastecimento, Oficina, ServicoManutencao, DocumentoViatura
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


# ============================================================================
# PROVIDERS DE FROTA — RELATÓRIOS DETALHADOS
# ============================================================================
from decimal import Decimal


class FrotaHistoricoViaturaProvider(ReportProvider):
    """Histórico completo de uma viatura: despachos, manutenções, abastecimentos e documentos."""

    def get_data_and_columns(self, filters=None):
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.units import cm as cm_unit

        filters = filters or {}
        viatura_id = filters.get('viatura')
        if not viatura_id:
            return [{'title': 'Erro', 'columns': ['Aviso'], 'data': [['Viatura não selecionada.']]}]

        try:
            viatura = Viatura.objects.select_related('modelo', 'modelo__marca').get(pk=viatura_id)
        except Viatura.DoesNotExist:
            return [{'title': 'Erro', 'columns': ['Aviso'], 'data': [['Viatura não encontrada.']]}]

        data_inicio = filters.get('data_inicio')
        data_fim = filters.get('data_fim')
        results = []

        # ——— Cabeçalho: Dados da Viatura ———
        results.append({
            'title': f"DADOS DA VIATURA: {viatura.prefixo}",
            'columns': ['Campo', 'Valor'],
            'data': [
                ['Prefixo', viatura.prefixo],
                ['Placa', viatura.placa or 'N/A'],
                ['Marca / Modelo', f"{viatura.modelo.marca.nome} {viatura.modelo.nome}"],
                ['Tipo', viatura.modelo.get_tipo_display()],
                ['Ano', str(viatura.ano_fabricacao) if viatura.ano_fabricacao else 'N/A'],
                ['Odômetro Atual', f"{viatura.odometro_atual} km"],
                ['Status', viatura.get_status_display()],
                ['Combustível', viatura.get_tipo_combustivel_display()],
            ],
            'col_widths': [6 * cm_unit, 10 * cm_unit],
        })

        # ——— Despachos ———
        despachos = DespachoViatura.objects.filter(
            viatura=viatura
        ).select_related('motorista').order_by('-data_saida')
        if data_inicio:
            despachos = despachos.filter(data_saida__date__gte=data_inicio)
        if data_fim:
            despachos = despachos.filter(data_saida__date__lte=data_fim)

        desp_data = []
        for d in despachos:
            desp_data.append([
                d.data_saida.strftime('%d/%m/%Y %H:%M'),
                str(d.motorista.nome) if d.motorista else 'N/A',
                str(d.km_saida),
                d.data_retorno.strftime('%d/%m/%Y %H:%M') if d.data_retorno else 'Em curso',
                str(d.km_retorno) if d.km_retorno else '-',
            ])
        if desp_data:
            results.append({
                'title': f"DESPACHOS ({len(desp_data)} registros)",
                'columns': ['Saída', 'Motorista', 'Km Saída', 'Retorno', 'Km Retorno'],
                'data': desp_data,
                'col_widths': [3.5 * cm_unit, 4 * cm_unit, 2.5 * cm_unit, 3.5 * cm_unit, 2.5 * cm_unit],
            })

        # ——— Manutenções ———
        manutencoes = Manutencao.objects.filter(
            viatura=viatura
        ).select_related('oficina_fk').order_by('-data_inicio')
        if data_inicio:
            manutencoes = manutencoes.filter(data_inicio__gte=data_inicio)
        if data_fim:
            manutencoes = manutencoes.filter(data_inicio__lte=data_fim)

        manut_data = []
        custo_total_manut = Decimal('0')
        for m in manutencoes:
            manut_data.append([
                m.get_tipo_display(),
                m.data_inicio.strftime('%d/%m/%Y'),
                m.data_conclusao.strftime('%d/%m/%Y') if m.data_conclusao else 'Aberta',
                m.get_status_display(),
                m.oficina_fk.nome if m.oficina_fk else (m.oficina or '-'),
                f"R$ {m.custo_total:,.2f}",
            ])
            custo_total_manut += m.custo_total
        if manut_data:
            results.append({
                'title': f"MANUTENÇÕES ({len(manut_data)} registros) — Total: R$ {custo_total_manut:,.2f}",
                'columns': ['Tipo', 'Início', 'Conclusão', 'Status', 'Oficina', 'Custo'],
                'data': manut_data,
                'col_widths': [2.5 * cm_unit, 2.5 * cm_unit, 2.5 * cm_unit, 2.5 * cm_unit, 3.5 * cm_unit, 2.5 * cm_unit],
            })

        # ——— Abastecimentos ———
        abastecimentos = Abastecimento.objects.filter(
            viatura=viatura
        ).select_related('motorista').order_by('-data_abastecimento')
        if data_inicio:
            abastecimentos = abastecimentos.filter(data_abastecimento__date__gte=data_inicio)
        if data_fim:
            abastecimentos = abastecimentos.filter(data_abastecimento__date__lte=data_fim)

        abast_data = []
        total_litros = Decimal('0')
        total_valor = Decimal('0')
        for a in abastecimentos:
            abast_data.append([
                a.data_abastecimento.strftime('%d/%m/%Y'),
                a.get_combustivel_display(),
                f"{a.quantidade_litros} L",
                f"R$ {a.valor_total:,.2f}" if a.valor_total else '-',
                str(a.odometro),
                a.motorista.nome if a.motorista else '-',
            ])
            total_litros += a.quantidade_litros
            total_valor += (a.valor_total or Decimal('0'))
        if abast_data:
            results.append({
                'title': f"ABASTECIMENTOS ({len(abast_data)} registros) — {total_litros} L / R$ {total_valor:,.2f}",
                'columns': ['Data', 'Combustível', 'Litros', 'Valor', 'Odômetro', 'Motorista'],
                'data': abast_data,
                'col_widths': [2.5 * cm_unit, 3 * cm_unit, 2 * cm_unit, 2.5 * cm_unit, 2.5 * cm_unit, 3.5 * cm_unit],
            })

        # ——— Documentos ———
        documentos = DocumentoViatura.objects.filter(
            viatura=viatura, ativo=True
        ).order_by('data_vencimento')
        doc_data = []
        for doc in documentos:
            doc_data.append([
                doc.get_tipo_display(),
                doc.numero_documento or 'N/A',
                doc.data_emissao.strftime('%d/%m/%Y') if doc.data_emissao else '-',
                doc.data_vencimento.strftime('%d/%m/%Y') if doc.data_vencimento else '-',
            ])
        if doc_data:
            results.append({
                'title': f"DOCUMENTOS ({len(doc_data)} registros)",
                'columns': ['Tipo', 'Número', 'Emissão', 'Vencimento'],
                'data': doc_data,
                'col_widths': [5 * cm_unit, 5 * cm_unit, 3 * cm_unit, 3 * cm_unit],
            })

        return results


class FrotaHistoricoManutencaoProvider(ReportProvider):
    """Histórico de manutenções com serviços executados e custos."""

    def get_data_and_columns(self, filters=None):
        filters = filters or {}
        manutencoes = Manutencao.objects.select_related(
            'viatura', 'viatura__modelo', 'viatura__modelo__marca', 'oficina_fk'
        ).all().order_by('-data_inicio')

        if filters.get('data_inicio'):
            manutencoes = manutencoes.filter(data_inicio__gte=filters['data_inicio'])
        if filters.get('data_fim'):
            manutencoes = manutencoes.filter(data_inicio__lte=filters['data_fim'])
        if filters.get('tipo_manutencao'):
            manutencoes = manutencoes.filter(tipo=filters['tipo_manutencao'])
        if filters.get('viatura'):
            manutencoes = manutencoes.filter(viatura_id=filters['viatura'])
        if filters.get('status'):
            manutencoes = manutencoes.filter(status=filters['status'])

        results = []
        custo_geral = Decimal('0')

        # Tabela principal
        data = []
        for m in manutencoes:
            custo_geral += m.custo_total
            data.append([
                m.viatura.prefixo,
                m.get_tipo_display(),
                m.data_inicio.strftime('%d/%m/%Y'),
                m.data_conclusao.strftime('%d/%m/%Y') if m.data_conclusao else 'Aberta',
                m.get_status_display(),
                f"{m.odometro} km",
                m.oficina_fk.nome if m.oficina_fk else (m.oficina or '-'),
                m.ordem_servico or '-',
                f"R$ {m.custo_pecas:,.2f}",
                f"R$ {m.custo_mao_obra:,.2f}",
                f"R$ {m.custo_total:,.2f}",
            ])

        if data:
            results.append({
                'title': f"HISTÓRICO DE MANUTENÇÕES ({len(data)} registros) — Custo Total: R$ {custo_geral:,.2f}",
                'columns': ['Viatura', 'Tipo', 'Início', 'Conclusão', 'Status', 'KM', 'Oficina', 'O.S.', 'Peças', 'M.O.', 'Total'],
                'data': data,
                'col_widths': [1.5 * cm, 1.5 * cm, 1.8 * cm, 1.8 * cm, 1.5 * cm, 1.5 * cm, 2.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm],
            })

        # Detalhes dos serviços executados (últimas 50)
        servicos = ServicoManutencao.objects.filter(
            manutencao__in=manutencoes[:50]
        ).select_related('manutencao', 'manutencao__viatura').order_by('-manutencao__data_inicio')

        if servicos.exists():
            serv_data = []
            for s in servicos:
                serv_data.append([
                    s.manutencao.viatura.prefixo,
                    s.manutencao.ordem_servico or str(s.manutencao.pk),
                    s.descricao[:60],
                    f"{s.odometro} km" if s.odometro else '-',
                    f"R$ {s.custo_pecas + s.custo_mao_obra:,.2f}",
                ])
            if serv_data:
                results.append({
                    'title': f"SERVIÇOS EXECUTADOS ({len(serv_data)} registros)",
                    'columns': ['Viatura', 'O.S.', 'Descrição', 'Odômetro', 'Custo'],
                    'data': serv_data,
                    'col_widths': [2 * cm, 2.5 * cm, 8 * cm, 2 * cm, 2 * cm],
                })

        return results


class FrotaGastosPeriodoProvider(ReportProvider):
    """Gastos de manutenção e abastecimento agrupados por mês."""

    def get_data_and_columns(self, filters=None):
        from django.db.models.functions import TruncMonth

        filters = filters or {}
        data_inicio = filters.get('data_inicio')
        data_fim = filters.get('data_fim')

        # ——— Gastos de Manutenção por Mês ———
        manut_qs = Manutencao.objects.filter(status='CONCLUIDA')
        if data_inicio:
            manut_qs = manut_qs.filter(data_inicio__gte=data_inicio)
        if data_fim:
            manut_qs = manut_qs.filter(data_inicio__lte=data_fim)

        manut_mes = (
            manut_qs
            .annotate(mes=TruncMonth('data_inicio'))
            .values('mes')
            .annotate(
                total_pecas=Sum('custo_pecas'),
                total_mao_obra=Sum('custo_mao_obra'),
                qtd=Count('id'),
            )
            .order_by('mes')
        )

        results = []
        manut_data = []
        total_pecas = Decimal('0')
        total_mo = Decimal('0')
        for row in manut_mes:
            pecas = row['total_pecas'] or Decimal('0')
            mo = row['total_mao_obra'] or Decimal('0')
            total_pecas += pecas
            total_mo += mo
            manut_data.append([
                row['mes'].strftime('%m/%Y') if row['mes'] else '-',
                str(row['qtd']),
                f"R$ {pecas:,.2f}",
                f"R$ {mo:,.2f}",
                f"R$ {pecas + mo:,.2f}",
            ])
        if manut_data:
            manut_data.append([
                'TOTAL', '', f"R$ {total_pecas:,.2f}",
                f"R$ {total_mo:,.2f}", f"R$ {total_pecas + total_mo:,.2f}",
            ])
            results.append({
                'title': f"GASTOS DE MANUTENÇÃO POR MÊS — Total: R$ {total_pecas + total_mo:,.2f}",
                'columns': ['Mês', 'Qtd.', 'Peças', 'Mão de Obra', 'Total'],
                'data': manut_data,
                'col_widths': [3 * cm, 2 * cm, 4 * cm, 4 * cm, 4 * cm],
            })

        # ——— Gastos de Abastecimento por Mês ———
        abast_qs = Abastecimento.objects.all()
        if data_inicio:
            abast_qs = abast_qs.filter(data_abastecimento__date__gte=data_inicio)
        if data_fim:
            abast_qs = abast_qs.filter(data_abastecimento__date__lte=data_fim)

        abast_mes = (
            abast_qs
            .annotate(mes=TruncMonth('data_abastecimento'))
            .values('mes')
            .annotate(
                total_litros=Sum('quantidade_litros'),
                total_valor=Sum('valor_total'),
                qtd=Count('id'),
            )
            .order_by('mes')
        )

        abast_data = []
        total_litros = Decimal('0')
        total_valor_abast = Decimal('0')
        for row in abast_mes:
            litros = row['total_litros'] or Decimal('0')
            valor = row['total_valor'] or Decimal('0')
            total_litros += litros
            total_valor_abast += valor
            abast_data.append([
                row['mes'].strftime('%m/%Y') if row['mes'] else '-',
                str(row['qtd']),
                f"{litros:,.1f} L",
                f"R$ {valor:,.2f}",
            ])
        if abast_data:
            abast_data.append([
                'TOTAL', '', f"{total_litros:,.1f} L",
                f"R$ {total_valor_abast:,.2f}",
            ])
            results.append({
                'title': f"GASTOS DE ABASTECIMENTO POR MÊS — Total: R$ {total_valor_abast:,.2f}",
                'columns': ['Mês', 'Qtd.', 'Litros', 'Valor'],
                'data': abast_data,
                'col_widths': [4 * cm, 3 * cm, 4.5 * cm, 4.5 * cm],
            })

        # ——— Resumo Consolidado ———
        if manut_data or abast_data:
            resumo = [
                ['Manutenção', f"R$ {total_pecas + total_mo:,.2f}"],
                ['Abastecimento', f"R$ {total_valor_abast:,.2f}"],
                ['TOTAL GERAL', f"R$ {total_pecas + total_mo + total_valor_abast:,.2f}"],
            ]
            results.insert(0, {
                'title': "RESUMO CONSOLIDADO",
                'columns': ['Categoria', 'Valor Total'],
                'data': resumo,
                'col_widths': [8 * cm, 8 * cm],
            })

        return results


class FrotaGastosOficinaProvider(ReportProvider):
    """Gastos agrupados por oficina (com contagem de manutenções e custo médio)."""

    def get_data_and_columns(self, filters=None):
        filters = filters or {}
        manut_qs = Manutencao.objects.all()
        if filters.get('data_inicio'):
            manut_qs = manut_qs.filter(data_inicio__gte=filters['data_inicio'])
        if filters.get('data_fim'):
            manut_qs = manut_qs.filter(data_inicio__lte=filters['data_fim'])

        # ——— Por Oficina cadastrada ———
        oficina_agg = (
            manut_qs
            .filter(oficina_fk__isnull=False)
            .values('oficina_fk__nome', 'oficina_fk__cidade')
            .annotate(
                total_pecas=Sum('custo_pecas'),
                total_mao_obra=Sum('custo_mao_obra'),
                qtd_manutencoes=Count('id'),
            )
            .order_by('-total_pecas', '-total_mao_obra')
        )

        results = []
        data = []
        custo_geral = Decimal('0')
        for row in oficina_agg:
            pecas = row['total_pecas'] or Decimal('0')
            mo = row['total_mao_obra'] or Decimal('0')
            total = pecas + mo
            custo_geral += total
            qtd = row['qtd_manutencoes']
            custo_medio = total / qtd if qtd else Decimal('0')
            data.append([
                row['oficina_fk__nome'],
                row.get('oficina_fk__cidade') or '-',
                str(qtd),
                f"R$ {pecas:,.2f}",
                f"R$ {mo:,.2f}",
                f"R$ {total:,.2f}",
                f"R$ {custo_medio:,.2f}",
            ])

        # ——— Por Oficina texto livre ———
        texto_agg = (
            manut_qs
            .filter(oficina_fk__isnull=True, oficina__isnull=False)
            .exclude(oficina='')
            .values('oficina')
            .annotate(
                total_pecas=Sum('custo_pecas'),
                total_mao_obra=Sum('custo_mao_obra'),
                qtd_manutencoes=Count('id'),
            )
            .order_by('-total_pecas', '-total_mao_obra')
        )
        for row in texto_agg:
            pecas = row['total_pecas'] or Decimal('0')
            mo = row['total_mao_obra'] or Decimal('0')
            total = pecas + mo
            custo_geral += total
            qtd = row['qtd_manutencoes']
            custo_medio = total / qtd if qtd else Decimal('0')
            data.append([
                row['oficina'], '-', str(qtd),
                f"R$ {pecas:,.2f}", f"R$ {mo:,.2f}",
                f"R$ {total:,.2f}", f"R$ {custo_medio:,.2f}",
            ])

        if data:
            data.append([
                'TOTAL', '', str(sum(int(r[2]) for r in data)),
                '', '', f"R$ {custo_geral:,.2f}", '',
            ])
            results.append({
                'title': f"GASTOS POR OFICINA — Total: R$ {custo_geral:,.2f}",
                'columns': ['Oficina', 'Cidade', 'Qtd.', 'Peças', 'M. Obra', 'Total', 'Custo Médio'],
                'data': data,
                'col_widths': [4 * cm, 2 * cm, 1.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2 * cm],
            })

        # ——— Detalhamento por oficina (top 5) ———
        top_oficinas = sorted(
            list(oficina_agg) + list(texto_agg),
            key=lambda x: float((x.get('total_pecas') or 0) + (x.get('total_mao_obra') or 0)),
            reverse=True,
        )[:5]

        for of in top_oficinas:
            nome = of.get('oficina_fk__nome') or of.get('oficina', 'N/A')
            manuts = manut_qs.filter(
                oficina_fk__nome=nome
            ) if of.get('oficina_fk__nome') else manut_qs.filter(oficina=nome)

            detalhe = []
            for m in manuts.order_by('-data_inicio')[:20]:
                detalhe.append([
                    m.viatura.prefixo,
                    m.get_tipo_display(),
                    m.data_inicio.strftime('%d/%m/%Y'),
                    m.descricao[:50],
                    f"R$ {m.custo_total:,.2f}",
                ])
            if detalhe:
                results.append({
                    'title': f"Detalhamento — {nome}",
                    'columns': ['Viatura', 'Tipo', 'Data', 'Descrição', 'Custo'],
                    'data': detalhe,
                    'col_widths': [2.5 * cm, 2.5 * cm, 2.5 * cm, 7 * cm, 2.5 * cm],
                })

        return results


class FrotaGastosViaturaProvider(ReportProvider):
    """Gastos agrupados por viatura (manutenção + abastecimento)."""

    def get_data_and_columns(self, filters=None):
        filters = filters or {}
        data_inicio = filters.get('data_inicio')
        data_fim = filters.get('data_fim')

        # Manutenções por viatura
        manut_qs = Manutencao.objects.filter(status='CONCLUIDA')
        if data_inicio:
            manut_qs = manut_qs.filter(data_inicio__gte=data_inicio)
        if data_fim:
            manut_qs = manut_qs.filter(data_inicio__lte=data_fim)

        manut_agg = (
            manut_qs
            .values(
                'viatura__prefixo',
                'viatura__modelo__marca__nome',
                'viatura__modelo__nome',
            )
            .annotate(
                total_pecas=Sum('custo_pecas'),
                total_mao_obra=Sum('custo_mao_obra'),
                qtd_manut=Count('id'),
            )
            .order_by('viatura__prefixo')
        )
        manut_dict = {}
        for row in manut_agg:
            key = row['viatura__prefixo']
            manut_dict[key] = {
                'modelo': f"{row['viatura__modelo__marca__nome']} {row['viatura__modelo__nome']}",
                'qtd_manut': row['qtd_manut'],
                'pecas': row['total_pecas'] or Decimal('0'),
                'mao_obra': row['total_mao_obra'] or Decimal('0'),
            }

        # Abastecimentos por viatura
        abast_qs = Abastecimento.objects.all()
        if data_inicio:
            abast_qs = abast_qs.filter(data_abastecimento__date__gte=data_inicio)
        if data_fim:
            abast_qs = abast_qs.filter(data_abastecimento__date__lte=data_fim)

        abast_agg = (
            abast_qs
            .values('viatura__prefixo')
            .annotate(
                total_litros=Sum('quantidade_litros'),
                total_valor=Sum('valor_total'),
                qtd_abast=Count('id'),
            )
        )
        abast_dict = {}
        for row in abast_agg:
            abast_dict[row['viatura__prefixo']] = {
                'qtd_abast': row['qtd_abast'],
                'litros': row['total_litros'] or Decimal('0'),
                'valor': row['total_valor'] or Decimal('0'),
            }

        # Consolidar
        all_prefixos = sorted(set(list(manut_dict.keys()) + list(abast_dict.keys())))
        results = []
        data = []
        grand_total = Decimal('0')

        for prefixo in all_prefixos:
            m = manut_dict.get(prefixo, {})
            a = abast_dict.get(prefixo, {})
            custo_manut = m.get('pecas', Decimal('0')) + m.get('mao_obra', Decimal('0'))
            custo_abast = a.get('valor', Decimal('0'))
            total = custo_manut + custo_abast
            grand_total += total
            data.append([
                prefixo,
                m.get('modelo', '-'),
                str(m.get('qtd_manut', 0)),
                f"R$ {custo_manut:,.2f}",
                str(a.get('qtd_abast', 0)),
                f"{a.get('litros', Decimal('0')):,.1f} L",
                f"R$ {custo_abast:,.2f}",
                f"R$ {total:,.2f}",
            ])

        if data:
            data.append([
                'TOTAL', '', '', '', '', '', '',
                f"R$ {grand_total:,.2f}",
            ])
            periodo_str = ''
            if data_inicio and data_fim:
                periodo_str = f" ({data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')})"
            elif data_inicio:
                periodo_str = f" (a partir de {data_inicio.strftime('%d/%m/%Y')})"

            results.append({
                'title': f"GASTOS POR VIATURA{periodo_str} — Total: R$ {grand_total:,.2f}",
                'columns': ['Prefixo', 'Modelo', 'Manut.', 'Custo Manut.', 'Abast.', 'Litros', 'Custo Abast.', 'Total'],
                'data': data,
                'col_widths': [1.8 * cm, 3.5 * cm, 1.2 * cm, 2.2 * cm, 1.2 * cm, 1.8 * cm, 2.2 * cm, 2.5 * cm],
            })

        # Top 5 mais custosas
        top5 = sorted(data[:-1], key=lambda r: float(r[-1].replace('R$ ', '').replace('.', '').replace(',', '.')), reverse=True)[:5]
        if len(top5) > 1:
            results.append({
                'title': "TOP 5 VIATURAS MAIS CUSTOSAS",
                'columns': ['Prefixo', 'Modelo', 'Manut.', 'Custo Manut.', 'Abast.', 'Litros', 'Custo Abast.', 'Total'],
                'data': top5,
                'col_widths': [1.8 * cm, 3.5 * cm, 1.2 * cm, 2.2 * cm, 1.2 * cm, 1.8 * cm, 2.2 * cm, 2.5 * cm],
            })

        return results
