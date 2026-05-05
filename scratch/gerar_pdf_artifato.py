import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

def parse_markdown_to_elements(file_path, styles):
    elements = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False
    code_content = []
    in_table = False
    table_data = []

    for line in lines:
        stripped = line.strip()
        
        # Code block handling
        if stripped.startswith('```'):
            if in_code_block:
                elements.append(Paragraph("<br/>".join(code_content), styles['CodeStyle']))
                elements.append(Spacer(1, 10))
                code_content = []
                in_code_block = False
            else:
                in_code_block = True
            continue
        
        if in_code_block:
            code_content.append(stripped.replace('<', '&lt;').replace('>', '&gt;'))
            continue

        # Table handling (very basic)
        if stripped.startswith('|') and '|' in stripped[1:]:
            in_table = True
            row = [cell.strip() for cell in stripped.split('|') if cell.strip()]
            if row and not all(c == '-' for c in row[0]): # skip separator line
                table_data.append(row)
            continue
        elif in_table:
            # End of table
            if table_data:
                # Filter out the separator row if it's there
                table_data = [r for r in table_data if not all(set(c) <= {'-', '|', ' ', ':'} for c in r)]
                
                t = Table(table_data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2980b9")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 15))
            table_data = []
            in_table = False

        if not stripped:
            elements.append(Spacer(1, 8))
            continue

        # Headers
        if stripped.startswith('# '):
            elements.append(Paragraph(stripped[2:], styles['TitleStyle']))
            elements.append(Spacer(1, 10))
        elif stripped.startswith('## '):
            elements.append(Paragraph(stripped[3:], styles['Heading2Style']))
            elements.append(Spacer(1, 8))
        elif stripped.startswith('### '):
            elements.append(Paragraph(stripped[4:], styles['Heading3Style']))
            elements.append(Spacer(1, 6))
        # Bullet points
        elif stripped.startswith('- ') or stripped.startswith('* '):
            elements.append(Paragraph(f"• {stripped[2:]}", styles['BodyStyle']))
        # Paragraph
        else:
            elements.append(Paragraph(stripped, styles['BodyStyle']))

    return elements

def generate_pdf():
    input_file = r"C:\Users\2BAEP-32KVB92\.gemini\antigravity\brain\06785f59-5054-482c-b762-d005d9fecc8c\artifacts\arquitetura_licenciamento.md.resolved"
    output_file = "arquitetura_licenciamento_detalhada.pdf"
    
    doc = SimpleDocTemplate(output_file, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor("#2c3e50"), alignment=TA_CENTER, spaceAfter=20)
    h2_style = ParagraphStyle('Heading2Style', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor("#2980b9"), spaceBefore=15, spaceAfter=10)
    h3_style = ParagraphStyle('Heading3Style', parent=styles['Heading3'], fontSize=13, textColor=colors.HexColor("#16a085"), spaceBefore=10, spaceAfter=8)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, alignment=TA_JUSTIFY, leading=12, spaceAfter=6)
    code_style = ParagraphStyle('CodeStyle', parent=styles['Normal'], fontName='Courier', fontSize=8, leftIndent=15, backgroundColor=colors.HexColor("#f4f4f4"), borderPadding=5, leading=10)

    custom_styles = {
        'TitleStyle': title_style,
        'Heading2Style': h2_style,
        'Heading3Style': h3_style,
        'BodyStyle': body_style,
        'CodeStyle': code_style
    }

    elements = parse_markdown_to_elements(input_file, custom_styles)
    
    doc.build(elements)
    print(f"PDF gerado com sucesso: {output_file}")

if __name__ == "__main__":
    generate_pdf()
