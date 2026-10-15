"""Import/export helpers for the multi-sheet SIAC inventory workbook."""
from __future__ import annotations

import io
import json
import math
import re
from datetime import date, datetime
from typing import Any

import pandas as pd
from django.db import transaction
from django.utils import timezone

from .models import Asset, Employee


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
        'model_keys': ['Model'], 'asset_tag_keys': ['Asset Number'], 'status': Asset.Status.ACTIVE,
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
    'name', 'arabic_name', 'company', 'project', 'sector', 'department', 'section',
    'unit', 'office', 'team', 'position', 'employment_status', 'termination_date', 'updated_at',
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


def import_inventory_workbook(uploaded_file):
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
        defaults = {
            'name': name,
            'arabic_name': clean_cell(row.get('Arabic Name')),
            'company': '',  # no personal or sensitive HR columns are imported
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
                Asset.objects.bulk_create(
                    pending_assets, batch_size=500, update_conflicts=True,
                    unique_fields=['source_sheet', 'source_row'], update_fields=ASSET_UPDATE_FIELDS,
                )
                assets_by_sheet[sheet_name] = len(pending_assets)
                created_or_updated_assets += len(pending_assets)

    return {
        'employees': len(employee_map),
        'assets': created_or_updated_assets,
        'by_sheet': assets_by_sheet,
    }
