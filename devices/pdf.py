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
    """Build the approved SIAC one-page custody statement (not the device inspection PDF)."""
    from weasyprint import HTML
    from .models import Asset

    base_dir = Path(__file__).resolve().parent.parent
    logo_path = base_dir / 'static' / 'img' / 'siac_logo.png'
    regular_font = base_dir / 'static' / 'fonts' / 'NotoSansArabic-Regular.ttf'
    bold_font = base_dir / 'static' / 'fonts' / 'NotoSansArabic-Bold.ttf'

    def val(obj, key, fallback=''):
        if obj is None:
            return fallback
        value = getattr(obj, key, fallback)
        return '' if value is None else str(value).strip()

    def date_text(value):
        if not value:
            return 'غير مسجل'
        try:
            return value.strftime('%d %b %Y')
        except Exception:
            return str(value).strip() or 'غير مسجل'

    def raw(asset, *keys):
        values = getattr(asset, 'raw_data', {}) or {}
        for key in keys:
            value = values.get(key)
            if value is not None and str(value).strip() and str(value).strip().lower() != 'nan':
                return str(value).strip()
        return ''

    def esc(value):
        text = clean_text(value)
        return html.escape(text, quote=True).replace('\n', '<br>')

    def field(obj, key, default='-'):
        return esc(val(obj, key) or default)

    def heading(bilingual_ar, bilingual_en=''):
        return (f'<div class="section-heading"><strong>{esc(bilingual_ar)}</strong>'
                f'<span>{esc(bilingual_en)}</span></div>')

    rows = list(assets or [])
    excluded = {Asset.Types.NEW_2026, Asset.Types.REQUEST_2025, Asset.Types.SCRAP}
    rows = [a for a in rows if val(a, 'asset_type') not in excluded and val(a, 'asset_status') != Asset.Status.SCRAPPED]
    computers = [a for a in rows if val(a, 'asset_type') == Asset.Types.COMPUTER]
    monitors = [a for a in rows if val(a, 'asset_type') == Asset.Types.MONITOR]
    printers = [a for a in rows if val(a, 'asset_type') == Asset.Types.PRINTER]
    licenses = [a for a in rows if val(a, 'asset_type') == Asset.Types.GSTAR]
    others = [a for a in rows if val(a, 'asset_type') == Asset.Types.OTHER]

    employee_name = val(employee, 'name') or next((val(a, 'display_employee_name') for a in rows if val(a, 'display_employee_name') not in ('', '-')), '') or 'غير مسجل'
    employee_arabic_name = val(employee, 'arabic_name')
    code = val(employee, 'hr_code') or str(hr_code or '')
    hiring_date = date_text(getattr(employee, 'hiring_date', None))
    termination_date = date_text(getattr(employee, 'termination_date', None))
    cost_center = val(employee, 'cost_center')
    project = val(employee, 'project') or next((val(a, 'project') for a in rows if val(a, 'project')), '')
    sector = val(employee, 'sector') or next((val(a, 'sector') for a in rows if val(a, 'sector')), '')
    department = val(employee, 'department') or next((val(a, 'department') for a in rows if val(a, 'department')), '')
    position = val(employee, 'position')

    # Tune density to keep the approved statement on one A4 page.
    total_rows = len(rows)
    if total_rows <= 5:
        cell_pad, body_font, notes_height = '1.35mm', '7pt', '23mm'
    elif total_rows <= 10:
        cell_pad, body_font, notes_height = '0.95mm', '6.5pt', '17mm'
    elif total_rows <= 18:
        cell_pad, body_font, notes_height = '0.6mm', '5.9pt', '10mm'
    elif total_rows <= 28:
        cell_pad, body_font, notes_height = '0.35mm', '5.2pt', '5mm'
    else:
        cell_pad, body_font, notes_height = '0.2mm', '4.6pt', '3mm'

    def asset_specs(asset):
        specs = [
            ('المعالج / Processor', val(asset, 'processor')),
            ('الذاكرة / RAM', val(asset, 'ram')),
            ('التخزين / HDD', val(asset, 'storage')),
        ]
        return ''.join(
            f'<div class="spec"><span>{esc(label)}</span><b>{esc(value or "غير مسجل")}</b></div>'
            for label, value in specs
        )

    computer_rows = []
    for a in computers:
        computer_name = val(a, 'computer_name_new') or val(a, 'computer_name') or raw(a, 'Computer Name New', 'Computer Name') or '-'
        computer_rows.append(
            '<tr>'
            f'<td>{esc(computer_name)}</td>'
            f'<td>{field(a, "item_type")}</td>'
            f'<td>{field(a, "brand")}</td>'
            f'<td>{field(a, "model")}</td>'
            f'<td class="eng">{field(a, "serial_number")}</td>'
            f'<td class="eng">{field(a, "manufacturing_year")}</td>'
            '</tr>'
            f'<tr class="spec-row"><td colspan="6"><div class="spec-grid">{asset_specs(a)}</div></td></tr>'
        )
    if not computer_rows:
        computer_rows.append('<tr><td colspan="6" class="empty">لا توجد أجهزة كمبيوتر مسجلة على عهدة الموظف.</td></tr>')

    monitor_rows = []
    for a in monitors:
        monitor_rows.append(
            '<tr>'
            f'<td>{esc(raw(a, "Name", "Computer Name") or val(a, "computer_name_new") or val(a, "computer_name") or val(a, "item_type") or "-")}</td>'
            f'<td>{field(a, "brand")}</td>'
            f'<td>{esc(raw(a, "Model") or val(a, "model") or "-")}</td>'
            f'<td class="eng">{esc(raw(a, "Size") or val(a, "item_type") or "-")}</td>'
            f'<td class="eng">{field(a, "serial_number")}</td>'
            f'<td class="eng">{esc(raw(a, "Asset Number") or val(a, "asset_tag") or "—")}</td>'
            '</tr>'
        )
    if not monitor_rows:
        monitor_rows.append('<tr><td colspan="6" class="empty">لا توجد شاشات مسجلة على عهدة الموظف.</td></tr>')

    license_rows = []
    for a in licenses:
        license_key = raw(a, 'Gstar PRO', 'License Key') or val(a, 'model') or val(a, 'item_type') or '-'
        license_rows.append(
            '<tr>'
            f'<td class="eng">{field(a, "serial_number")}</td>'
            f'<td class="eng">{esc(raw(a, "Version") or val(a, "license_version") or "-")}</td>'
            f'<td class="eng">{esc(raw(a, "Activated") or val(a, "license_activated") or "-")}</td>'
            f'<td class="eng license-key">{esc(license_key)}</td>'
            f'<td class="eng">{esc(raw(a, "Email to send License") or val(a, "email") or "—")}</td>'
            '</tr>'
        )
    if not license_rows:
        license_rows.append('<tr><td colspan="5" class="empty">لا توجد تراخيص GStar CAD مسجلة على عهدة الموظف.</td></tr>')

    printer_list = ''.join(
        f'<div class="printer-line">{esc(val(a, "computer_name_new") or val(a, "computer_name") or val(a, "item_type") or "طابعة")} — '
        f'<span dir="ltr">{esc(val(a, "serial_number") or "-")}</span></div>' for a in printers
    )
    printer_message = printer_list if printers else 'لا توجد طابعات مسجلة على عهدة الموظف.'
    other_rows = []
    for a in others:
        label = val(a, 'item_type') or val(a, 'model') or 'أصل آخر'
        other_rows.append(f'<div class="printer-line">{esc(label)} — <span dir="ltr">{esc(val(a, "serial_number") or "-")}</span></div>')
    other_html = '<div class="other-extra">' + ''.join(other_rows) + '</div>' if other_rows else ''

    logo_uri = logo_path.as_uri() if logo_path.exists() else ''
    fallback_regular = Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf')
    fallback_bold = Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf')
    font_regular_uri = (regular_font if regular_font.exists() else fallback_regular).as_uri()
    font_bold_uri = (bold_font if bold_font.exists() else fallback_bold).as_uri()

    doc = f'''<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>
@font-face {{font-family:NotoArabic;src:url("{font_regular_uri}");font-weight:400;}}
@font-face {{font-family:NotoArabic;src:url("{font_bold_uri}");font-weight:700;}}
@page {{size:A4;margin:6.5mm 7.5mm 7mm 7.5mm;}}
* {{box-sizing:border-box;}}
body {{font-family:NotoArabic,sans-serif;color:#203447;font-size:7.15pt;line-height:1.25;margin:0;direction:rtl;}}
.header {{direction:ltr;display:flex;justify-content:space-between;align-items:center;border-bottom:2.2pt solid #1f8987;padding-bottom:2.2mm;margin-bottom:2.2mm;min-height:20mm;}}
.logo {{width:27mm;height:20mm;object-fit:contain;}}
.company {{text-align:right;color:#173e56;font-weight:700;font-size:9.7pt;line-height:1.5;}}
.company small {{display:block;font-weight:400;font-size:7.5pt;color:#627887;}}
.titlebar {{display:flex;justify-content:space-between;align-items:center;background:#173f58;color:white;border-radius:1.6mm;padding:2mm 3mm;margin:0 0 2.2mm;min-height:13mm;}}
.titlebar .main-title {{font-size:12.4pt;font-weight:700;line-height:1.25;}}
.titlebar .english {{font:7.2pt Arial,sans-serif;direction:ltr;text-align:right;letter-spacing:.35px;color:#c1d2d8;margin-top:.6mm;}}
.internal {{background:#e0f3f1;color:#287f7d;border-radius:4mm;padding:1.15mm 2.4mm;font-size:6.2pt;font-weight:700;white-space:nowrap;}}
.section-heading {{display:flex;justify-content:space-between;align-items:center;margin:1.4mm 0 1mm;color:#173f58;font-size:8.4pt;font-weight:700;}}
.section-heading span {{font:6.2pt Arial,sans-serif;direction:ltr;color:#91a4af;letter-spacing:.35px;}}
.profile {{display:grid;grid-template-columns:1fr 1.9fr;gap:1.2mm;margin-bottom:1.8mm;}}
.profile-box {{border:.45pt solid #d6e0e7;border-radius:1.7mm;padding:1.55mm 2mm;min-height:10mm;display:flex;flex-direction:column;justify-content:space-between;}}
.profile-row {{display:grid;gap:1.2mm;margin-bottom:1.2mm;}}
.profile-row.two {{grid-template-columns:1fr 1fr;}}
.profile-row.three {{grid-template-columns:1fr 1fr 1fr;}}
.label {{font-size:6.15pt;color:#8798a5;line-height:1.2;}}
.value {{font-size:7.55pt;color:#273b4d;font-weight:700;overflow-wrap:anywhere;margin-top:1mm;}}
.value.ltr {{direction:ltr;text-align:right;font-family:Arial,sans-serif;}}
.assets {{width:100%;border-collapse:collapse;table-layout:fixed;margin-bottom:1.2mm;}}
.assets th {{background:#eaf2f5;color:#29485c;font-weight:700;font-size:6.2pt;line-height:1.15;padding:{cell_pad} 1mm;border:.4pt solid #d0dce3;vertical-align:middle;}}
.assets td {{font-size:{body_font};line-height:1.2;padding:{cell_pad} 1mm;border:.4pt solid #d0dce3;vertical-align:middle;overflow-wrap:anywhere;text-align:center;}}
.assets tbody tr:nth-child(odd) td {{background:#fff;}}
.assets tbody tr:nth-child(even) td {{background:#f8fbfd;}}
.assets .eng {{direction:ltr;font-family:Arial,sans-serif;text-align:center;}}
.assets .empty {{padding:2mm;text-align:center;color:#728592;}}
.spec-row td {{background:#f4f8fa!important;padding:.7mm 1mm!important;}}
.spec-grid {{display:grid;grid-template-columns:repeat(3,1fr);gap:1mm;}}
.spec {{display:flex;justify-content:space-between;gap:1mm;white-space:normal;}}
.spec span {{color:#8294a0;font-size:5.7pt;}}
.spec b {{font-weight:700;font-size:6pt;}}
.computers col:nth-child(1) {{width:18%;}} .computers col:nth-child(2) {{width:12%;}} .computers col:nth-child(3) {{width:11%;}} .computers col:nth-child(4) {{width:19%;}} .computers col:nth-child(5) {{width:23%;}} .computers col:nth-child(6) {{width:17%;}}
.monitors col:nth-child(1) {{width:20%;}} .monitors col:nth-child(2) {{width:12%;}} .monitors col:nth-child(3) {{width:16%;}} .monitors col:nth-child(4) {{width:8%;}} .monitors col:nth-child(5) {{width:28%;}} .monitors col:nth-child(6) {{width:16%;}}
.licenses col:nth-child(1) {{width:15%;}} .licenses col:nth-child(2) {{width:10%;}} .licenses col:nth-child(3) {{width:11%;}} .licenses col:nth-child(4) {{width:44%;}} .licenses col:nth-child(5) {{width:20%;}}
.other-box {{border:.45pt dashed #d6e0e7;border-radius:1.6mm;background:#f7fafb;padding:1.5mm 2mm;margin-bottom:1.3mm;}}
.printer-head {{display:flex;align-items:center;justify-content:space-between;font-weight:700;font-size:6.8pt;color:#40586a;}}
.count {{background:#e4f4f2;color:#24827e;border-radius:1.4mm;padding:1mm 3mm;font-size:8pt;font-weight:700;min-width:9mm;text-align:center;}}
.printer-message {{font-size:6.2pt;color:#7b8d99;margin-top:.7mm;}}
.printer-line {{font-size:6.1pt;color:#536979;margin-top:.6mm;}}
.notes-title {{margin:1.5mm 0 1mm;font-size:8.4pt;font-weight:700;color:#173f58;}}
.notes-box {{border:.55pt solid #d4dfe7;border-radius:1.7mm;height:{notes_height};background:linear-gradient(to bottom,transparent calc(100% - .35pt),#e6edf1 calc(100% - .35pt)) 0 0/100% 8mm repeat-y;}}
.footer {{border-top:2.2pt solid #1f8987;padding-top:2mm;margin-top:2mm;}}
.footer-row {{display:flex;gap:2mm;margin-bottom:1.4mm;}}
.footer-item {{flex:1;border:.45pt solid #d6e0e7;border-radius:1.5mm;min-height:8.5mm;padding:1.8mm 2mm;font-size:6.8pt;color:#455f70;display:flex;justify-content:space-between;align-items:center;gap:1mm;}}
.footer-item .dots {{color:#8a9ba6;white-space:nowrap;}}
.signature {{min-height:8mm;}}
.bottomline {{display:flex;justify-content:space-between;border-top:.4pt solid #e0e7ec;padding-top:1.2mm;margin-top:.5mm;color:#9aaab4;font-size:5.4pt;}}
.bottomline .eng {{font:5.4pt Arial,sans-serif;direction:ltr;}}
</style></head><body>
<header class="header"><img class="logo" src="{logo_uri}" alt="SIAC Construction"><div class="company">الشركة الهندسية للصناعات والتشييد (سياك)<small>إدارة الحاسب الآلي ونظم المعلومات</small></div></header>
<div class="titlebar"><div><div class="main-title">بيان عهدة الموظف والأصول المسجلة</div><div class="english">EMPLOYEE ASSET CUSTODY REPORT</div></div><span class="internal">للاستخدام الداخلي</span></div>
{heading('بيانات الموظف', 'EMPLOYEE INFORMATION')}
<div class="profile">
  <div class="profile-box"><div class="label">كود الموظف / HR ID</div><div class="value ltr">{esc(code or '-')}</div></div>
  <div class="profile-box"><div class="label">اسم الموظف / Employee Name</div><div class="value ltr">{esc(employee_name)}</div>{f'<div class="label">{esc(employee_arabic_name)}</div>' if employee_arabic_name else ''}</div>
</div>
<div class="profile-row two">
 <div class="profile-box"><div class="label">الوظيفة / Position</div><div class="value">{esc(position or '-')}</div></div>
 <div class="profile-box"><div class="label">القطاع / Sector</div><div class="value">{esc(sector or '-')}</div></div>
</div>
<div class="profile-row three">
 <div class="profile-box"><div class="label">المشروع / الموقع / Project / Site</div><div class="value">{esc(project or '-')}</div></div>
 <div class="profile-box"><div class="label">الإدارة / Department</div><div class="value">{esc(department or '-')}</div></div>
 <div class="profile-box"><div class="label">مركز التكلفة / Cost Center</div><div class="value">{esc(cost_center or '-')}</div></div>
</div>
<div class="profile-row two">
 <div class="profile-box"><div class="label">تاريخ التعيين / Hiring Date</div><div class="value ltr">{esc(hiring_date)}</div></div>
 <div class="profile-box"><div class="label">تاريخ انتهاء الخدمة / Termination Date</div><div class="value">{esc(termination_date)}</div></div>
</div>
{heading('أجهزة الكمبيوتر واللاب توب ومحطات العمل', f'COMPUTERS / LAPTOPS / WORKSTATIONS · {len(computers)}')}
<table class="assets computers"><colgroup><col><col><col><col><col><col></colgroup><thead><tr><th>اسم الجهاز<br>Computer Name</th><th>النوع<br>Type</th><th>الماركة<br>Brand</th><th>الموديل<br>Model</th><th class="eng">Serial Number</th><th>سنة الصنع<br>Mfg Year</th></tr></thead><tbody>{''.join(computer_rows)}</tbody></table>
{heading('الشاشات', f'MONITORS · {len(monitors)}')}
<table class="assets monitors"><colgroup><col><col><col><col><col><col></colgroup><thead><tr><th>اسم الشاشة<br>Name</th><th>الماركة<br>Brand</th><th>الموديل<br>Model</th><th>المقاس<br>Size</th><th class="eng">Serial Number</th><th>رقم الأصل<br>Asset No.</th></tr></thead><tbody>{''.join(monitor_rows)}</tbody></table>
{heading('تراخيص GStar CAD', f'GSTAR CAD LICENSES · {len(licenses)}')}
<table class="assets licenses"><colgroup><col><col><col><col><col></colgroup><thead><tr><th>الجهاز<br>Computer SN</th><th>الإصدار<br>Version</th><th>التفعيل<br>Activated</th><th>مفتاح الترخيص<br>License Key</th><th>البريد الإلكتروني<br>Email</th></tr></thead><tbody>{''.join(license_rows)}</tbody></table>
{heading('بنود أخرى', 'OTHER CUSTODY RECORDS')}
<div class="other-box"><div class="printer-head"><span>الطابعات / Printers</span><span class="count">{len(printers)}</span></div><div class="printer-message">{printer_message}</div>{other_html}</div>
<div class="notes-title">ملاحظات <span style="font:6.2pt Arial,sans-serif;direction:ltr;color:#91a4af;">NOTES</span></div>
<div class="notes-box"></div>
<div class="footer">
 <div class="footer-row"><div class="footer-item"><span>تاريخ التقرير :</span><span class="dots">................................................</span></div><div class="footer-item"><span>اسم مسئول الدعم الفني :</span><span class="dots">......................................</span></div></div>
 <div class="footer-row"><div class="footer-item signature"><span>توقيع المستخدم :</span><span class="dots">......................................</span></div></div>
 <div class="bottomline"><span>بيان عهدة الموظف</span><span class="eng">SIAC · INTERNAL DOCUMENT</span><span>إدارة الحاسب الآلي ونظم المعلومات</span></div>
</div>
</body></html>'''

    pdf_bytes = HTML(string=doc, base_url=str(base_dir)).write_pdf()
    return io.BytesIO(pdf_bytes)

