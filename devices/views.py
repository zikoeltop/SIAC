from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from audit.models import AuditLog
from audit.utils import log_event
from accounts.decorators import admin_required
from .forms import ExcelUploadForm
from .models import Device, DeviceImport, PendingExcelImport
from .services import create_pending_import, import_excel, normalize_serial
from .pdf import build_pdf

@login_required
def dashboard(request):
    return render(request, 'devices/dashboard.html', {
        'device_count': Device.objects.count(),
        'user_count': __import__('accounts.models', fromlist=['User']).User.objects.count(),
        'is_admin': request.user.is_admin_role,
    })

@login_required
def search_device(request):
    serial = normalize_serial(request.GET.get('serial'))
    device = Device.objects.filter(serial_number__iexact=serial).first() if serial else None
    if serial:
        log_event(request.user, 'DEVICE_SEARCH', request, f'Searched serial {serial}; found={bool(device)}')
    return render(request, 'devices/search.html', {'device': device, 'serial': serial})

@login_required
def download_report(request, pk):
    device = get_object_or_404(Device, pk=pk)
    log_event(request.user, 'PDF_DOWNLOAD', request, f'Downloaded report for {device.serial_number}')
    return FileResponse(build_pdf(device), as_attachment=True, filename=f'Report_{device.serial_number}.pdf', content_type='application/pdf')

@admin_required
def manage_excel(request):
    current = DeviceImport.objects.filter(is_current=True).first()
    form = ExcelUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        try:
            pending = create_pending_import(form.cleaned_data['excel_file'], request.user)
            log_event(request.user, 'EXCEL_PREVIEW', request, f'Prepared Excel preview: {pending.valid_rows} valid, {pending.duplicate_rows} duplicates')
            return redirect('excel_preview', pk=pending.pk)
        except Exception as exc:
            messages.error(request, f'فشل قراءة الملف: {exc}')
    return render(request, 'devices/manage_excel.html', {'form': form, 'current': current})

@admin_required
def excel_preview(request, pk):
    pending = get_object_or_404(PendingExcelImport, pk=pk, uploaded_by=request.user, is_approved=False)
    if request.method == 'POST':
        try:
            with pending.file.open('rb') as f:
                count, record, info = import_excel(f, request.user)
            pending.is_approved = True
            pending.save(update_fields=['is_approved'])
            log_event(request.user, 'EXCEL_IMPORT', request, f'Approved Excel: {count} devices; duplicates ignored={info["duplicate_rows"]}')
            messages.success(request, f'تم اعتماد الملف بنجاح. تم تحميل {count} جهاز إلى قاعدة البيانات.')
            return redirect('manage_excel')
        except Exception as exc:
            messages.error(request, f'فشل اعتماد الملف: {exc}')
    return render(request, 'devices/excel_preview.html', {'pending': pending, 'current_count': Device.objects.count()})
