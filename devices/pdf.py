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
    return str(value).replace('\\r\\n', '\\n').replace('\\r', '\\n')


def has_arabic(text):
    return bool(ARABIC_RE.search(text))


def visual_text(value):
    """Prepare text for ReportLab while preserving Arabic + English/numbers."""
    text = clean_text(value)
    if not text:
        return ''
    if has_arabic(text):
        # Bidi is applied only to the value itself. English labels are kept
        # outside this function so mixed rows cannot swallow or reorder them.
        text = get_display(reshape(text), base_dir='R')
    return html.escape(text, quote=False).replace('\\n', '<br/>')


def register_font():
    candidates = [
        BASE_DIR / 'static' / 'fonts' / 'NotoSansArabic-Regular.ttf',
        Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'),
        Path('C:/Windows/Fonts/arial.ttf'),
    ]
    for path in candidates:
        if path.exists():
            try:
                if 'SIACArabic' not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont('SIACArabic', str(path)))
                return 'SIACArabic'
            except Exception:
                continue
    raise RuntimeError('Arabic PDF font was not found.')


def _paragraph(value, style):
    return Paragraph(visual_text(value), style)


def _field_block(label, value, font, value_size=10):
    """Return a self-contained label/value block so every field is always rendered."""
    label_style = ParagraphStyle(
        f'label_{label}', fontName=font, fontSize=value_size, leading=value_size + 3,
        alignment=2, spaceAfter=1,
    )
    value_style = ParagraphStyle(
        f'value_{label}', fontName=font, fontSize=value_size, leading=value_size + 3,
        alignment=2,
    )
    return [
        Paragraph(html.escape(label, quote=False), label_style),
        Paragraph(visual_text(value) if clean_text(value) else ' ', value_style),
    ]


def build_pdf(device):
    font = register_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25,
    )

    right = ParagraphStyle('right', fontName=font, fontSize=10, alignment=2, leading=13)
    center = ParagraphStyle('center', fontName=font, fontSize=16, alignment=1, spaceAfter=8, leading=20)
    heading = ParagraphStyle('heading', fontName=font, fontSize=10, alignment=2, spaceAfter=2, leading=13)
    field_label = ParagraphStyle('field_label', fontName=font, fontSize=9, alignment=2, leading=12)
    field_value = ParagraphStyle('field_value', fontName=font, fontSize=10, alignment=2, leading=13)

    story = [
        _paragraph('الشركة الهندسية للصناعات والتشييد (سياك)', right),
        _paragraph('إدارة الحاسب الآلي ونظم المعلومات', right),
        Spacer(1, 4),
        _paragraph('إجراءات فحص جهاز', center),
    ]

    # Explicit 4-column layout: English label is isolated from the value.
    # This prevents bidi processing of a mixed Arabic/English string from
    # hiding labels or values.
    fields = [
        [
            Paragraph('User Name :', field_label),
            Paragraph(visual_text(device.user_name) or ' ', field_value),
            Paragraph('Project :', field_label),
            Paragraph(visual_text(device.project) or ' ', field_value),
        ],
        [
            Paragraph('Serial Number :', field_label),
            Paragraph(visual_text(device.serial_number) or ' ', field_value),
            Paragraph('Model :', field_label),
            Paragraph(visual_text(device.model) or ' ', field_value),
        ],
        [
            Paragraph('', field_label),
            Paragraph('', field_value),
            Paragraph('Pc Name :', field_label),
            Paragraph(visual_text(device.computer_name) or ' ', field_value),
        ],
    ]

    t = Table(fields, colWidths=[78, 192, 68, 202], hAlign='RIGHT')
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story += [t, Spacer(1, 8), _paragraph('إجراءات فحص جهاز:', heading)]
    story += [Spacer(1, 3), _paragraph('HDD :', heading)]

    box = Table(
        [[_paragraph(device.hdd, right)], [_paragraph('', right)]],
        colWidths=[540], rowHeights=[20, 20],
    )
    box.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story += [box, Spacer(1, 5)]

    ram_proc = [
        [
            _paragraph(f'RAM : [ {device.ram} ]', heading),
            _paragraph(f'processor : [ {device.processor} ]', right),
        ]
    ] + [[_paragraph('', right), _paragraph('', right)] for _ in range(3)]

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
        story += [_paragraph(title, heading)]
        b = Table(
            [[_paragraph('', right)], [_paragraph('', right)]],
            colWidths=[540], rowHeights=[20, 20],
        )
        b.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story += [b, Spacer(1, 5)]

    footer = [
        [
            _paragraph('اسم مسئول الدعم الفنى : ......................................', right),
            _paragraph('تاريخ التقرير : ................................................', right),
        ],
        [
            _paragraph('', right),
            _paragraph('توقيع المستخدم : ......................................', right),
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
