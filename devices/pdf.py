import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from arabic_reshaper import reshape
from bidi.algorithm import get_display

BASE_DIR = Path(__file__).resolve().parent.parent


def fix_ar(text):
    """Shape Arabic and apply RTL display order for ReportLab."""
    if text is None:
        return ''
    return get_display(reshape(str(text)))


def register_font():
    """Register a font with reliable Arabic coverage for Linux and Windows."""
    candidates = [
        BASE_DIR / 'static' / 'fonts' / 'NotoSansArabic-Regular.ttf',
        Path('C:/Windows/Fonts/arial.ttf'),
        Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'),
    ]

    for path in candidates:
        if path.exists():
            try:
                font_name = 'SIACArabic'
                if font_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(font_name, str(path)))
                return font_name
            except Exception:
                continue

    raise RuntimeError(
        'Arabic PDF font was not found. Noto Sans Arabic should be downloaded during the build.'
    )


def build_pdf(device):
    font = register_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=25,
    )

    right = ParagraphStyle(
        'right', fontName=font, fontSize=10, alignment=2, leading=13
    )
    center = ParagraphStyle(
        'center', fontName=font, fontSize=16, alignment=1, spaceAfter=8
    )
    heading = ParagraphStyle(
        'heading', fontName=font, fontSize=10, alignment=2, spaceAfter=2
    )

    def para(text, style=right):
        return Paragraph(fix_ar('' if text is None else text), style)

    story = [
        para('الشركة الهندسية للصناعات والتشييد (سياك)'),
        para('إدارة الحاسب الآلي ونظم المعلومات'),
        Spacer(1, 4),
        para('إجراءات فحص جهاز', center),
    ]

    fields = [
        [
            para(f'User Name : {device.user_name}'),
            para(f'Project : {device.project}'),
        ],
        [
            para(f'Serial Number : {device.serial_number}'),
            para(f'Model : {device.model}'),
        ],
        [
            para(''),
            para(f'Pc Name : {device.computer_name}'),
        ],
    ]

    t = Table(fields, colWidths=[270, 270])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story += [t, Spacer(1, 8), para('إجراءات فحص جهاز:', heading)]
    story += [Spacer(1, 3), para('HDD :', heading)]

    box = Table(
        [[para(device.hdd)], [para('')]],
        colWidths=[540],
        rowHeights=[20, 20],
    )
    box.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story += [box, Spacer(1, 5)]

    ram_proc = [
        [
            para(f'RAM : [ {device.ram} ]', heading),
            para(f'processor : [ {device.processor} ]'),
        ]
    ] + [
        [para(''), para('')]
        for _ in range(3)
    ]

    box2 = Table(ram_proc, colWidths=[270, 270], rowHeights=[20, 20, 20, 20])
    box2.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story += [box2, Spacer(1, 5)]

    for title in [
        '-3 نتيجة فحص Battery :',
        '-4 نتيجة فحص الهيكل الخارجي والشكل العام :',
        '-5 نوع وسريال الشاشة :',
        '-6 نوع وسريال الطابعه :',
        '-7 ملاحظات:',
    ]:
        story += [para(title, heading)]
        b = Table(
            [[para('')], [para('')]],
            colWidths=[540],
            rowHeights=[20, 20],
        )
        b.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story += [b, Spacer(1, 5)]

    footer = [
        [
            para('اسم مسئول الدعم الفنى : ......................................'),
            para('تاريخ التقرير : ................................................'),
        ],
        [
            para(''),
            para('توقيع المستخدم : ......................................'),
        ],
    ]
    ft = Table(footer, colWidths=[270, 270])
    ft.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(ft)

    doc.build(story)
    buf.seek(0)
    return buf
