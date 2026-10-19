"""Import/export helpers for the multi-sheet SIAC inventory workbook."""
from __future__ import annotations

import io
import json
import math
import re
import uuid
from datetime import date, datetime
from typing import Any

import pandas as pd
from django.db import transaction
from django.utils import timezone

from .models import Asset, AssetMovement, Employee


SHEET_CONFIGS = {
    'all': {
        'asset_type': Asset.Types.COMPUTER,
        'hr_keys': ['Resolved HR ID', 'HR ID (clean)', 'HR Code'],
        'name_keys': ['English Nmae', 'Original Name'],
        'project_keys': ['Project', 'Original Project'],
        'sector_keys': ['Sector', 'Original Sector', 'Sector (from ID)'],
        'department_keys': ['Department', 'Original Department'],
        'serial_keys': ['Serial Number'],
        'computer_name_new_keys': ['Computer Name New'],
        'computer_name_keys': ['Computer Name'],
        'item_keys': ['Item'], 'brand_keys': ['Brand'], 'model_keys': ['Model'],
        'year_keys': ['manufacturing Year'], 'processor_keys': ['processor'],
        'ram_keys': ['ram'], 'storage_keys': ['hdd'], 'email_keys': ['Email'],
        'status': Asset.Status.ACTIVE,
    },
    'Printers 2027': {
        'asset_type': Asset.Types.PRINTER,
        'hr_keys': ['Resolved HR ID', 'HR ID (clean)', 'HR ID'],
        'name_keys': ['User Name', 'Name', 'Original Name'],
        'project_keys': ['Project', 'Original Project'],
        'sector_keys': ['Sector (from ID)'], 'department_keys': ['Department', 'Original Department'],
        'serial_keys': ['Serial Number'], 'item_keys': ['Machin Type'], 'brand_keys': ['Brand'],
        'model_keys': ['Model'], 'year_keys': ['manufacturing year'], 'toner_keys': ['Toner Code'],
        'status': Asset.Status.ACTIVE,
    },
    'Monitors 2': {
        'asset_type': Asset.Types.MONITOR,
        'hr_keys': ['Resolved HR ID', 'HR ID (clean)'],
        'name_keys': ['User Name', 'Username', 'Original Name'],
        'project_keys': ['Project', 'Original Project'],
        'sector_keys': ['Sector (from ID)'], 'department_keys': ['Department', 'Original Department'],
        'serial_keys': ['Serial'], 'item_keys': ['Size', 'Name'], 'brand_keys': ['Brand'],
        'model_keys': ['Model'], 'asset_tag_keys': ['Siac ID', 'Asset Number'], 'status': Asset.Status.ACTIVE,
    },
    'GStar': {
        'asset_type': Asset.Types.GSTAR,
        'hr_keys': ['Resolved HR ID', 'HR ID (clean)'],
        'name_keys': ['Name', 'Original Name'], 'project_keys': ['Location', 'Original Project'],
        'department_keys': ['Department', 'Original Department'], 'serial_keys': ['Computer SN'],
        'item_keys': ['Gstar PRO'], 'brand_keys': ['GStar CAD'], 'model_keys': ['Gstar PRO'],
        'email_keys': ['Email to send License'], 'license_version_keys': ['Version'],
        'license_activated_keys': ['Activated'], 'status': Asset.Status.ACTIVE,
    },
    'التعينات الجديدة 2026': {
        'asset_type': Asset.Types.NEW_2026,
        'hr_keys': ['Resolved HR ID', 'HR ID (clean)'],
        'name_keys': ['Name', 'Original Name'], 'department_keys': ['Department', 'Original Department'],
        'serial_keys': ['Serial Number'], 'item_keys': ['Type'], 'brand_keys': ['Brand'],
        'model_keys': ['Model'], 'purchase_date_keys': ['Date'], 'status': Asset.Status.ACTIVE,
    },
    'طلبات صرف وشراء 2025': {
        'asset_type': Asset.Types.REQUEST_2025,
        'hr_keys': ['Resolved HR ID', 'HR ID (clean)', 'SN'],
        'name_keys': ['Name', 'Original Name'], 'project_keys': ['Project', 'Original Project'],
        'serial_keys': ['Serial Number'], 'item_keys': ['Type'], 'brand_keys': ['Brand'],
        'model_keys': ['Model'], 'purchase_date_keys': ['Date'], 'status': Asset.Status.ACTIVE,
    },
    'Scraped': {
        'asset_type': Asset.Types.SCRAP,
        'hr_keys': [], 'name_keys': ['Username'], 'project_keys': ['Project'],
        'department_keys': ['Department'], 'computer_name_keys': ['Computer Name'],
        'serial_keys': ['Serial'], 'item_keys': ['Type'], 'brand_keys': ['Brand'],
        'model_keys': ['Model'], 'scrap_date_keys': ['تاريخ التخريد'],
        'scrap_number_keys': ['رقم التخريد'], 'status': Asset.Status.SCRAPPED,
    },
}

EMPLOYEE_UPDATE_FIELDS = [
    'name', 'arabic_name', 'company', 'cost_center', 'project', 'sector', 'department', 'section',
    'unit', 'office', 'team', 'position', 'employment_status', 'hiring_date', 'termination_date', 'updated_at',
]
ASSET_UPDATE_FIELDS = [
    'employee', 'hr_code', 'employee_name', 'asset_type', 'asset_status', 'company', 'project',
    'sector', 'department', 'computer_name_new', 'computer_name', 'item_type', 'brand', 'model',
    'serial_number', 'asset_tag', 'manufacturing_year', 'processor', 'ram', 'storage', 'email',
    'toner_code', 'license_version', 'license_activated', 'purchase_date', 'scrap_date',
    'scrap_number', 'notes', 'software_licenses', 'raw_data', 'updated_at',
]


def clean_cell(value: Any) -> str:
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()[:10]
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, (int,)):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return ''
        if value.is_integer():
            return str(int(value))
        return str(value).strip()
    text = str(value).strip()
    if text.endswith('.0') and text[:-2].isdigit():
        text = text[:-2]
    return text


def cell_data(value: Any):
    """JSON-safe source data: keep dates ISO-formatted and blank cells omitted."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return int(value) if isinstance(value, float) and value.is_integer() else value
    return str(value).strip()


def pick(row: dict, keys: list[str]) -> str:
    for key in keys:
        value = clean_cell(row.get(key))
        if value:
            return value
    return ''


def parse_date(value):
    if value is None or value == '':
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and 20000 < value < 80000:
        try:
            return (pd.Timestamp('1899-12-30') + pd.to_timedelta(float(value), unit='D')).date()
        except Exception:
            return None
    if isinstance(value, str) and value.strip().replace('.', '', 1).isdigit():
        try:
            serial = float(value.strip())
            if 20000 < serial < 80000:
                return (pd.Timestamp('1899-12-30') + pd.to_timedelta(serial, unit='D')).date()
        except Exception:
            pass
    try:
        if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}', value.strip()):
            parsed = pd.to_datetime(value, errors='coerce', format='mixed')
        else:
            parsed = pd.to_datetime(value, errors='coerce', dayfirst=True)
        return None if pd.isna(parsed) else parsed.date()
    except Exception:
        return None


def _dataframe(excel_file, sheet_name):
    if sheet_name not in excel_file.sheet_names:
        return None
    df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=object)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _match_employee_code(row, config, employee_by_code, employee_by_name):
    raw_codes = [clean_cell(row.get(key)) for key in config.get('hr_keys', [])]
    raw_codes = [code for code in raw_codes if code]
    for code in raw_codes:
        if code.casefold() in employee_by_code:
            return employee_by_code[code.casefold()].hr_code
    name = pick(row, config.get('name_keys', []))
    employee = employee_by_name.get(name.casefold()) if name else None
    if employee:
        return employee.hr_code
    return raw_codes[-1] if raw_codes else ''


def preview_inventory_workbook(uploaded_file):
    """Count employee/asset rows that the importer will recognize, without saving data."""
    content = uploaded_file.read()
    uploaded_file.seek(0)
    excel = pd.ExcelFile(io.BytesIO(content), engine='openpyxl')
    required = {'ID', 'all'}
    if not required.issubset(set(excel.sheet_names)):
        raise ValueError('الملف لا يحتوي على الشيتين المطلوبين ID و all.')

    employee_df = _dataframe(excel, 'ID')
    employee_codes = set()
    for row in employee_df.to_dict('records'):
        code = clean_cell(row.get('Employee Code'))
        name = clean_cell(row.get('Employee Name'))
        if code and name:
            employee_codes.add(code)
    employees = len(employee_codes)

    assets_by_sheet = {}
    for sheet_name, config in SHEET_CONFIGS.items():
        df = _dataframe(excel, sheet_name)
        if df is None:
            continue
        count = 0
        for raw_row in df.to_dict('records'):
            row = {str(k).strip(): v for k, v in raw_row.items()}
            keys = (config.get('serial_keys', []) + config.get('model_keys', []) +
                    config.get('item_keys', []) + config.get('brand_keys', []) +
                    config.get('computer_name_new_keys', []) + config.get('computer_name_keys', []) +
                    config.get('asset_tag_keys', []) + config.get('license_version_keys', []) +
                    config.get('toner_keys', []))
            if pick(row, keys):
                count += 1
        if count:
            assets_by_sheet[sheet_name] = count

    return {
        'file_name': getattr(uploaded_file, 'name', 'inventory.xlsx'),
        'employees': employees,
        'assets': assets_by_sheet,
        'total_assets': sum(assets_by_sheet.values()),
        'sheets_found': list(excel.sheet_names),
    }


def import_inventory_workbook(uploaded_file, actor=None):
    """Import the inventory workbook without deleting manual records or unrelated data.

    Employees are upserted by HR Code. Imported assets are upserted by source sheet and
    source row, so uploading an updated workbook refreshes those imported rows while
    manually entered rows (which have no source row) remain untouched.
    """
    content = uploaded_file.read()
    uploaded_file.seek(0)
    excel = pd.ExcelFile(io.BytesIO(content), engine='openpyxl')
    required = {'ID', 'all'}
    if not required.issubset(set(excel.sheet_names)):
        raise ValueError('الملف لا يحتوي على الشيتين المطلوبين ID و all.')

    employee_df = _dataframe(excel, 'ID')
    employee_map = {}
    for row in employee_df.to_dict('records'):
        code = clean_cell(row.get('Employee Code'))
        name = clean_cell(row.get('Employee Name'))
        if not code or not name:
            continue
        termination_date = parse_date(row.get('Termination Date'))
        hiring_date = parse_date(row.get('Hiring Date')) or parse_date(row.get('Employment Date')) or parse_date(row.get('Contract Start Date'))
        defaults = {
            'name': name,
            'arabic_name': clean_cell(row.get('Arabic Name')),
            'company': '',  # no personal or sensitive HR columns are imported
            'cost_center': clean_cell(row.get('Cost Center')),
            'hiring_date': hiring_date,
            'project': clean_cell(row.get('Site')),
            'sector': clean_cell(row.get('Sector')),
            'department': clean_cell(row.get('Department')),
            'section': clean_cell(row.get('Section')),
            'unit': clean_cell(row.get('Unit')),
            'office': clean_cell(row.get('Office')),
            'team': clean_cell(row.get('Team')),
            'position': clean_cell(row.get('Position')),
            'employment_status': 'Terminated' if termination_date else 'Active',
            'termination_date': termination_date,
            'updated_at': timezone.now(),
        }
        employee_map[code] = defaults  # deduplicate same HR Code inside the source file

    if not employee_map:
        raise ValueError('لم يتم العثور على موظفين لديهم Employee Code وEmployee Name.')

    with transaction.atomic():
        import_changes = []
        employee_objects = [Employee(hr_code=code, **defaults) for code, defaults in employee_map.items()]
        Employee.objects.bulk_create(
            employee_objects, batch_size=500, update_conflicts=True,
            unique_fields=['hr_code'], update_fields=EMPLOYEE_UPDATE_FIELDS,
        )
        employees = Employee.objects.filter(hr_code__in=list(employee_map.keys()))
        employee_by_code = {e.hr_code.casefold(): e for e in employees}
        employee_by_name = {}
        for e in employees:
            if e.name:
                employee_by_name.setdefault(e.name.casefold(), e)
            if e.arabic_name:
                employee_by_name.setdefault(e.arabic_name.casefold(), e)

        created_or_updated_assets = 0
        assets_by_sheet = {}
        for sheet_name, config in SHEET_CONFIGS.items():
            df = _dataframe(excel, sheet_name)
            if df is None:
                continue
            pending_assets = []
            for idx, raw_row in enumerate(df.to_dict('records'), start=2):
                row = {str(k).strip(): v for k, v in raw_row.items()}
                serial = pick(row, config.get('serial_keys', []))
                model = pick(row, config.get('model_keys', []))
                item_type = pick(row, config.get('item_keys', []))
                brand = pick(row, config.get('brand_keys', []))
                computer_new = pick(row, config.get('computer_name_new_keys', []))
                computer = pick(row, config.get('computer_name_keys', []))
                asset_tag = pick(row, config.get('asset_tag_keys', []))
                license_version = pick(row, config.get('license_version_keys', []))
                toner = pick(row, config.get('toner_keys', []))
                if not any([serial, model, item_type, brand, computer_new, computer, asset_tag, license_version, toner]):
                    continue

                hr_code = _match_employee_code(row, config, employee_by_code, employee_by_name)
                employee = employee_by_code.get(hr_code.casefold()) if hr_code else None
                employee_name = pick(row, config.get('name_keys', []))
                if not employee_name and employee:
                    employee_name = employee.name
                raw = {str(k): cell_data(v) for k, v in row.items() if cell_data(v) not in (None, '')}
                software_keys = [k for k in ['Manage Engine', 'Kaspersky', 'windows', 'windows ', 'office', 'adobe pro', 'Gstar CAD', 'AutoDeks', 'civel 3d', 'primavera', 'sap'] if clean_cell(row.get(k))]
                software = {k: clean_cell(row.get(k)) for k in software_keys}
                purchase_date = parse_date(pick(row, config.get('purchase_date_keys', []))) if config.get('purchase_date_keys') else None
                status = config.get('status', Asset.Status.ACTIVE)
                pending_assets.append(Asset(
                    employee=employee,
                    hr_code=hr_code,
                    employee_name=employee_name,
                    asset_type=config['asset_type'],
                    asset_status=status,
                    source_sheet=sheet_name,
                    source_row=idx,
                    company=pick(row, ['Company']),
                    project=pick(row, config.get('project_keys', [])),
                    sector=pick(row, config.get('sector_keys', [])),
                    department=pick(row, config.get('department_keys', [])),
                    computer_name_new=computer_new,
                    computer_name=computer,
                    item_type=item_type,
                    brand=brand,
                    model=model,
                    serial_number=serial,
                    asset_tag=asset_tag,
                    manufacturing_year=pick(row, config.get('year_keys', [])),
                    processor=pick(row, config.get('processor_keys', [])),
                    ram=pick(row, config.get('ram_keys', [])),
                    storage=pick(row, config.get('storage_keys', [])),
                    email=pick(row, config.get('email_keys', []))[:254],
                    toner_code=toner,
                    license_version=license_version,
                    license_activated=pick(row, config.get('license_activated_keys', [])),
                    purchase_date=purchase_date,
                    scrap_date=pick(row, config.get('scrap_date_keys', [])),
                    scrap_number=pick(row, config.get('scrap_number_keys', [])),
                    software_licenses=software,
                    raw_data=raw,
                    updated_at=timezone.now(),
                ))
            if pending_assets:
                source_rows = [asset.source_row for asset in pending_assets]
                existing_by_row = {
                    item.source_row: item
                    for item in Asset.objects.filter(source_sheet=sheet_name, source_row__in=source_rows).select_related('employee')
                }
                for desired in pending_assets:
                    previous = existing_by_row.get(desired.source_row)
                    if not previous:
                        continue
                    old_hr = (previous.hr_code or '').strip().casefold()
                    new_hr = (desired.hr_code or '').strip().casefold()
                    if old_hr != new_hr or previous.asset_status != desired.asset_status:
                        import_changes.append({
                            'source_sheet': sheet_name,
                            'source_row': desired.source_row,
                            'from_employee': previous.employee if previous.employee_id else None,
                            'from_hr_code': previous.hr_code,
                            'from_employee_name': previous.employee.name if previous.employee_id else previous.employee_name,
                            'from_status': previous.asset_status,
                            'old_hr_code': previous.hr_code,
                            'old_status': previous.asset_status,
                        })
                Asset.objects.bulk_create(
                    pending_assets, batch_size=500, update_conflicts=True,
                    unique_fields=['source_sheet', 'source_row'], update_fields=ASSET_UPDATE_FIELDS,
                )
                assets_by_sheet[sheet_name] = len(pending_assets)
                created_or_updated_assets += len(pending_assets)

        # If a physical serial exists in the Scraped sheet, reconcile matching hardware
        # inventory rows to SCRAPPED so they do not remain in active custody counts.
        # Keep this bulk-oriented: the workbook has hundreds of scrap rows, and a
        # per-row get_or_create can exceed Gunicorn's request timeout on PostgreSQL.
        hardware_types = [Asset.Types.COMPUTER, Asset.Types.PRINTER, Asset.Types.MONITOR, Asset.Types.OTHER]
        scraped_rows = list(
            Asset.objects.filter(source_sheet='Scraped').exclude(serial_number='').select_related('employee')
        )
        physical_candidates = list(
            Asset.objects.filter(asset_type__in=hardware_types)
            .exclude(serial_number='')
            .select_related('employee')
        )
        physical_by_serial = {}
        for physical_item in physical_candidates:
            physical_by_serial.setdefault(physical_item.serial_number.casefold(), []).append(physical_item)

        linked_scrap_ids = set()
        physical_updates = {}
        scrap_link_events = []
        existing_scrap_link_keys = set(
            AssetMovement.objects.filter(source_event_key__startswith='scrap-link:')
            .values_list('source_event_key', flat=True)
        )
        for scrap in scraped_rows:
            candidates = [
                candidate
                for candidate in physical_by_serial.get(scrap.serial_number.casefold(), [])
                if candidate.pk != scrap.pk
            ]
            if not candidates:
                continue
            linked_scrap_ids.add(scrap.pk)
            for physical in candidates:
                previous_status = physical.asset_status
                # Prefer the last holder recorded in Scraped; if not linkable, preserve a known holder.
                from_employee = scrap.employee if scrap.employee_id else (
                    physical.employee if physical.employee_id and not scrap.employee_name else None
                )
                from_hr_code = scrap.hr_code or (physical.hr_code if not scrap.employee_name else '')
                from_name = scrap.employee.name if scrap.employee_id else (scrap.employee_name or physical.employee_name)

                physical.asset_status = Asset.Status.SCRAPPED
                physical.scrap_date = scrap.scrap_date or physical.scrap_date
                physical.scrap_number = scrap.scrap_number or physical.scrap_number
                physical.updated_at = timezone.now()
                physical_updates[physical.pk] = physical

                # One stable link event per matching source scrap row, idempotent on re-import.
                event_key = f'scrap-link:{physical.pk}:{scrap.pk}'
                if event_key in existing_scrap_link_keys:
                    continue
                existing_scrap_link_keys.add(event_key)
                scrap_link_events.append(AssetMovement(
                    asset=physical,
                    event_type=AssetMovement.EventTypes.SCRAPPED,
                    effective_date=parse_date(scrap.scrap_date),
                    from_employee=from_employee,
                    to_employee=None,
                    from_hr_code=from_hr_code or '',
                    from_employee_name=from_name or '',
                    to_hr_code='',
                    to_employee_name='التخريد',
                    from_status=previous_status,
                    to_status=Asset.Status.SCRAPPED,
                    reason='تخريد وارد في الشيت المرجعي Scraped',
                    reference_number=scrap.scrap_number or '',
                    notes='تم الربط بالسيريال نمبر المطابق بين سجل الأصل وشيت Scraped. الملف لا يتضمن بالضرورة جميع الحركات السابقة.',
                    source_sheet='Scraped',
                    source_row=scrap.source_row,
                    source_event_key=event_key,
                    created_by=actor,
                ))

        if physical_updates:
            Asset.objects.bulk_update(
                list(physical_updates.values()),
                ['asset_status', 'scrap_date', 'scrap_number', 'updated_at'],
                batch_size=500,
            )
        if scrap_link_events:
            AssetMovement.objects.bulk_create(
                scrap_link_events, batch_size=500, ignore_conflicts=True,
            )

        # Record detected custody/status changes across subsequent workbook imports.
        for change in import_changes:
            saved = Asset.objects.filter(source_sheet=change['source_sheet'], source_row=change['source_row']).select_related('employee').first()
            if not saved:
                continue
            old_hr = (change['old_hr_code'] or '').strip().casefold()
            new_hr = (saved.hr_code or '').strip().casefold()
            old_status = change['old_status']
            # Reconciliation may restore the same already-scrapped state from Scraped.
            if old_hr == new_hr and old_status == saved.asset_status:
                continue
            if saved.asset_status == Asset.Status.SCRAPPED and old_status != Asset.Status.SCRAPPED:
                event_type = AssetMovement.EventTypes.SCRAPPED
                to_employee, to_hr, to_name = None, '', 'التخريد'
            elif old_hr != new_hr:
                if old_hr and new_hr:
                    event_type = AssetMovement.EventTypes.TRANSFERRED
                elif new_hr:
                    event_type = AssetMovement.EventTypes.ASSIGNED
                else:
                    event_type = AssetMovement.EventTypes.RETURNED
                to_employee, to_hr = saved.employee if saved.employee_id else None, saved.hr_code
                to_name = saved.employee.name if saved.employee_id else saved.employee_name
            else:
                event_type = AssetMovement.EventTypes.STATUS_CHANGED
                to_employee, to_hr = saved.employee if saved.employee_id else None, saved.hr_code
                to_name = saved.employee.name if saved.employee_id else saved.employee_name
            key = f"source-change:{change['source_sheet']}:{change['source_row']}:{uuid.uuid4().hex}"
            AssetMovement.objects.create(
                asset=saved, event_type=event_type, effective_date=timezone.localdate(),
                from_employee=change['from_employee'], to_employee=to_employee,
                from_hr_code=change['from_hr_code'] or '', from_employee_name=change['from_employee_name'] or '',
                to_hr_code=to_hr or '', to_employee_name=to_name or ('التخريد' if event_type == AssetMovement.EventTypes.SCRAPPED else 'المخزون'),
                from_status=old_status or '', to_status=saved.asset_status,
                reason='تغيير اكتُشف عند تحديث الملف المرجعي',
                notes='تاريخ الحركة الأصلي غير موجود في الملف؛ التاريخ المسجل هنا هو تاريخ اكتشاف التغيير عند الاستيراد.',
                source_sheet=change['source_sheet'], source_row=change['source_row'],
                source_event_key=key, created_by=actor,
            )

        # Seed exactly one truthful baseline entry per imported row. These describe the
        # source's known state, not invented historical transfer dates.
        all_source_assets = list(Asset.objects.filter(source_sheet__in=list(SHEET_CONFIGS), source_row__isnull=False).select_related('employee'))
        existing_baseline_keys = set(AssetMovement.objects.filter(
            source_event_key__startswith='baseline:'
        ).values_list('source_event_key', flat=True))
        already_scrapped_asset_ids = set(AssetMovement.objects.filter(
            event_type=AssetMovement.EventTypes.SCRAPPED
        ).values_list('asset_id', flat=True))
        baseline_events = []
        for asset in all_source_assets:
            if asset.source_sheet == 'Scraped' and asset.pk in linked_scrap_ids:
                # The linked hardware record carries the authoritative scrap event.
                continue
            baseline_key = f'baseline:{asset.source_sheet}:{asset.source_row}'
            if baseline_key in existing_baseline_keys:
                continue
            baseline_to_status = asset.asset_status
            if asset.asset_status == Asset.Status.SCRAPPED and asset.pk in already_scrapped_asset_ids:
                if asset.source_sheet != 'Scraped':
                    baseline_to_status = Asset.Status.ACTIVE
                # The asset has a linked scrap event; retain its source-sheet owner snapshot too.
                if not asset.hr_code:
                    event_type = AssetMovement.EventTypes.ADDED_TO_STOCK
                    from_hr, from_name, from_employee = '', 'الملف المرجعي', None
                    to_hr, to_name, to_employee = '', 'المخزون', None
                else:
                    event_type = AssetMovement.EventTypes.SOURCE_STATE
                    from_hr, from_name, from_employee = '', 'الملف المرجعي', None
                    to_hr = asset.hr_code
                    to_name = asset.employee.name if asset.employee_id else asset.employee_name or asset.hr_code
                    to_employee = asset.employee if asset.employee_id else None
                effective_date = None
                reason = 'الحالة المسجلة في شيت المصدر قبل ربط سجل التخريد'
                notes = 'هذه لقطة من بيانات الشيت المصدر وليست تاريخ تسليم مؤكدًا؛ سجل التخريد المنفصل يحتوي على التاريخ المتاح.'
            elif asset.asset_status == Asset.Status.SCRAPPED:
                event_type = AssetMovement.EventTypes.SCRAPPED
                from_hr = asset.hr_code
                from_name = asset.employee.name if asset.employee_id else asset.employee_name
                to_hr, to_name, from_employee, to_employee = '', 'التخريد', asset.employee if asset.employee_id else None, None
                effective_date = parse_date(asset.scrap_date)
                reason = 'حالة تخريد كما وردت في الملف المرجعي'
                notes = 'تم نقل حالة التخريد المتاحة في المصدر. سجل التنقلات الأقدم لا يتوفر إلا إذا كان موثقًا في الملف.'
            elif asset.hr_code:
                event_type = AssetMovement.EventTypes.SOURCE_STATE
                from_hr, from_name, from_employee = '', 'الملف المرجعي', None
                to_hr = asset.hr_code
                to_name = asset.employee.name if asset.employee_id else asset.employee_name or asset.hr_code
                to_employee = asset.employee if asset.employee_id else None
                effective_date = None
                reason = 'حالة العهدة كما وردت في الملف المرجعي'
                notes = 'تاريخ التسليم الأصلي غير متوفر في الملف؛ هذا سجل للحالة المعروفة وقت الاستيراد وليس تاريخ حركة مخترعًا.'
            else:
                event_type = AssetMovement.EventTypes.ADDED_TO_STOCK
                from_hr, from_name, from_employee = '', 'الملف المرجعي', None
                to_hr, to_name, to_employee = '', 'المخزون', None
                effective_date = None
                reason = 'أصل مسجل في الملف المرجعي دون HR Code مطابق'
                notes = 'لا يوجد موظف مؤكد مرتبط بالسجل في المصدر وقت الاستيراد.'
            baseline_events.append(AssetMovement(
                asset=asset, event_type=event_type, effective_date=effective_date,
                from_employee=from_employee, to_employee=to_employee,
                from_hr_code=from_hr or '', from_employee_name=from_name or '',
                to_hr_code=to_hr or '', to_employee_name=to_name or '',
                from_status='', to_status=baseline_to_status,
                reason=reason, reference_number=asset.scrap_number or '', notes=notes,
                source_sheet=asset.source_sheet, source_row=asset.source_row,
                source_event_key=baseline_key, created_by=actor,
            ))
        if baseline_events:
            AssetMovement.objects.bulk_create(baseline_events, batch_size=500, ignore_conflicts=True)

    return {
        'employees': len(employee_map),
        'assets': created_or_updated_assets,
        'by_sheet': assets_by_sheet,
    }
