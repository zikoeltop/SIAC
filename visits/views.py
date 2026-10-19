import json
import io
from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from devices.models import Asset, Employee, Device
from audit.utils import log_event
from .models import Visit, VisitItem

def _projects():
    values = set(Asset.objects.exclude(project="").values_list("project", flat=True))
    values.update(Employee.objects.exclude(project="").values_list("project", flat=True))
    return sorted((v.strip() for v in values if v and v.strip()), key=str.casefold)

def _device_lookup(serial):
    assets = Asset.objects.filter(serial_number__iexact=serial).exclude(asset_type=Asset.Types.SCRAP).select_related("employee").order_by("id")
    asset = next((a for a in assets if a.asset_type == Asset.Types.COMPUTER), None) or assets.first()
    if not asset:
        asset = Asset.objects.filter(computer_name__iexact=serial).exclude(asset_type=Asset.Types.SCRAP).select_related("employee").first()
    if not asset:
        legacy = Device.objects.filter(Q(serial_number__iexact=serial) | Q(computer_name__iexact=serial)).first()
        if not legacy:
            return None
        return {
            "asset_id": None, "user_name": legacy.user_name, "device_type": "LAPTOP" if "laptop" in legacy.model.lower() else "PC",
            "model": legacy.model, "serial_number": legacy.serial_number, "computer_name": legacy.computer_name,
            "monitor_model": "", "monitor_serial": "", "printer_model": "", "printer_serial": "",
        }
    hr = (asset.hr_code or (asset.employee.hr_code if asset.employee_id else "")).strip()
    user_name = asset.display_employee_name
    related = Asset.objects.filter(hr_code__iexact=hr) if hr else Asset.objects.none()
    monitor = related.filter(asset_type=Asset.Types.MONITOR).exclude(asset_status=Asset.Status.SCRAPPED).first()
    printer = related.filter(asset_type=Asset.Types.PRINTER).exclude(asset_status=Asset.Status.SCRAPPED).first()
    typ = "LAPTOP" if "laptop" in (asset.item_type + " " + asset.model).lower() else "PC"
    return {
        "asset_id": asset.pk, "user_name": user_name, "device_type": typ,
        "model": asset.model or asset.item_type, "serial_number": asset.serial_number,
        "computer_name": asset.computer_name_new or asset.computer_name,
        "monitor_model": monitor.model if monitor else "",
        "monitor_serial": monitor.serial_number if monitor else "",
        "printer_model": printer.model if printer else "",
        "printer_serial": printer.serial_number if printer else "",
    }

@login_required
def visit_list(request):
    visits = Visit.objects.select_related("created_by").annotate(device_count=Count("items"))
    if not request.user.is_admin_role:
        visits = visits.filter(Q(created_by=request.user) | Q(status=Visit.Status.APPROVED))
    return render(request, "visits/list.html", {"visits": visits, "projects": _projects()})

@login_required
def visit_create(request):
    projects = _projects()
    if request.method == "POST":
        project = request.POST.get("project", "").strip()
        visit_date = request.POST.get("visit_date", "").strip()
        tech = request.POST.get("technician_name", "").strip()
        if project not in projects or not visit_date or not tech:
            messages.error(request, "اختار المشروع وتاريخ الزيارة واكتب اسم الفني.")
        else:
            visit = Visit.objects.create(project=project, visit_date=visit_date, technician_name=tech, created_by=request.user, updated_by=request.user)
            # Start every visit with the full project computer inventory. Technicians can still search
            # and add any additional asset not assigned to the project in the source data.
            project_assets = Asset.objects.filter(asset_type=Asset.Types.COMPUTER).exclude(
                asset_status=Asset.Status.SCRAPPED
            ).filter(Q(project__iexact=project) | Q(employee__project__iexact=project)).select_related("employee").distinct()
            seen = set()
            for asset in project_assets:
                data = _device_lookup(asset.serial_number) if asset.serial_number else None
                if not data:
                    data = {
                        "user_name": asset.display_employee_name,
                        "device_type": "LAPTOP" if "laptop" in (asset.item_type + " " + asset.model).lower() else "PC",
                        "model": asset.model or asset.item_type, "serial_number": asset.serial_number,
                        "computer_name": asset.computer_name_new or asset.computer_name,
                        "monitor_model": "", "monitor_serial": "", "printer_model": "", "printer_serial": "",
                    }
                hr = (asset.hr_code or (asset.employee.hr_code if asset.employee_id else "")).strip()
                related = Asset.objects.filter(hr_code__iexact=hr) if hr else Asset.objects.none()
                monitor = related.filter(asset_type=Asset.Types.MONITOR).exclude(asset_status=Asset.Status.SCRAPPED).first()
                printer = related.filter(asset_type=Asset.Types.PRINTER).exclude(asset_status=Asset.Status.SCRAPPED).first()
                key = asset.serial_number.strip().casefold() or f"asset-{asset.pk}"
                if key in seen:
                    continue
                seen.add(key)
                VisitItem.objects.create(
                    visit=visit, asset=asset, user_name=asset.display_employee_name,
                    device_type=data.get("device_type", ""), model=asset.model or asset.item_type,
                    serial_number=asset.serial_number, computer_name=asset.computer_name_new or asset.computer_name,
                    monitor_model=monitor.model if monitor else "", monitor_serial=monitor.serial_number if monitor else "",
                    printer_model=printer.model if printer else "", printer_serial=printer.serial_number if printer else "",
                )
            for legacy in Device.objects.filter(project__iexact=project):
                key = legacy.serial_number.strip().casefold() or f"legacy-{legacy.pk}"
                if key in seen:
                    continue
                seen.add(key)
                VisitItem.objects.create(
                    visit=visit, asset=None, user_name=legacy.user_name,
                    device_type="LAPTOP" if "laptop" in legacy.model.lower() else "PC",
                    model=legacy.model, serial_number=legacy.serial_number,
                    computer_name=legacy.computer_name,
                )
            log_event(request.user, "PROJECT_VISIT_CREATE", request, f"Created visit {visit.pk} for {project}; preloaded {len(seen)} project devices")
            return redirect("visit_detail", pk=visit.pk)
    return render(request, "visits/create.html", {"projects": projects, "today": timezone.localdate()})

@login_required
def project_dashboard(request):
    project = request.GET.get("project", "").strip()
    projects = _projects()
    visits = Visit.objects.all()
    if not request.user.is_admin_role:
        visits = visits.filter(Q(created_by=request.user) | Q(status=Visit.Status.APPROVED))
    if project:
        visits = visits.filter(project=project)
    visits = visits.annotate(device_count=Count("items"))
    visit_count = visits.count()
    approved_count = visits.filter(status=Visit.Status.APPROVED).count()
    if project:
        project_assets = Asset.objects.exclude(asset_type=Asset.Types.SCRAP).filter(Q(project__iexact=project) | Q(employee__project__iexact=project)).distinct()
        asset_count = project_assets.count()
    else:
        asset_count = Asset.objects.exclude(asset_type=Asset.Types.SCRAP).count()
    checked_count = VisitItem.objects.filter(visit__project=project).count() if project else VisitItem.objects.count()
    context = {
        "projects": projects, "selected_project": project, "visits": visits[:20],
        "visit_count": visit_count, "approved_count": approved_count,
        "checked_count": checked_count, "asset_count": asset_count,
    }
    return render(request, "visits/dashboard.html", context)

@login_required
def visit_detail(request, pk):
    visit = get_object_or_404(Visit.objects.select_related("created_by"), pk=pk)
    if not request.user.is_admin_role and visit.created_by_id != request.user.id and visit.status != Visit.Status.APPROVED:
        return HttpResponseForbidden("ليس لديك صلاحية عرض الزيارة.")
    can_edit = request.user.is_admin_role or visit.created_by_id == request.user.id
    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "update_visit":
            if not can_edit:
                return HttpResponseForbidden("ليس لديك صلاحية تعديل الزيارة.")
            project = request.POST.get("project", "").strip()
            visit_date = request.POST.get("visit_date", "").strip()
            tech = request.POST.get("technician_name", "").strip()
            if project not in _projects() or not visit_date or not tech:
                messages.error(request, "بيانات الزيارة غير مكتملة.")
            else:
                visit.project = project
                visit.visit_date = visit_date
                visit.technician_name = tech
                visit.updated_by = request.user
                visit.save(update_fields=["project", "visit_date", "technician_name", "updated_by", "updated_at"])
                log_event(request.user, "PROJECT_VISIT_EDIT", request, f"Updated visit {visit.pk}")
                messages.success(request, "تم تحديث بيانات الزيارة.")
            return redirect("visit_detail", pk=visit.pk)
        if action == "approve":
            if visit.status == Visit.Status.DRAFT:
                visit.status = Visit.Status.APPROVED
                visit.updated_by = request.user
                visit.save(update_fields=["status", "updated_by", "updated_at"])
                log_event(request.user, "PROJECT_VISIT_APPROVE", request, f"Approved visit {visit.pk}")
                messages.success(request, "تم اعتماد تسجيل الزيارة.")
            return redirect("visit_detail", pk=visit.pk)
        if action == "cancel":
            if visit.status != Visit.Status.CANCELLED:
                visit.status = Visit.Status.CANCELLED
                visit.updated_by = request.user
                visit.save(update_fields=["status", "updated_by", "updated_at"])
                log_event(request.user, "PROJECT_VISIT_CANCEL", request, f"Cancelled visit {visit.pk}")
                messages.success(request, "تم إلغاء تسجيل الزيارة.")
            return redirect("visit_detail", pk=visit.pk)
        if action == "delete":
            if not request.user.is_admin_role:
                return HttpResponseForbidden("حذف الزيارة متاح للـ Admin فقط.")
            visit_id, project = visit.pk, visit.project
            visit.delete()
            log_event(request.user, "PROJECT_VISIT_DELETE", request, f"Deleted visit {visit_id} for {project}")
            messages.success(request, "تم حذف الزيارة.")
            return redirect("visit_list")
        if action == "add_item":
            if not can_edit:
                return HttpResponseForbidden("ليس لديك صلاحية تعديل الزيارة.")
            serial = request.POST.get("serial_number", "").strip()
            data = _device_lookup(serial) if serial else None
            if not data:
                messages.error(request, "لم يتم العثور على جهاز بهذا السيريال أو اسم الكمبيوتر.")
            else:
                asset = Asset.objects.filter(pk=data.pop("asset_id")).first()
                if visit.items.filter(serial_number__iexact=data["serial_number"]).exists():
                    messages.warning(request, "الجهاز مسجل بالفعل في الزيارة.")
                else:
                    comments = []
                    for field, label in [("user_name","USER NAME"),("monitor_model","Monitor Model"),("monitor_serial","Monitor Serial"),("printer_model","Printer Model"),("printer_serial","Printer Serial")]:
                        changed = request.POST.get(field, data.get(field, "")).strip()
                        reason = request.POST.get(field + "_reason", "").strip()
                        original = data.get(field, "")
                        if changed != original:
                            if reason:
                                comments.append(f"{label} changed from '{original}' to '{changed}'. Reason: {reason}")
                            else:
                                comments.append(f"{label} changed from '{original}' to '{changed}'. Reason not provided.")
                        data[field] = changed
                    extra = request.POST.get("comments", "").strip()
                    if extra:
                        comments.append(extra)
                    VisitItem.objects.create(visit=visit, asset=asset, comments="\n".join(comments), **data)
                    visit.updated_by = request.user
                    visit.save(update_fields=["updated_by", "updated_at"])
                    log_event(request.user, "PROJECT_VISIT_ITEM_ADD", request, f"Added serial {serial} to visit {visit.pk}")
                    messages.success(request, "تمت إضافة الجهاز إلى شيت الفحص.")
            return redirect("visit_detail", pk=visit.pk)
        if action == "remove_item":
            if not can_edit:
                return HttpResponseForbidden("ليس لديك صلاحية تعديل الزيارة.")
            item = get_object_or_404(VisitItem, pk=request.POST.get("item_id"), visit=visit)
            item.delete()
            messages.success(request, "تم حذف الجهاز من شيت الزيارة.")
            return redirect("visit_detail", pk=visit.pk)
    query = request.GET.get("q", "").strip()
    items = visit.items.all()
    if query:
        items = items.filter(Q(serial_number__icontains=query) | Q(computer_name__icontains=query) | Q(user_name__icontains=query))
    return render(request, "visits/detail.html", {
        "visit": visit, "items": items, "query": query, "can_edit": can_edit, "visit_projects": _projects(),
        "is_admin": request.user.is_admin_role, "can_approve": request.user.is_admin_role or visit.created_by_id == request.user.id,
    })

@login_required
def lookup_device(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"found": False})
    data = _device_lookup(query)
    return JsonResponse({"found": bool(data), "device": data or {}})


@login_required
def visit_item_edit(request, pk, item_pk):
    visit = get_object_or_404(Visit, pk=pk)
    item = get_object_or_404(VisitItem, pk=item_pk, visit=visit)
    if not request.user.is_admin_role and visit.created_by_id != request.user.id:
        return HttpResponseForbidden("تعديل بيانات الفحص متاح لمنشئ الزيارة أو الـ Admin.")
    tracked = [
        ("user_name", "USER NAME"), ("monitor_model", "Monitor Model"),
        ("monitor_serial", "Monitor Serial"), ("printer_model", "printer model"),
        ("printer_serial", "printer serial"),
    ]
    if request.method == "POST":
        comments = []
        for field, label in tracked:
            old = getattr(item, field)
            new_value = request.POST.get(field, "").strip()
            reason = request.POST.get(field + "_reason", "").strip()
            if new_value != old:
                comments.append(f"{label} changed from '{old}' to '{new_value}'. Reason: {reason or 'Reason not provided.'}")
            setattr(item, field, new_value)
        for field in ("device_type", "model", "serial_number", "computer_name"):
            setattr(item, field, request.POST.get(field, "").strip())
        manual = request.POST.get("comments", "").strip()
        if manual:
            comments.append(manual)
        if comments:
            item.comments = "\n".join(filter(None, [item.comments, *comments]))
        item.save()
        visit.updated_by = request.user
        visit.save(update_fields=["updated_by", "updated_at"])
        log_event(request.user, "PROJECT_VISIT_ITEM_EDIT", request, f"Edited inspection row {item.pk} on visit {visit.pk}")
        messages.success(request, "تم حفظ تعديلات الجهاز داخل سجل الزيارة فقط.")
        return redirect("visit_detail", pk=visit.pk)
    return render(request, "visits/item_edit.html", {"visit": visit, "item": item})


@login_required
def visit_export(request, pk):
    from openpyxl import Workbook
    visit = get_object_or_404(Visit, pk=pk)
    if not request.user.is_admin_role and visit.created_by_id != request.user.id and visit.status != Visit.Status.APPROVED:
        return HttpResponseForbidden("ليس لديك صلاحية تصدير الزيارة.")
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Inspection"
    ws.append(["Project", "visit date", "IT TECH NAME", "USER NAME", "TYPE", "MODEL", "SERIAL NUMBER", "COMPUTER NAME", "Monitor Model", "Monitor Serial", "printer model", "printer serial", "COMMENTS"])
    for item in visit.items.all():
        ws.append([visit.project, visit.visit_date.isoformat(), visit.technician_name, item.user_name, item.device_type, item.model, item.serial_number, item.computer_name, item.monitor_model, item.monitor_serial, item.printer_model, item.printer_serial, item.comments])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col in ws.columns:
        letter = col[0].column_letter
        ws.column_dimensions[letter].width = min(max(max(len(str(c.value or "")) for c in col) + 2, 12), 45)
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    response = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="SIAC_Visit_{visit.pk}.xlsx"'
    log_event(request.user, "PROJECT_VISIT_EXPORT", request, f"Exported visit {visit.pk}")
    return response
