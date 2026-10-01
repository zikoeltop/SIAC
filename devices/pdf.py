import html
import io
import re
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
ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')


def clean_text(value):
    if value is None:
        return ''
    return str(value).replace('\r\n', '\n').replace('\r', '\n')


def has_arabic(text):
    return bool(ARABIC_RE.search(text))


def visual_text(value):
    """Return text safe for ReportLab, preserving Arabic and Latin/number content.

    Pure LTR content is left untouched. Text containing Arabic is reshaped and
    passed through the bidi algorithm. HTML/XML characters are escaped only
    after bidi processing so ReportLab's Paragraph parser cannot eat data such
    as '&', '<', or '>'.
    """
    text = clean_text(value)
    if not text:
        return ''

    if has_arabic(text):
        text = get_display(reshape(text), base_dir='R')

    return html.escape(text, quote=False).replace('\n', '<br/>')


def labeled_value(label, value):
    """Keep an English/LTR label intact while rendering the value safely."""
    return f'{html.escape(clean_text(label), quote=False)} {visual_text(value)}'


def register_font():
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
        return Paragraph(visual_text(text), style)

    story = [
        para('الشركة الهندسية للصناعات والتشييد (سياك)'),
        para('إدارة الحاسب الآلي ونظم المعلومات'),
        Spacer(1, 4),
        para('إجراءات فحص جهاز', center),
    ]

    # Keep bilingual labels readable while preserving the exact stored value.
    fields = [
        [
            Paragraph(labeled_value('User Name :', device.user_name), right),
            Paragraph(labeled_value('Project :', device.project), right),
        ],
        [
            Paragraph(labeled_value('Serial Number :', device.serial_number), right),
            Paragraph(labeled_value('Model :', device.model), right),
        ],
        [
            Paragraph('', right),
            Paragraph(labeled_value('Pc Name :', device.computer_name), right),
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
            Paragraph(labeled_value('RAM : [', f'{device.ram} ]'), heading),
            Paragraph(labeled_value('processor : [', f'{device.processor} ]'), right),
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
