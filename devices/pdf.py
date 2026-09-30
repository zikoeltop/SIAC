import io, os
from django.http import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from arabic_reshaper import reshape
from bidi.algorithm import get_display


def fix_ar(text):
    if text is None: return ''
    return get_display(reshape(str(text)))

def register_font():
    paths = ['C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
    for path in paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('SIACArabic', path))
                return 'SIACArabic'
            except Exception:
                pass
    return 'Helvetica'

def build_pdf(device):
    font = register_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    right = ParagraphStyle('right', fontName=font, fontSize=10, alignment=2, leading=13)
    center = ParagraphStyle('center', fontName=font, fontSize=16, alignment=1, spaceAfter=8)
    heading = ParagraphStyle('heading', fontName=font, fontSize=10, alignment=2, spaceAfter=2)
    story = [
        Paragraph(fix_ar('الشركة الهندسية للصناعات والتشييد (سياك)'), right),
        Paragraph(fix_ar('إدارة الحاسب الآلي ونظم المعلومات'), right), Spacer(1,4),
        Paragraph(fix_ar('إجراءات فحص جهاز'), center),
    ]
    fields = [
        [Paragraph(f'User Name : {device.user_name}', right), Paragraph(f'Project : {device.project}', right)],
        [Paragraph(f'Serial Number : {device.serial_number}', right), Paragraph(f'Model : {device.model}', right)],
        [Paragraph('', right), Paragraph(f'Pc Name : {device.computer_name}', right)],
    ]
    t = Table(fields, colWidths=[270,270]); t.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'RIGHT'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BOTTOMPADDING',(0,0),(-1,-1),2)])); story += [t, Spacer(1,8), Paragraph(fix_ar('إجراءات فحص جهاز:'), heading)]
    story += [Spacer(1,3), Paragraph(fix_ar('HDD :'), heading)]
    box = Table([[Paragraph(fix_ar(device.hdd), right)], [Paragraph('', right)]], colWidths=[540], rowHeights=[20,20]); box.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.black),('VALIGN',(0,0),(-1,-1),'MIDDLE')])); story += [box, Spacer(1,5)]
    ram_proc = [[Paragraph(fix_ar(f'RAM : [ {device.ram} ]'), heading), Paragraph(fix_ar(f'processor : [ {device.processor} ]'), right)]] + [[Paragraph('',right),Paragraph('',right)] for _ in range(3)]
    box2 = Table(ram_proc, colWidths=[270,270], rowHeights=[20,20,20,20]); box2.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.black),('VALIGN',(0,0),(-1,-1),'MIDDLE')])); story += [box2, Spacer(1,5)]
    for title in ['-3 نتيجة فحص Battery :','-4 نتيجة فحص الهيكل الخارجي والشكل العام :','-5 نوع وسريال الشاشة :','-6 نوع وسريال الطابعه :','-7 ملاحظات:']:
        story += [Paragraph(fix_ar(title), heading)]
        b = Table([[Paragraph('',right)],[Paragraph('',right)]], colWidths=[540], rowHeights=[20,20]); b.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.black),('VALIGN',(0,0),(-1,-1),'MIDDLE')])); story += [b, Spacer(1,5)]
    footer = [[Paragraph(fix_ar('اسم مسئول الدعم الفنى : ......................................'),right),Paragraph(fix_ar('تاريخ التقرير : ................................................'),right)],[Paragraph('',right),Paragraph(fix_ar('توقيع المستخدم : ......................................'),right)]]
    ft=Table(footer,colWidths=[270,270]); ft.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'RIGHT'),('BOTTOMPADDING',(0,0),(-1,-1),2)])); story.append(ft)
    doc.build(story); buf.seek(0); return buf
