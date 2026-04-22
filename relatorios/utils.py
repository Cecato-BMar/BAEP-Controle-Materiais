from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.utils import ImageReader
from django.conf import settings
from django.contrib.staticfiles import finders
from django.utils import timezone
import io
import os

class PDFReportGenerator:
    def __init__(self, buffer, title, user=None):
        self.buffer = buffer
        self.title = title
        self.user = user
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        self.doc = SimpleDocTemplate(
            self.buffer, 
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2*cm
        )

    def _setup_styles(self):
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.black,
            alignment=1,
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.black,
            borderPadding=5,
            spaceBefore=15,
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='NormalCenter',
            parent=self.styles['Normal'],
            alignment=1,
            fontSize=9
        ))
        self.styles.add(ParagraphStyle(
            name='Small',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        ))

    def _draw_header(self, canvas, doc):
        canvas.saveState()
        
        # Logo
        logo_path = finders.find('img/logo_baep.png')
        if logo_path and os.path.exists(logo_path):
            img = ImageReader(logo_path)
            canvas.drawImage(img, doc.leftMargin, doc.pagesize[1] - 2*cm, width=1.5*cm, height=1.5*cm, mask='auto')
        
        # Cabeçalho Texto
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawCentredString(doc.pagesize[0]/2, doc.pagesize[1] - 1.2*cm, "POLÍCIA MILITAR DO ESTADO DE SÃO PAULO")
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(doc.pagesize[0]/2, doc.pagesize[1] - 1.7*cm, "2º BATALHÃO DE AÇÕES ESPECIAIS DE POLÍCIA - 2º BAEP")
        
        # Linha divisória (Preta para máximo contraste em P&B)
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(1.5)
        canvas.line(doc.leftMargin, doc.pagesize[1] - 2.2*cm, doc.pagesize[0] - doc.rightMargin, doc.pagesize[1] - 2.2*cm)
        
        canvas.restoreState()

    def _draw_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setStrokeColor(colors.lightgrey)
        canvas.line(doc.leftMargin, 1.5*cm, doc.pagesize[0] - doc.rightMargin, 1.5*cm)
        
        # Data e Usuário
        data_geracao = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')
        usuario = self.user.get_full_name() if self.user and self.user.get_full_name() else (self.user.username if self.user else "Sistema")
        
        canvas.drawString(doc.leftMargin, 1.1*cm, f"Gerado em: {data_geracao} | Por: {usuario}")
        
        # Paginação
        page_num = canvas.getPageNumber()
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 1.1*cm, f"Página {page_num}")
        
        canvas.restoreState()

    def create_table(self, data, col_widths=None, style_type='NORMAL'):
        # Converte dados para Paragraph para permitir quebra de linha automática
        processed_data = []
        for row in data:
            processed_row = []
            for cell in row:
                if isinstance(cell, str):
                    # Usa estilo centralizado para o corpo da tabela
                    style = self.styles['NormalCenter']
                    processed_row.append(Paragraph(cell, style))
                else:
                    processed_row.append(cell)
            processed_data.append(processed_row)

        if not col_widths:
            # Distribuição automática se não fornecida
            col_widths = [(self.doc.width / len(data[0]))] * len(data[0])
            
        table = Table(processed_data, colWidths=col_widths, repeatRows=1)
        
        if style_type == 'NORMAL':
            style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')), # Cinza claro
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]
        elif style_type == 'DANGER':
            style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c0392b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]
        
        table.setStyle(TableStyle(style))
        return table

    def generate(self, elements):
        # Adicionar Título Principal no início se fornecido
        if self.title:
            elements.insert(0, Paragraph(self.title.upper(), self.styles['ReportTitle']))
            elements.insert(1, Spacer(1, 10))

        self.doc.build(
            elements, 
            onFirstPage=self._on_page, 
            onLaterPages=self._on_page
        )

    def _on_page(self, canvas, doc):
        self._draw_header(canvas, doc)
        self._draw_footer(canvas, doc)
