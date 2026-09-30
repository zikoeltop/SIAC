import io, os, re
import pandas as pd
from django.conf import settings
from django.db import transaction
from django.utils.text import get_valid_filename
from .models import Device, DeviceImport, PendingExcelImport

COLUMN_MAP = {
    'Serial Number': 'serial_number',
    'English Nmae': 'user_name',
    'Project': 'project',
    'Model': 'model',
    'processor': 'processor',
    'ram': 'ram',
    'Computer Name': 'computer_name',
    'hdd': 'hdd',
}

def clean_value(value):
    if value is None or pd.isna(value): return ''
    return str(value).strip()

def read_excel_preview(uploaded_file):
    data = uploaded_file.read()
    df = pd.read_excel(io.BytesIO(data), engine='openpyxl')
    df.columns = [str(c).strip() for c in df.columns]
    if 'Serial Number' not in df.columns:
        raise ValueError('الملف يجب أن يحتوي على عمود Serial Number.')

    original_rows = len(df)
    df['Serial Number'] = df['Serial Number'].apply(normalize_serial).str.replace(r'\.0$', '', regex=True)
    df = df[df['Serial Number'] != ''].copy()
    duplicate_mask = df['Serial Number'].duplicated(keep='first')
    duplicate_rows = int(duplicate_mask.sum())
    df = df.drop_duplicates(subset=['Serial Number'], keep='first')

    # Convert NaN/unsupported values to display-safe strings.
    preview_df = df.head(25).fillna('')
    preview_rows = []
    for _, row in preview_df.iterrows():
        preview_rows.append({str(k): clean_value(v) for k, v in row.items()})

    return {
        'data': data,
        'total_rows': original_rows,
        'valid_rows': len(df),
        'duplicate_rows': duplicate_rows,
        'columns': list(df.columns),
        'preview_rows': preview_rows,
    }

def create_pending_import(uploaded_file, user):
    info = read_excel_preview(uploaded_file)
    uploaded_file.seek(0)
    pending = PendingExcelImport.objects.create(
        file=uploaded_file,
        uploaded_by=user,
        total_rows=info['total_rows'],
        valid_rows=info['valid_rows'],
        duplicate_rows=info['duplicate_rows'],
        columns=info['columns'],
        preview_rows=info['preview_rows'],
    )
    return pending

def import_excel(uploaded_file, user):
    info = read_excel_preview(uploaded_file)
    df = pd.read_excel(io.BytesIO(info['data']), engine='openpyxl')
    df.columns = [str(c).strip() for c in df.columns]
    df['Serial Number'] = df['Serial Number'].apply(normalize_serial).str.replace(r'\.0$', '', regex=True)
    df = df[df['Serial Number'] != ''].drop_duplicates(subset=['Serial Number'], keep='first')

    with transaction.atomic():
        Device.objects.all().delete()
        objs = []
        for _, row in df.iterrows():
            serial = clean_value(row.get('Serial Number'))
            raw = {str(k): clean_value(v) for k, v in row.items()}
            kwargs = {'serial_number': serial, 'raw_data': raw}
            for excel_col, model_field in COLUMN_MAP.items():
                kwargs[model_field] = clean_value(row.get(excel_col, ''))
            objs.append(Device(**kwargs))
        Device.objects.bulk_create(objs, batch_size=1000)
        DeviceImport.objects.update(is_current=False)
        uploaded_file.seek(0)
        instance = DeviceImport.objects.create(file=uploaded_file, uploaded_by=user, rows_imported=len(objs), is_current=True)
    return len(objs), instance, info

def normalize_serial(value):
    return str(value or '').strip()
