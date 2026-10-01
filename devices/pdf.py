import html
import io
import os
import re
from pathlib import Path

from arabic_reshaper import reshape
from bidi.algorithm import get_display
from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).resolve().parent.parent
ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')


def clean_text(value):
    if value is None:
        return ''
    return str(value).replace('\\r\\n', '\n').replace('\\r', '\n').replace('\r\n', '\n').replace('\r', '\n')


def has_arabic(text):
    return bool(ARABIC_RE.search(text))


def register_fonts():
    """Register an Arabic Unicode font while keeping Helvetica for English/Latin."""
    arabic_candidates = [
        BASE_DIR / 'static' / 'fonts' / 'NotoSansArabic-Regular.ttf',
        Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'),
        Path('C:/Windows/Fonts/arial.ttf'),
    ]

    for path in arabic_candidates:
        if path.exists():
            try:
                if 'SIACArabic' not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont('SIACArabic', str(path)))
                return 'SIACArabic'
            except Exception:
                continue

    raise RuntimeError('Arabic PDF font was not found. Run build.sh so NotoSansArabic is downloaded.')


def escape_pdf_text(value):
    return html.escape(clean_text(value), quote=False).replace('\n', '<br/>')


def rtl_arabic(value):
    """Shape and reorder Arabic-only text for ReportLab."""
    text = clean_text(value)
    if not text:
        return ''
    return get_display(reshape(text), base_dir='R')


def mixed_markup(value, arabic_font='SIACArabic', latin_font='Helvetica'):
    """
    Preserve both Arabic and English/numbers in the same value.
    Arabic runs are reshaped/reordered; Latin runs are left untouched and
    explicitly assigned to Helvetica so they cannot disappear from the PDF.
    """
    text = clean_text(value)
    if not text:
        return ''

    parts = []
    current = []
    current_is_ar = None

    def flush(is_ar, chars):
        if not chars:
            return
        run = ''.join(chars)
        if is_ar:
            run = get_display(reshape(run), base_dir='R')
            font = arabic_font
        else:
            font = latin_font
        run = html.escape(run, quote=False).replace('\n', '<br/>')
        parts.append(f'<font name="{font}">{run}</font>')

    for ch in text:
        is_ar = bool(ARABIC_RE.match(ch))
        if current_is_ar is None:
            current_is_ar = is_ar
        elif is_ar != current_is_ar:
            flush(current_is_ar, current)
            current = []
            current_is_ar = is_ar
        current.append(ch)

    flush(current_is_ar, current)
    return ''.join(parts)


def p_mixed(value, style):
    return Paragraph(mixed_markup(value) or ' ', style)


def p_ar(value, style):
    text = clean_text(value)
    return Paragraph(html.escape(rtl_arabic(text), quote=False).replace('\n', '<br/>') or ' ', style)


def p_en(value, style):
    text = escape_pdf_text(value)
    return Paragraph(text or ' ', style)


def build_pdf(device):
    arabic_font = register_fonts()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=25,
    )

    right_ar = ParagraphStyle(
        'right_ar', fontName=arabic_font, fontSize=10, alignment=2, leading=13,
    )
    center_ar = ParagraphStyle(
        'center_ar', fontName=arabic_font, fontSize=16, alignment=1,
        spaceAfter=8, leading=20,
    )
    heading_ar = ParagraphStyle(
        'heading_ar', fontName=arabic_font, fontSize=10, alignment=2,
        spaceAfter=2, leading=13,
    )
    label_en = ParagraphStyle(
        'label_en', fontName='Helvetica', fontSize=9, alignment=2, leading=12,
    )
    value_mixed = ParagraphStyle(
        'value_mixed', fontName='Helvetica', fontSize=10, alignment=2, leading=13,
    )
    small_mixed = ParagraphStyle(
        'small_mixed', fontName='Helvetica', fontSize=9, alignment=2, leading=12,
    )

    story = [
        p_ar('الشركة الهندسية للصناعات والتشييد (سياك)', right_ar),
        p_ar('إدارة الحاسب الآلي ونظم المعلومات', right_ar),
        Spacer(1, 4),
        p_ar('إجراءات فحص جهاز', center_ar),
    ]

    # Labels are English/Latin and values are mixed-safe. This prevents an
    # Arabic-only font from swallowing English text.
    fields = [
        [
            p_en('User Name :', label_en),
            p_mixed(getattr(device, 'user_name', ''), value_mixed),
            p_en('Project :', label_en),
            p_mixed(getattr(device, 'project', ''), value_mixed),
        ],
        [
            p_en('Serial Number :', label_en),
            p_mixed(getattr(device, 'serial_number', ''), value_mixed),
            p_en('Model :', label_en),
            p_mixed(getattr(device, 'model', ''), value_mixed),
        ],
        [
            p_en('', label_en),
            p_en('', value_mixed),
            p_en('Pc Name :', label_en),
            p_mixed(getattr(device, 'computer_name', ''), value_mixed),
        ],
    ]

    fields_table = Table(fields, colWidths=[78, 192, 68, 202], hAlign='RIGHT')
    fields_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story += [fields_table, Spacer(1, 8), p_ar('إجراءات فحص جهاز:', heading_ar)]

    # English-only technical labels use Helvetica explicitly.
    story += [Spacer(1, 3), p_en('HDD :', label_en)]
    hdd_box = Table(
        [[p_mixed(getattr(device, 'hdd', ''), value_mixed)], [p_en('', value_mixed)]],
        colWidths=[540],
        rowHeights=[20, 20],
    )
    hdd_box.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story += [hdd_box, Spacer(1, 5)]

    ram_cell = p_mixed(f'RAM : [ {getattr(device, "ram", "")} ]', small_mixed)
    processor_cell = p_mixed(
        f'processor : [ {getattr(device, "processor", "")} ]',
        value_mixed,
    )
    ram_proc = [[ram_cell, processor_cell]] + [
        [p_en('', value_mixed), p_en('', value_mixed)] for _ in range(3)
    ]

    box2 = Table(ram_proc, colWidths=[270, 270], rowHeights=[20, 20, 20, 20])
    box2.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story += [box2, Spacer(1, 5)]

    section_titles = [
        '-3 نتيجة فحص Battery :',
        '-4 نتيجة فحص الهيكل الخارجي والشكل العام :',
        '-5 نوع وسريال الشاشة :',
        '-6 نوع وسريال الطابعه :',
        '-7 ملاحظات:',
    ]
    for title in section_titles:
        story += [p_mixed(title, heading_ar)]
        b = Table(
            [[p_en('', value_mixed)], [p_en('', value_mixed)]],
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
            p_ar('اسم مسئول الدعم الفنى : ......................................', right_ar),
            p_ar('تاريخ التقرير : ................................................', right_ar),
        ],
        [
            p_en('', value_mixed),
            p_ar('توقيع المستخدم : ......................................', right_ar),
        ],
    ]
    footer_table = Table(footer, colWidths=[270, 270])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(footer_table)

    doc.build(story)
    buf.seek(0)
    return buf
