from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import FileResponse, HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from accounts.decorators import admin_required
from accounts.models import User
from audit.models import AuditLog
from audit.utils import log_event
from .forms import AssetForm, EmployeeForm, ExcelUploadForm, InventoryWorkbookImportForm
from .inventory_exports import build_inventory_excel_response
from .inventory_services import import_inventory_workbook, preview_inventory_workbook
from .models import Asset, Device, DeviceImport, Employee, PendingExcelImport, PendingInventoryImport
from .services import create_pending_import, import_excel, normalize_serial
from .pdf import build_pdf, build_custody_pdf


def _custody_assets(hr_code):
    if not hr_code:
        return Asset.objects.none()
    return Asset.objects.filter(hr_code__iexact=hr_code, asset_status=Asset.Status.ACTIVE).exclude(
        asset_type=Asset.Types.SCRAP
    ).select_related('employee').order_by('asset_type', 'serial_number', 'id')


@login_required
def dashboard(request):
    return render(request, 'devices/dashboard.html', {
        'device_count': Device.objects.count(),
        'asset_count': Asset.objects.count(),
        'employee_count': Employee.objects.count(),
        'user_count': User.objects.count(),
        'is_admin': request.user.is_admin_role,
    })


@login_required
def search_device(request):
    # The supported search keys are deliberately limited to Serial Number and HR Code.
    serial = normalize_serial(request.GET.get('serial'))
    hr_code = normalize_serial(request.GET.get('hr_code'))
    mode = 'serial' if serial else ('hr' if hr_code else '')
    matched_assets = []
    custody_assets = []
    employee = None
    legacy_device = None
    matched_owners = []
    resolved_hr_code = hr_code
    found = False

    if serial:
        matched_assets = list(Asset.objects.filter(serial_number__iexact=serial).select_related('employee').order_by('source_sheet', 'id'))
        if not matched_assets:
            legacy_device = Device.objects.filter(serial_number__iexact=serial).first()
        codes = []
        for asset in matched_assets:
            code = (asset.hr_code or (asset.employee.hr_code if asset.employee_id else '')).strip()
            if code and code.casefold() not in [c.casefold() for c in codes]:
                codes.append(code)
        for code in codes:
            owner = Employee.objects.filter(hr_code__iexact=code).first()
            owner_assets = list(_custody_assets(code))
            sample = next((a for a in matched_assets if a.hr_code.casefold() == code.casefold()), None)
            matched_owners.append({
                'hr_code': code,
                'employee': owner,
                'employee_name': owner.name if owner else (sample.display_employee_name if sample else ''),
                'project': owner.project if owner else (sample.project if sample else ''),
                'asset_count': len(owner_assets),
            })
        if len(matched_owners) == 1:
            resolved_hr_code = matched_owners[0]['hr_code']
            employee = matched_owners[0]['employee']
            custody_assets = list(_custody_assets(resolved_hr_code))
        found = bool(matched_assets or legacy_device)
        log_event(request.user, 'ASSET_SEARCH', request, f'Searched serial {serial}; found={found}; matches={len(matched_assets)}')
    elif hr_code:
        employee = Employee.objects.filter(hr_code__iexact=hr_code).first()
        matched_assets = list(Asset.objects.filter(hr_code__iexact=hr_code).select_related('employee').order_by('asset_type', 'id'))
        custody_assets = list(_custody_assets(hr_code))
        found = bool(employee or matched_assets)
        log_event(request.user, 'ASSET_SEARCH', request, f'Searched HR Code {hr_code}; found={found}; assets={len(matched_assets)}')

    sample_asset = matched_assets[0] if matched_assets else None
    selected_owner = matched_owners[0] if len(matched_owners) == 1 else {}
    display_employee_name = (
        (employee.name if employee else '')
        or selected_owner.get('employee_name', '')
        or (sample_asset.display_employee_name if sample_asset else '')
    )
    display_project = (
        (employee.project if employee else '')
        or selected_owner.get('project', '')
        or (sample_asset.project if sample_asset else '')
    )
    display_sector = (employee.sector if employee else '') or (sample_asset.sector if sample_asset else '')
    display_department = (employee.department if employee else '') or (sample_asset.department if sample_asset else '')
    context = {
        'serial': serial,
        'hr_code': hr_code,
        'mode': mode,
        'found': found,
        'employee': employee,
        'resolved_hr_code': resolved_hr_code,
        'matched_assets': matched_assets,
        'custody_assets': custody_assets,
        'matched_owners': matched_owners,
        'legacy_device': legacy_device,
        'active_count': len(custody_assets),
        'display_employee_name': display_employee_name,
        'display_project': display_project,
        'display_sector': display_sector,
        'display_department': display_department,
    }
    return render(request, 'devices/search.html', context)


@login_required
def download_custody_report(request, hr_code):
    code = normalize_serial(hr_code)
    employee = Employee.objects.filter(hr_code__iexact=code).first()
    assets = list(_custody_assets(code))
    all_matching = Asset.objects.filter(hr_code__iexact=code).exclude(asset_type=Asset.Types.SCRAP).exists()
    if not employee and not all_matching:
        messages.error(request, 'لا يوجد موظف أو أصول مرتبطة بكود HR هذا.')
        return redirect('search_device')
    log_event(request.user, 'CUSTODY_PDF_DOWNLOAD', request, f'Downloaded custody PDF for HR Code {code}')
    filename = slugify(code) or 'employee'
    return FileResponse(
        build_custody_pdf(employee, assets, hr_code=code),
        as_attachment=True,
        filename=f'SIAC_Custody_{filename}.pdf',
        content_type='application/pdf',
    )


@login_required
def download_report(request, pk):
    device = get_object_or_404(Device, pk=pk)
    log_event(request.user, 'PDF_DOWNLOAD', request, f'Downloaded legacy device report for {device.serial_number}')
    return FileResponse(build_pdf(device), as_attachment=True, filename=f'Report_{device.serial_number}.pdf', content_type='application/pdf')


# ---- Admin-only employee and asset management ----
@admin_required
def employee_list(request):
    query = (request.GET.get('q') or '').strip()
    employees = Employee.objects.all()
    if query:
        employees = employees.filter(
            Q(hr_code__icontains=query) | Q(name__icontains=query) | Q(arabic_name__icontains=query)
            | Q(project__icontains=query) | Q(department__icontains=query)
        )
    pager = Paginator(employees, 50)
    page = pager.get_page(request.GET.get('page'))
    return render(request, 'inventory/employee_list.html', {'page': page, 'query': query, 'employee_count': employees.count()})


@admin_required
def employee_create(request):
    form = EmployeeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        employee = form.save()
        log_event(request.user, 'EMPLOYEE_CREATE', request, f'Created employee HR Code {employee.hr_code}')
        messages.success(request, f'تمت إضافة الموظف {employee.name}.')
        return redirect('employee_list')
    return render(request, 'inventory/employee_form.html', {'form': form, 'title': 'إضافة موظف جديد'})


@admin_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    old_hr_code = employee.hr_code
    form = EmployeeForm(request.POST or None, instance=employee)
    if request.method == 'POST' and form.is_valid():
        updated = form.save()
        if old_hr_code != updated.hr_code:
            Asset.objects.filter(hr_code=old_hr_code).update(hr_code=updated.hr_code, employee=updated)
        log_event(request.user, 'EMPLOYEE_EDIT', request, f'Edited employee HR Code {updated.hr_code}')
        messages.success(request, 'تم حفظ بيانات الموظف وتحديث روابط عهدته.')
        return redirect('employee_list')
    return render(request, 'inventory/employee_form.html', {'form': form, 'title': f'تعديل الموظف: {employee.name}'})


@admin_required
def asset_list(request):
    query = (request.GET.get('q') or '').strip()
    asset_type = (request.GET.get('type') or '').strip()
    assets = Asset.objects.select_related('employee').all()
    if query:
        assets = assets.filter(
            Q(serial_number__icontains=query) | Q(hr_code__icontains=query)
            | Q(employee_name__icontains=query) | Q(employee__name__icontains=query)
            | Q(computer_name_new__icontains=query) | Q(computer_name__icontains=query)
            | Q(model__icontains=query) | Q(project__icontains=query)
        )
    if asset_type in dict(Asset.Types.choices):
        assets = assets.filter(asset_type=asset_type)
    pager = Paginator(assets.order_by('asset_type', 'serial_number', 'id'), 50)
    page = pager.get_page(request.GET.get('page'))
    return render(request, 'inventory/asset_list.html', {
        'page': page, 'query': query, 'selected_type': asset_type,
        'asset_types': Asset.Types.choices, 'asset_count': assets.count(),
    })


@admin_required
def asset_create(request):
    form = AssetForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        asset = form.save()
        log_event(request.user, 'ASSET_CREATE', request, f'Created asset type={asset.asset_type}, serial={asset.serial_number}')
        if asset.hr_code and not asset.employee_id:
            messages.warning(request, 'تم حفظ الأصل، لكن HR Code غير موجود في قائمة الموظفين؛ ستظل البيانات محفوظة ويمكن ربطه لاحقًا.')
        else:
            messages.success(request, 'تمت إضافة الأصل بنجاح.')
        return redirect('asset_list')
    return render(request, 'inventory/asset_form.html', {'form': form, 'title': 'إضافة أصل جديد'})


@admin_required
def asset_edit(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    form = AssetForm(request.POST or None, instance=asset)
    if request.method == 'POST' and form.is_valid():
        updated = form.save()
        log_event(request.user, 'ASSET_EDIT', request, f'Edited asset id={updated.pk}, serial={updated.serial_number}')
        if updated.hr_code and not updated.employee_id:
            messages.warning(request, 'تم حفظ التعديل، لكن HR Code غير موجود في قائمة الموظفين.')
        else:
            messages.success(request, 'تم حفظ تعديلات الأصل.')
        return redirect('asset_list')
    return render(request, 'inventory/asset_form.html', {'form': form, 'title': f'تعديل الأصل: {asset.serial_number or asset.model or asset.pk}'})


@admin_required
def inventory_import(request):
    form = InventoryWorkbookImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        workbook = form.cleaned_data['workbook']
        try:
            summary = preview_inventory_workbook(workbook)
            pending = PendingInventoryImport.objects.create(
                file=workbook, uploaded_by=request.user, summary=summary
            )
            log_event(request.user, 'INVENTORY_PREVIEW', request, f"Previewed inventory workbook: employees={summary['employees']}, assets={summary['total_assets']}")
            return redirect('inventory_import_preview', pk=pending.pk)
        except Exception as exc:
            messages.error(request, f'تعذر قراءة الملف: {exc}')
    return render(request, 'inventory/import.html', {'form': form})


@admin_required
def inventory_import_preview(request, pk):
    pending = get_object_or_404(PendingInventoryImport, pk=pk, uploaded_by=request.user, is_approved=False)
    if request.method == 'POST':
        try:
            with pending.file.open('rb') as workbook:
                result = import_inventory_workbook(workbook)
            pending.is_approved = True
            pending.save(update_fields=['is_approved'])
            details = ', '.join(f'{name}: {count}' for name, count in result['by_sheet'].items())
            log_event(request.user, 'INVENTORY_IMPORT', request, f"Imported inventory workbook: employees={result['employees']}, assets={result['assets']}; {details}")
            messages.success(request, f"اكتمل الاستيراد: {result['employees']} موظفًا و{result['assets']} سجل أصل. تم تحديث السجلات المستوردة دون حذف الإدخالات اليدوية.")
            return redirect('asset_list')
        except Exception as exc:
            messages.error(request, f'تعذر استيراد الملف: {exc}')
    return render(request, 'inventory/import_preview.html', {'pending': pending, 'summary': pending.summary})


@admin_required
def inventory_export(request):
    response = build_inventory_excel_response()
    log_event(request.user, 'INVENTORY_EXPORT', request, f'Exported inventory workbook: assets={Asset.objects.count()}, employees={Employee.objects.count()}')
    return response


# Legacy single-sheet Excel import remains available for compatibility with the initial version.
@admin_required
def manage_excel(request):
    current = DeviceImport.objects.filter(is_current=True).first()
    form = ExcelUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        try:
            pending = create_pending_import(form.cleaned_data['excel_file'], request.user)
            log_event(request.user, 'EXCEL_PREVIEW', request, f'Prepared legacy Excel preview: {pending.valid_rows} valid, {pending.duplicate_rows} duplicates')
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
            log_event(request.user, 'EXCEL_IMPORT', request, f'Approved legacy Excel import: {count} devices; duplicates ignored={info["duplicate_rows"]}')
            messages.success(request, f'تم اعتماد الملف بنجاح. تم تحميل {count} جهاز إلى قاعدة البيانات القديمة.')
            return redirect('manage_excel')
        except Exception as exc:
            messages.error(request, f'فشل اعتماد الملف: {exc}')
    return render(request, 'devices/excel_preview.html', {'pending': pending, 'current_count': Device.objects.count()})
