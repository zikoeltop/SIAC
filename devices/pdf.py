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

# --- Employee custody report (generated from database records imported from Custody Lookup sources) ---
def build_custody_pdf(employee, assets, hr_code=None):
    """Create the professional multi-page employee custody report with the SIAC logo."""
    from datetime import date
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Flowable
    from .models import Asset

    arabic_font = register_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=92, bottomMargin=30,
        title='SIAC Employee Custody Report', author='SIAC IT',
    )
    label_ar = ParagraphStyle('custody_label_ar', fontName=arabic_font, fontSize=8.5, leading=11, alignment=2, textColor=colors.HexColor('#526174'))
    value_mix = ParagraphStyle('custody_value_mix', fontName='Helvetica', fontSize=8.7, leading=11.5, alignment=2, textColor=colors.HexColor('#17233B'))
    title_ar = ParagraphStyle('custody_title_ar', fontName=arabic_font, fontSize=17, leading=22, alignment=1, textColor=colors.HexColor('#17365D'), spaceAfter=3)
    subtitle_en = ParagraphStyle('custody_subtitle_en', fontName='Helvetica-Bold', fontSize=9, leading=12, alignment=1, textColor=colors.HexColor('#1F8A8A'), spaceAfter=10)
    section_ar = ParagraphStyle('custody_section_ar', fontName=arabic_font, fontSize=10, leading=14, alignment=2, textColor=colors.HexColor('#17365D'), spaceBefore=6, spaceAfter=5)
    table_head = ParagraphStyle('custody_table_head', fontName=arabic_font, fontSize=8, leading=10, alignment=1, textColor=colors.white)
    table_en_head = ParagraphStyle('custody_table_en_head', fontName='Helvetica-Bold', fontSize=7.5, leading=9, alignment=1, textColor=colors.white)
    table_cell = ParagraphStyle('custody_table_cell', fontName='Helvetica', fontSize=7.3, leading=9, alignment=2, textColor=colors.HexColor('#18273A'))
    table_cell_ar = ParagraphStyle('custody_table_cell_ar', fontName=arabic_font, fontSize=7.3, leading=9, alignment=2, textColor=colors.HexColor('#18273A'))
    small_ar = ParagraphStyle('custody_small_ar', fontName=arabic_font, fontSize=8.2, leading=11, alignment=2, textColor=colors.HexColor('#27364B'))

    def draw_header(canvas, document):
        canvas.saveState()
        page_width, page_height = A4
        logo_path = BASE_DIR / 'static' / 'img' / 'siac_logo.png'
        if logo_path.exists():
            try:
                canvas.drawImage(str(logo_path), 27, page_height - 78, width=83, height=67, preserveAspectRatio=True, mask='auto', anchor='c')
            except Exception:
                pass
        company = rtl_arabic('الشركة الهندسية للصناعات والتشييد (سياك)')
        department = rtl_arabic('إدارة الحاسب الآلي ونظم المعلومات')
        canvas.setFont(arabic_font, 11)
        canvas.setFillColor(colors.HexColor('#17365D'))
        canvas.drawRightString(page_width - 28, page_height - 40, company)
        canvas.setFont(arabic_font, 9)
        canvas.setFillColor(colors.HexColor('#344B68'))
        canvas.drawRightString(page_width - 28, page_height - 57, department)
        canvas.setStrokeColor(colors.HexColor('#1F8A8A'))
        canvas.setLineWidth(1.2)
        canvas.line(27, page_height - 84, page_width - 27, page_height - 84)
        canvas.restoreState()

    asset_rows = list(assets)
    employee_name = ''
    if employee:
        employee_name = getattr(employee, 'name', '') or getattr(employee, 'employee_name', '')
        hr_code = getattr(employee, 'hr_code', '') or hr_code
    elif asset_rows:
        employee_name = next((a.display_employee_name for a in asset_rows if a.display_employee_name and a.display_employee_name != '-'), '')
    employee_name = employee_name or 'Employee record not found'
    hr_code = str(hr_code or '')

    counts = {
        'computer': sum(1 for a in asset_rows if a.asset_type == 'computer'),
        'printer': sum(1 for a in asset_rows if a.asset_type == 'printer'),
        'monitor': sum(1 for a in asset_rows if a.asset_type == 'monitor'),
        'gstar_license': sum(1 for a in asset_rows if a.asset_type == 'gstar_license'),
        'new_2026': sum(1 for a in asset_rows if a.asset_type == 'new_2026'),
        'request_2025': sum(1 for a in asset_rows if a.asset_type == 'request_2025'),
    }
    total_assets = len(asset_rows)

    story = [
        p_ar('بيان عهدة الموظف', title_ar),
        p_en('EMPLOYEE CUSTODY REPORT', subtitle_en),
    ]

    def employee_value(attribute, asset_attribute=None):
        value = getattr(employee, attribute, '') if employee else ''
        if not value and asset_attribute and asset_rows:
            value = getattr(asset_rows[0], asset_attribute, '')
        return value or '-'

    employee_fields = [
        [p_ar('كود الموظف', label_ar), p_mixed(hr_code or '-', value_mix), p_ar('اسم الموظف', label_ar), p_mixed(employee_name, value_mix)],
        [p_ar('المشروع / الموقع', label_ar), p_mixed(employee_value('project', 'project'), value_mix), p_ar('القطاع', label_ar), p_mixed(employee_value('sector', 'sector'), value_mix)],
        [p_ar('الإدارة', label_ar), p_mixed(employee_value('department', 'department'), value_mix), p_ar('الوظيفة', label_ar), p_mixed(employee_value('position'), value_mix)],
        [p_ar('الشركة', label_ar), p_mixed(employee_value('company', 'company'), value_mix), p_ar('حالة الموظف', label_ar), p_mixed(employee_value('employment_status'), value_mix)],
    ]
    profile = Table(employee_fields, colWidths=[70, 192, 70, 208], hAlign='RIGHT')
    profile.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F5FA')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F0F5FA')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#CAD5E2')),
        ('INNERGRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#DAE2EC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story += [profile, Spacer(1, 8), p_ar('ملخص العهدة', section_ar)]

    summary_labels = [
        ('إجمالي الأصول', total_assets), ('أجهزة الكمبيوتر', counts['computer']),
        ('الطابعات', counts['printer']), ('الشاشات', counts['monitor']),
        ('تراخيص GStar CAD', counts['gstar_license']), ('تعيينات 2026', counts['new_2026']),
        ('طلبات 2025', counts['request_2025']),
    ]
    summary_cells = []
    for label, count in summary_labels:
        summary_cells.append(Paragraph(f'{mixed_markup(label)}<br/><font name="Helvetica-Bold" size="13" color="#17365D">{count}</font>', ParagraphStyle(f'sum{len(summary_cells)}', fontName=arabic_font, fontSize=8, leading=12, alignment=1, textColor=colors.HexColor('#344B68'))))
    summary_second = summary_cells[4:] + [p_en('', value_mix)]
    summary = Table([summary_cells[:4], summary_second], colWidths=[135, 135, 135, 135], hAlign='RIGHT')
    summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F4F8FC')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#D0DAE6')),
        ('INNERGRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#DCE4EE')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story += [summary, Spacer(1, 7), p_ar('تفاصيل الأصول المسجلة على الموظف', section_ar)]

    headers = [
        p_ar('نوع الأصل', table_head), p_en('Serial Number', table_en_head),
        p_en('Computer Name New', table_en_head), p_ar('الوصف / الموديل', table_head),
        p_ar('الحالة', table_head),
    ]
    detail_rows = [headers]
    type_labels = dict(Asset.Types.choices)
    status_labels = dict(Asset.Status.choices)
    for asset in asset_rows:
        description_parts = [asset.item_type, asset.brand, asset.model]
        if asset.processor or asset.ram or asset.storage:
            spec = ' / '.join(x for x in [asset.processor, f'RAM {asset.ram}' if asset.ram else '', asset.storage] if x)
            if spec:
                description_parts.append(spec)
        if asset.asset_tag:
            description_parts.append(f'Asset No. {asset.asset_tag}')
        if asset.toner_code:
            description_parts.append(f'Toner: {asset.toner_code}')
        if asset.license_version:
            description_parts.append(f'License: {asset.license_version}')
        if asset.license_activated:
            description_parts.append(f'Activated: {asset.license_activated}')
        if asset.manufacturing_year:
            description_parts.append(f'Year: {asset.manufacturing_year}')
        if asset.purchase_date:
            description_parts.append(f'Date: {asset.purchase_date}')
        if asset.software_licenses:
            installed = [str(k) for k, v in asset.software_licenses.items() if str(v).strip().casefold() not in ('', 'no', 'none', 'false', '0', 'n/a')]
            if installed:
                description_parts.append('Software: ' + ', '.join(installed))
        device_description = ' | '.join(str(x) for x in description_parts if x)
        detail_rows.append([
            p_mixed(type_labels.get(asset.asset_type, asset.asset_type), table_cell),
            p_en(asset.serial_number or '-', table_cell),
            p_mixed(asset.computer_name_new or asset.computer_name or '-', table_cell),
            p_mixed(device_description or '-', table_cell),
            p_mixed(status_labels.get(asset.asset_status, asset.asset_status), table_cell),
        ])
    if not asset_rows:
        detail_rows.append([p_ar('لا توجد أصول مسجلة على هذا الكود حاليًا.', table_cell_ar), '', '', '', ''])
    detail_table = Table(detail_rows, colWidths=[78, 100, 105, 180, 72], repeatRows=1, hAlign='RIGHT')
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17365D')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CAD5E2')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFD')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('SPAN', (0, 1), (-1, 1)) if not asset_rows else ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story += [detail_table, Spacer(1, 13)]

    footer_rows = [
        [p_ar('اسم مسئول الدعم الفني : ......................................', small_ar),
         p_ar('تاريخ التقرير : ................................................', small_ar)],
        ['', p_ar('توقيع المستخدم : ......................................', small_ar)],
    ]
    footer_table = Table(footer_rows, colWidths=[272, 272], hAlign='RIGHT')
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    class BottomAlignedFooter(Flowable):
        def __init__(self, table):
            super().__init__()
            self.table = table
            self.width = 0
            self.height = 0

        def wrap(self, available_width, available_height):
            self.width = available_width
            # Fill the remaining frame to anchor the signatures at the page bottom.
            # If there is too little room, ReportLab moves this block to the next page.
            self.height = max(available_height, 85)
            return self.width, self.height

        def draw(self):
            _, table_height = self.table.wrapOn(self.canv, self.width, 60)
            self.canv.saveState()
            self.canv.setStrokeColor(colors.HexColor('#1F8A8A'))
            self.canv.setLineWidth(0.8)
            self.canv.line(0, table_height + 9, self.width, table_height + 9)
            self.table.drawOn(self.canv, 0, 3)
            self.canv.restoreState()

    story.append(BottomAlignedFooter(footer_table))
    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header)
    buf.seek(0)
    return buf
