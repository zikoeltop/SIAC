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

# --- Employee custody report ---
def build_custody_pdf(employee, assets, hr_code=None):
    """Render SIAC's approved one-page custody report with notes and signature fields."""
    from weasyprint import HTML
    from .models import Asset

    base_dir = Path(__file__).resolve().parent.parent
    logo_path = base_dir / 'static' / 'img' / 'siac_logo.png'
    regular_font = base_dir / 'static' / 'fonts' / 'NotoSansArabic-Regular.ttf'
    bold_font = base_dir / 'static' / 'fonts' / 'NotoSansArabic-Bold.ttf'

    asset_rows = list(assets)
    # Keep only current-custody details in this report. Historical 2025/2026 request
    # sheets are intentionally not presented as active employee assets.
    asset_rows = [a for a in asset_rows if a.asset_type not in {Asset.Types.NEW_2026, Asset.Types.REQUEST_2025, Asset.Types.SCRAP}]

    def val(obj, key, fallback=''):
        if obj is None:
            return fallback
        value = getattr(obj, key, fallback)
        return '' if value is None else str(value).strip()

    def esc(value):
        value = clean_text(value)
        return html.escape(value, quote=True).replace('\n', '<br>')

    if employee:
        employee_name = val(employee, 'arabic_name') or val(employee, 'name') or val(employee, 'employee_name')
        hr_code = val(employee, 'hr_code') or hr_code
    else:
        employee_name = next((val(a, 'display_employee_name') for a in asset_rows if val(a, 'display_employee_name') not in ('', '-')), '')
    employee_name = employee_name or 'غير مسجل'
    hr_code = str(hr_code or '')

    def profile_value(primary, secondary=None):
        first = val(employee, primary)
        second = val(employee, secondary) if secondary else ''
        if primary == 'arabic_name' and not first and not second:
            first = employee_name
        if first and second and first.strip() != second.strip():
            return f'{esc(first)}<span class="subvalue" dir="ltr">{esc(second)}</span>'
        return esc(first or second or '-')

    def field_value(attribute, asset_attribute=None):
        value = val(employee, attribute)
        if not value and asset_attribute and asset_rows:
            value = val(asset_rows[0], asset_attribute)
        return esc(value or '-')

    type_labels = {
        Asset.Types.COMPUTER: 'كمبيوتر',
        Asset.Types.PRINTER: 'طابعة',
        Asset.Types.MONITOR: 'شاشة',
        Asset.Types.GSTAR: 'ترخيص GStar CAD',
        Asset.Types.OTHER: 'أصل آخر',
    }
    status_labels = {
        Asset.Status.ACTIVE: 'عهدة نشطة',
        Asset.Status.PENDING: 'معلق',
        Asset.Status.SCRAPPED: 'مخرد',
        Asset.Status.ARCHIVED: 'مؤرشف',
    }

    asset_html = []
    for asset in asset_rows:
        kind = val(asset, 'item_type')
        brand = val(asset, 'brand')
        model = val(asset, 'model')
        description_parts = [part for part in (kind, brand, model) if part]
        description = ' | '.join(description_parts)
        specs = []
        if val(asset, 'processor'):
            specs.append(val(asset, 'processor'))
        if val(asset, 'ram'):
            specs.append('RAM ' + val(asset, 'ram'))
        if val(asset, 'storage'):
            specs.append(val(asset, 'storage'))
        if specs:
            description = (description + ' - ' if description else '') + ' / '.join(specs)
        serial = val(asset, 'serial_number') or '-'
        computer_name = val(asset, 'computer_name_new') or val(asset, 'computer_name') or '-'
        asset_type = type_labels.get(val(asset, 'asset_type'), val(asset, 'asset_type')) or '-'
        status = status_labels.get(val(asset, 'asset_status'), val(asset, 'asset_status')) or '-'
        asset_html.append(
            '<tr>'
            f'<td>{esc(asset_type)}</td>'
            f'<td class="eng">{esc(serial)}</td>'
            f'<td class="eng">{esc(computer_name)}</td>'
            f'<td dir="auto">{esc(description or "-")}</td>'
            f'<td>{esc(status)}</td>'
            '</tr>'
        )

    if not asset_html:
        asset_html.append('<tr><td colspan="5" class="no-assets">لا توجد أصول نشطة مسجلة على هذا الموظف.</td></tr>')

    # Keep the large note-taking area for ordinary reports and compact the table
    # when an employee has many items so common cases remain on one A4 page.
    count = len(asset_rows)
    if count <= 4:
        row_padding, table_font, notes_height = '1.8mm', '7.4pt', 73
    elif count <= 8:
        row_padding, table_font, notes_height = '1.25mm', '7pt', 58
    elif count <= 12:
        row_padding, table_font, notes_height = '0.95mm', '6.6pt', 43
    elif count <= 18:
        row_padding, table_font, notes_height = '0.7mm', '6.1pt', 28
    elif count <= 25:
        row_padding, table_font, notes_height = '0.45mm', '5.7pt', 16
    else:
        row_padding, table_font, notes_height = '0.35mm', '5.2pt', 8

    logo_uri = logo_path.as_uri() if logo_path.exists() else ''
    # The build script downloads these fonts on Railway; the system font paths are
    # a local testing fallback and are not included in the project ZIP.
    fallback_regular = Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf')
    fallback_bold = Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf')
    font_regular_uri = (regular_font if regular_font.exists() else fallback_regular).as_uri()
    font_bold_uri = (bold_font if bold_font.exists() else fallback_bold).as_uri()
    company = val(employee, 'company') or (val(asset_rows[0], 'company') if asset_rows else '') or 'سياك للإنشاءات'
    project = field_value('project', 'project')
    sector = field_value('sector', 'sector')
    department = field_value('department', 'department')
    position = field_value('position')
    employment_status = field_value('employment_status')

    document = f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
@font-face {{ font-family: NotoArabic; src: url("{font_regular_uri}"); font-weight: 400; }}
@font-face {{ font-family: NotoArabic; src: url("{font_bold_uri}"); font-weight: 700; }}
@page {{ size: A4; margin: 9mm 10mm 10mm 10mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: NotoArabic, sans-serif; color: #18273a; font-size: 8.5pt; direction: rtl; margin: 0; }}
.header {{ display:flex; flex-direction:row; justify-content:space-between; align-items:center; border-bottom:2px solid #1f8a8a; padding:0 0 4mm; margin-bottom:4mm; min-height:24mm; }}
.logo {{ width:29mm; height:24mm; object-fit:contain; }}
.company {{ text-align:right; color:#17365d; line-height:1.55; font-size:10pt; font-weight:700; }}
.subline {{ font-weight:400; font-size:8.7pt; color:#344b68; }}
.title {{ text-align:center; font-size:17pt; font-weight:700; color:#17365d; margin:1mm 0 0; line-height:1.3; }}
.subtitle {{ font:bold 8.5pt Arial,sans-serif; direction:ltr; text-align:center; color:#1f8a8a; letter-spacing:.8px; margin:1mm 0 4mm; }}
table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
.profile {{ margin-bottom:4mm; }}
.profile td {{ border:.4pt solid #cad5e2; padding:2mm 2.2mm; vertical-align:middle; overflow-wrap:anywhere; font-size:7.8pt; line-height:1.25; }}
.profile .label {{ width:16%; background:#f0f5fa; color:#526174; font-weight:700; }}
.profile .value {{ width:34%; }}
.subvalue {{ display:block; direction:ltr; font:7pt Arial,sans-serif; color:#526174; margin-top:1px; text-align:right; }}
.section-title {{ color:#17365d; font-size:10pt; font-weight:700; margin:2mm 0 2mm; }}
.assets th {{ color:#17365d; background:#eaf2f5; font-weight:700; padding:2mm 1.5mm; font-size:7.1pt; border:.4pt solid #cad5e2; }}
.assets td {{ padding:{row_padding} 1.5mm; border:.4pt solid #cad5e2; vertical-align:middle; text-align:right; line-height:1.25; overflow-wrap:anywhere; font-size:{table_font}; }}
.assets tbody tr:nth-child(even) td {{ background:#f7fafd; }}
.assets td.eng, .assets th.eng {{ direction:ltr; text-align:center; font-family:Arial,sans-serif; }}
.assets .type {{ width:13%; }} .assets .serial {{ width:18%; }} .assets .computer {{ width:21%; }} .assets .description {{ width:32%; }} .assets .status {{ width:16%; }}
.no-assets {{ text-align:center!important; color:#526174; padding:4mm!important; }}
.notes-title {{ margin-top:4mm; margin-bottom:1.5mm; color:#17365d; font-size:10pt; font-weight:700; }}
.notes-box {{ border:.7pt solid #cad5e2; border-radius:2mm; height:{notes_height}mm; background:#fff; }}
.footer {{ position:fixed; bottom:0; left:0; right:0; border-top:1.1pt solid #1f8a8a; padding-top:3mm; height:23mm; color:#18273a; background:white; }}
.footerrow {{ display:flex; justify-content:space-between; gap:8mm; margin-bottom:3.2mm; }}
.footeritem {{ flex:1; white-space:nowrap; font-size:8.3pt; }}
.sign {{ width:55%; }}
</style>
</head>
<body>
<header class="header">
  <div class="company">الشركة الهندسية للصناعات والتشييد (سياك)<br><span class="subline">إدارة الحاسب الآلي ونظم المعلومات</span></div>
  {f'<img class="logo" src="{logo_uri}" alt="SIAC Construction">' if logo_uri else ''}
</header>
<div class="title">بيان عهدة الموظف</div>
<div class="subtitle">EMPLOYEE CUSTODY REPORT</div>
<table class="profile"><tbody>
<tr><td class="label">كود الموظف / HR ID</td><td class="value labelen" dir="ltr">{esc(hr_code or '-')}</td><td class="label">اسم الموظف / Employee Name</td><td class="value" dir="auto">{profile_value('arabic_name', 'name')}</td></tr>
<tr><td class="label">المشروع / Project</td><td class="value" dir="auto">{project}</td><td class="label">القطاع / Sector</td><td class="value" dir="auto">{sector}</td></tr>
<tr><td class="label">الإدارة / Department</td><td class="value" dir="auto">{department}</td><td class="label">الوظيفة / Position</td><td class="value" dir="auto">{position}</td></tr>
<tr><td class="label">الشركة / Company</td><td class="value" dir="auto">{esc(company)}</td><td class="label">حالة الموظف / Status</td><td class="value" dir="auto">{employment_status}</td></tr>
</tbody></table>
<div class="section-title">تفاصيل الأصول المسجلة على الموظف <span style="font:700 7.5pt Arial,sans-serif; color:#7890a2;">ASSET DETAILS</span></div>
<table class="assets"><thead><tr><th class="type">نوع الأصل</th><th class="serial eng">Serial Number</th><th class="computer eng">Computer Name New</th><th class="description">الوصف / الموديل</th><th class="status">الحالة</th></tr></thead>
<tbody>{''.join(asset_html)}</tbody></table>
<div class="notes-title">ملاحظات <span style="font:700 7.5pt Arial,sans-serif; color:#7890a2;">NOTES</span></div>
<div class="notes-box"></div>
<div class="footer">
  <div class="footerrow"><div class="footeritem">اسم مسئول الدعم الفني : ......................................</div><div class="footeritem">تاريخ التقرير : ................................................</div></div>
  <div class="footerrow"><div class="footeritem sign">توقيع المستخدم : ......................................</div></div>
  <div style="display:flex;justify-content:space-between;border-top:.4pt solid #dce5ec;padding-top:1.5mm;margin-top:1mm;color:#9aabb8;font-size:6.5pt;"><span>بيان عهدة الموظف</span><span style="font-family:Arial,sans-serif;direction:ltr;">SIAC • INTERNAL DOCUMENT</span><span>إدارة الحاسب الآلي ونظم المعلومات</span></div>
</div>
</body></html>'''

    pdf_bytes = HTML(string=document, base_url=str(base_dir)).write_pdf()
    return io.BytesIO(pdf_bytes)
