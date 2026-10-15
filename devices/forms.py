from django import forms
from django.utils import timezone
from .models import Asset, Employee


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label='ملف Excel', help_text='xlsx فقط')

    def clean_excel_file(self):
        f = self.cleaned_data['excel_file']
        if not f.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('يسمح بملفات XLSX فقط.')
        if f.size > 25 * 1024 * 1024:
            raise forms.ValidationError('حجم الملف يجب ألا يتجاوز 25 MB.')
        return f


class InventoryWorkbookImportForm(forms.Form):
    workbook = forms.FileField(
        label='ملف المخزون المرجعي',
        help_text='اختر ملف inventory_2027_linked بصيغة XLSX. سيتم تحديث السجلات المستوردة من نفس الشيت وإضافة الجديد دون حذف الإدخالات اليدوية.',
    )

    def clean_workbook(self):
        f = self.cleaned_data['workbook']
        if not f.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('يسمح بملفات XLSX فقط.')
        if f.size > 25 * 1024 * 1024:
            raise forms.ValidationError('حجم الملف يجب ألا يتجاوز 25 MB.')
        return f


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'hr_code', 'name', 'arabic_name', 'company', 'cost_center', 'project', 'sector',
            'department', 'section', 'unit', 'office', 'team', 'position',
            'employment_status', 'hiring_date', 'termination_date',
        ]
        widgets = {
            'hiring_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'termination_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'arabic_name': forms.TextInput(attrs={'dir': 'rtl'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hr_code'].help_text = 'الكود الوظيفي المستخدم للربط مع العهدة.'
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_hr_code(self):
        return str(self.cleaned_data['hr_code']).strip()


class AssetForm(forms.ModelForm):
    movement_date = forms.DateField(
        label='تاريخ الحركة', required=False, initial=timezone.localdate,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        help_text='يُستخدم عند إضافة أصل أو تغيير الموظف/الحالة؛ اتركه فارغًا لاستخدام تاريخ اليوم.',
    )
    movement_reason = forms.CharField(
        label='سبب الحركة / ملاحظات السجل', required=False, max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'مثال: تسليم عهدة / نقل موظف / تخريد'}),
        help_text='يُحفظ مع سجل الحركة إذا تغير الموظف أو الحالة.',
    )

    class Meta:
        model = Asset
        fields = [
            'asset_type', 'asset_status', 'hr_code', 'employee_name', 'company',
            'project', 'sector', 'department', 'computer_name_new', 'computer_name',
            'item_type', 'brand', 'model', 'serial_number', 'asset_tag',
            'manufacturing_year', 'processor', 'ram', 'storage', 'email',
            'toner_code', 'license_version', 'license_activated', 'purchase_date',
            'scrap_date', 'scrap_number', 'notes',
        ]
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['serial_number'].help_text = 'قد يتكرر السيريال في الشيتات المصدر؛ كل سجل أصل يظل مستقلًا.'
        self.fields['hr_code'].help_text = 'إذا كان موجودًا في قائمة الموظفين ستُربط العهدة به تلقائيًا.'

    def clean_hr_code(self):
        return str(self.cleaned_data.get('hr_code') or '').strip()

    def save(self, commit=True):
        asset = super().save(commit=False)
        if not asset.pk:
            asset.source_sheet = 'manual'
            asset.source_row = None
        employee = Employee.objects.filter(hr_code__iexact=asset.hr_code).first() if asset.hr_code else None
        asset.employee = employee
        if employee:
            if not asset.employee_name:
                asset.employee_name = employee.name
            if not asset.project:
                asset.project = employee.project
            if not asset.sector:
                asset.sector = employee.sector
            if not asset.department:
                asset.department = employee.department
        if commit:
            asset.save()
            self.save_m2m()
        return asset
