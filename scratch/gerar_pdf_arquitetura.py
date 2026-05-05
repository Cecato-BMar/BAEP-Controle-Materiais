from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

def generate_pdf():
    file_path = "documentacao_arquitetura_licenciamento.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#2c3e50"),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor("#2980b9"),
        spaceBefore=20,
        spaceAfter=10
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor("#16a085"),
        spaceBefore=15,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        leading=14,
        spaceAfter=10
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=9,
        leftIndent=20,
        backgroundColor=colors.HexColor("#f0f0f0"),
        borderPadding=5
    )

    elements = []

    # Title
    elements.append(Paragraph("Detalhamento da Arquitetura de Licenciamento", title_style))
    elements.append(Paragraph("Sistema de Controle de Materiais - 2º BAEP", ParagraphStyle('Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, textColor=colors.grey)))
    elements.append(Spacer(1, 30))

    # 1. Introdução
    elements.append(Paragraph("1. Introdução e Objetivo", subtitle_style))
    elements.append(Paragraph(
        "Este documento detalha a implementação do sistema de licenciamento e controle remoto "
        "desenvolvido para o Sistema de Logística do 2º BAEP. O objetivo principal é garantir que o "
        "desenvolvedor mantenha o controle sobre a execução do software, permitindo o bloqueio "
        "remoto em caso de descumprimento de obrigações contratuais ou expiração de assinaturas SaaS.",
        body_style
    ))

    # 2. Estratégia Técnica
    elements.append(Paragraph("2. Estratégia Técnica: RSA Signed Tokens", subtitle_style))
    elements.append(Paragraph(
        "A arquitetura utiliza Criptografia Assimétrica (RSA de 2048 bits) para garantir a integridade "
        "e a autenticidade das licenças. Diferente de sistemas baseados em chaves simples ou verificações "
        "por internet (que podem falhar em redes internas policiais), esta solução é autossuficiente e "
        "matematicamente impossível de ser burlada sem a chave privada.",
        body_style
    ))

    data = [
        ["Componente", "Responsabilidade"],
        ["Chave Privada", "Mantida exclusivamente pelo desenvolvedor. Usada para assinar tokens."],
        ["Chave Pública", "Embutida no código-fonte do sistema. Usada para validar os tokens."],
        ["Token (JWT)", "Contém metadados: ID do cliente, data de emissão e data de expiração."]
    ]
    t = Table(data, colWidths=[120, 330])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2980b9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f9f9f9")),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # 3. Componentes da Implementação
    elements.append(Paragraph("3. Componentes da Implementação", subtitle_style))
    
    elements.append(Paragraph("3.1 LicenseRecord (Model)", section_style))
    elements.append(Paragraph(
        "Armazena as licenças ativadas no banco de dados SQLite, permitindo auditoria e controle de histórico.",
        body_style
    ))

    elements.append(Paragraph("3.2 LicenseCheckMiddleware", section_style))
    elements.append(Paragraph(
        "O 'coração' do controle. Este middleware intercepta cada requisição HTTP feita ao servidor. "
        "Se a licença for considerada inválida ou estiver expirada além do limite, o usuário é "
        "redirecionado para uma página de bloqueio global.",
        body_style
    ))

    elements.append(Paragraph("4. Proteções Anti-Tampering", subtitle_style))
    elements.append(Paragraph(
        "O sistema inclui proteções contra tentativas comuns de burlar o licenciamento:",
        body_style
    ))
    bullet_points = [
        "<b>Assinatura Digital:</b> Qualquer alteração no texto do token invalida a assinatura RSA.",
        "<b>Anti-Clock Tampering:</b> O sistema armazena a última data de verificação. Se o relógio do servidor for atrasado, o sistema detecta a anomalia.",
        "<b>Grace Period (Tolerância):</b> Oferece um período de 3 dias de funcionamento após a expiração com alertas constantes, evitando interrupções acidentais.",
        "<b>Bloqueio de Middleware:</b> A remoção do middleware desativa funções críticas do sistema."
    ]
    for bp in bullet_points:
        elements.append(Paragraph(f"• {bp}", body_style))

    elements.append(PageBreak())

    # 5. Fluxo de Operação
    elements.append(Paragraph("5. Fluxo de Operação e Gestão", subtitle_style))
    
    elements.append(Paragraph("5.1 Geração de Licença", section_style))
    elements.append(Paragraph(
        "Comando executado pelo desenvolvedor para emitir novos tokens:",
        body_style
    ))
    elements.append(Paragraph("python manage.py gerar_licenca --client_id 'baep' --days 30", code_style))

    elements.append(Paragraph("5.2 Ativação de Licença", section_style))
    elements.append(Paragraph(
        "Pode ser feita via terminal ou pela interface administrativa secreta:",
        body_style
    ))
    elements.append(Paragraph("python manage.py ativar_licenca 'TOKEN_BASE64_AQUI'", code_style))

    # 6. Conclusão
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("6. Conclusão", subtitle_style))
    elements.append(Paragraph(
        "Esta arquitetura fornece o equilíbrio ideal entre segurança e usabilidade. Ao utilizar "
        "padrões de mercado (RSA e JWT), o desenvolvedor garante que o sistema só operará sob sua "
        "autorização explícita, protegendo sua propriedade intelectual e garantindo o cumprimento "
        "do modelo de negócio SaaS.",
        body_style
    ))

    # Footer note
    elements.append(Spacer(1, 100))
    elements.append(Paragraph("Documento gerado automaticamente pelo Sistema de Inteligência - Antigravity", ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=colors.grey)))

    doc.build(elements)
    print(f"PDF gerado com sucesso em: {file_path}")

if __name__ == "__main__":
    generate_pdf()
