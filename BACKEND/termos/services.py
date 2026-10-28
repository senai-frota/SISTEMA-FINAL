import io

from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

ENTIDADES = ['FIBRA', 'SESI', 'SENAI', 'IEL']

CLAUSULAS = [
    "a) promover a adequada utilização e guarda do veículo institucional;",
    "b) comunicar, imediatamente, qualquer incidente e ocorrência com o veículo sob minha "
    "responsabilidade;",
    "c) arcar com as despesas oriundas de possíveis multas, ou danos/avarias causados ao "
    "veículo por motivo de irresponsabilidade, imprudência ou imperícia, autorizando o "
    "desconto em folha de pagamento, de forma integral quando o valor correspondente for "
    "inferior à margem consignável, ou em parcelas, respeitando o limite previsto no § 1º, "
    "artigo 462 da Consolidação das leis do Trabalho – CLT.",
]

PARAGRAFO_1 = (
    "Pelo presente Termo de Responsabilidade, considerando a autorização que me foi "
    "concedida para conduzir os veículos institucionais das entidades que compõem o "
    "Sistema Fibra, declaro ciência das disposições determinadas pelas leis de trânsito "
    "brasileiras, da responsabilidade civil, penal e administrativa, pelo uso e guarda do "
    "veículo."
)

PARAGRAFO_2 = (
    "Declaro ainda ter recebido as orientações acerca do normativo ING-APOIO-001 – "
    "UTILIZAÇÃO DE VEÍCULOS EM SERVIÇO, que dispõe sobre os regulamentos para a "
    "utilização do veículo institucional, bem como de minhas responsabilidades como "
    "empregado condutor, tais como:"
)


def _wrap_text(c, text, font, size, max_width):
    c.setFont(font, size)
    words = text.split(' ')
    lines = []
    current = ''
    for word in words:
        candidate = f"{current} {word}".strip()
        if c.stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def gerar_pdf_termo(termo):
    """Gera o PDF do Termo de Responsabilidade preenchido com os dados do usuário
    e da solicitação, deixando em branco apenas as assinaturas (preenchidas fora
    do sistema / aceitas pelo administrador)."""
    usuario = termo.usuario

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    y = height - margin

    # Cabeçalho
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(width / 2, y, 'FIBRA | SESI | SENAI | IEL')
    y -= 16

    c.setFont('Helvetica-Bold', 13)
    for line in [
        'TERMO DE RESPONSABILIDADE PARA',
        'UTILIZAÇÃO DE VEÍCULO A SERVIÇO',
    ]:
        c.drawCentredString(width / 2, y, line)
        y -= 16
    y -= 6

    # Entidade (checkboxes) + Data da solicitação
    c.setFont('Helvetica-Bold', 10)
    c.drawString(margin, y, 'Entidade:')
    x = margin + 45
    c.setFont('Helvetica', 10)
    box = 9
    for nome in ENTIDADES:
        marcado = nome == termo.entidade
        c.rect(x, y - 2, box, box, stroke=1, fill=1 if marcado else 0)
        if marcado:
            c.setFillColorRGB(1, 1, 1)
            c.setFont('Helvetica-Bold', 8)
            c.drawCentredString(x + box / 2, y - 0.5, 'X')
            c.setFillColorRGB(0, 0, 0)
            c.setFont('Helvetica', 10)
        c.drawString(x + box + 3, y, nome)
        x += box + 3 + c.stringWidth(nome, 'Helvetica', 10) + 14

    data_sol = termo.data_solicitacao.strftime('%d/%m/%Y')
    c.setFont('Helvetica-Bold', 10)
    c.drawRightString(width - margin, y, f'Data da Solicitação: {data_sol}')
    y -= 22

    # Linha separadora
    c.setLineWidth(0.5)
    c.line(margin, y, width - margin, y)
    y -= 18

    # Dados do empregado
    max_width = width - 2 * margin

    nome_label = 'Nome do Empregado: '
    nome_label_width = c.stringWidth(nome_label, 'Helvetica-Bold', 10)
    if c.stringWidth(nome_label + usuario.nome, 'Helvetica-Bold', 10) <= max_width:
        c.setFont('Helvetica-Bold', 10)
        c.drawString(margin, y, f'{nome_label}{usuario.nome}')
        y -= 16
    else:
        # Nome muito longo para caber em uma linha: quebra o texto para não
        # vazar para fora da página.
        c.setFont('Helvetica-Bold', 10)
        c.drawString(margin, y, nome_label)
        nome_lines = _wrap_text(
            c, usuario.nome, 'Helvetica-Bold', 10, max_width - nome_label_width
        )
        c.setFont('Helvetica-Bold', 10)
        c.drawString(margin + nome_label_width, y, nome_lines[0] if nome_lines else '')
        y -= 16
        for line in nome_lines[1:]:
            c.drawString(margin, y, line)
            y -= 16

    linha = f'Matrícula: {usuario.matricula}     CPF: {termo.cpf}     CNH: {termo.cnh}'
    c.drawString(margin, y, linha)
    y -= 24

    # Título da seção
    c.setFont('Helvetica-Bold', 11)
    c.drawString(margin, y, 'Termo de Responsabilidade')
    y -= 18

    max_width = width - 2 * margin
    c.setFont('Helvetica', 10)

    for paragrafo in [PARAGRAFO_1, PARAGRAFO_2]:
        for line in _wrap_text(c, paragrafo, 'Helvetica', 10, max_width):
            c.drawString(margin, y, line)
            y -= 13
        y -= 6

    for clausula in CLAUSULAS:
        for i, line in enumerate(_wrap_text(c, clausula, 'Helvetica', 10, max_width - 12)):
            c.drawString(margin + 12, y, line)
            y -= 13
        y -= 4

    y -= 16
    data_assinatura = data_sol
    c.setFont('Helvetica-Bold', 10)
    c.drawString(margin, y, f'Data: {data_assinatura}')
    y -= 40

    # Assinaturas (em branco - preenchidas/validadas pela chefia/admin)
    linha_y = y
    c.setLineWidth(0.5)
    c.line(margin, linha_y, margin + 200, linha_y)
    c.line(width - margin - 200, linha_y, width - margin, linha_y)
    c.setFont('Helvetica', 9)
    c.drawCentredString(margin + 100, linha_y - 12, 'Assinatura do Empregado')
    c.drawCentredString(width - margin - 100, linha_y - 12, 'Assinatura da Chefia Imediata')

    # Rodapé
    c.setFont('Helvetica', 7)
    c.drawString(
        margin, margin / 2,
        'Formulário 01 ING - SESI/SENAI 007 - UTILIZAÇÃO DE VEÍCULOS E TRANSPORTE DE '
        'PASSAGEIROS EM SERVIÇO   Revisão 0'
    )

    c.showPage()
    c.save()
    buffer.seek(0)

    nome_arquivo = f'termo_{usuario.matricula}_{termo.data_solicitacao.isoformat()}.pdf'
    return ContentFile(buffer.read(), name=nome_arquivo)
