from django import forms
from django.utils import timezone
from .models import Asset, AssetMovement, Employee


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label='ملف Excel', help_text='xlsx فقط')

    def clean_excel_file(self):
        f = self.cleaned_data['excel_file']
        if not f.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('يسمح بملفات XLSX فقط.')
        if f.size > 100 * 1024 * 1024:
            raise forms.ValidationError('حجم الملف يجب ألا يتجاوز 100 MB.')
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
        if f.size > 100 * 1024 * 1024:
            raise forms.ValidationError('حجم الملف يجب ألا يتجاوز 100 MB.')
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

    def clean(self):
        cleaned = super().clean()
        # New operational hardware must begin in stock or be linked to a known employee.
        # Once a record exists, custody/status changes are handled by the movement workflow.
        if not self.instance.pk:
            asset_type = cleaned.get('asset_type')
            asset_status = cleaned.get('asset_status')
            hr_code = (cleaned.get('hr_code') or '').strip()
            physical_types = {Asset.Types.COMPUTER, Asset.Types.PRINTER, Asset.Types.MONITOR, Asset.Types.GSTAR, Asset.Types.OTHER}
            if asset_type in physical_types:
                if asset_status == Asset.Status.IN_STOCK and hr_code:
                    self.add_error('hr_code', 'أصل المخزن يجب ألا يرتبط بموظف. احفظه في المخزن ثم سجّل حركة التسليم.')
                elif asset_status == Asset.Status.ACTIVE:
                    if not hr_code:
                        self.add_error('hr_code', 'للحالة «على عهدة موظف» أدخل HR Code، أو اختر «في المخزن».')
                    elif not Employee.objects.filter(hr_code__iexact=hr_code).exists():
                        self.add_error('hr_code', 'HR Code غير موجود. أضف الموظف أولًا أو احفظ الأصل في المخزن.')
                elif asset_status == Asset.Status.SCRAPPED:
                    if not (cleaned.get('scrap_number') or '').strip():
                        self.add_error('scrap_number', 'رقم محضر التخريد مطلوب.')
                    if not (cleaned.get('scrap_date') or '').strip():
                        self.add_error('scrap_date', 'تاريخ التخريد مطلوب.')
        return cleaned

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


class CustodyMovementForm(forms.Form):
    """Validated workflow for append-only custody movements on an existing asset."""
    ACTION_CHOICES = [
        (AssetMovement.EventTypes.ASSIGNED, 'تسليم من المخزون إلى موظف'),
        (AssetMovement.EventTypes.TRANSFERRED, 'نقل العهدة إلى موظف آخر'),
        (AssetMovement.EventTypes.RETURNED, 'إرجاع إلى المخزون'),
        (AssetMovement.EventTypes.SCRAPPED, 'تخريد الأصل'),
    ]

    event_type = forms.ChoiceField(label='نوع الحركة', choices=ACTION_CHOICES)
    target_hr_code = forms.CharField(
        label='HR Code للموظف الجديد', required=False, max_length=80,
        widget=forms.TextInput(attrs={'placeholder': 'مطلوب للتسليم أو نقل العهدة', 'autocomplete': 'off'}),
    )
    effective_date = forms.DateField(
        label='تاريخ الحركة', required=True, initial=timezone.localdate,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )
    reason = forms.CharField(
        label='سبب الحركة', required=True, max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'مثال: تسليم عهدة، نقل موظف، إرجاع للمخزون'}),
    )
    reference_number = forms.CharField(
        label='رقم المستند / التخريد', required=False, max_length=120,
        widget=forms.TextInput(attrs={'placeholder': 'رقم محضر التسليم أو التخريد إن وجد'}),
    )
    notes = forms.CharField(
        label='ملاحظات', required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'ملاحظات إضافية'}),
    )

    def __init__(self, *args, asset=None, **kwargs):
        self.asset = asset
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['target_hr_code'].help_text = 'اكتب HR Code مسجلًا في قاعدة بيانات الموظفين.'
        self.fields['effective_date'].help_text = 'تاريخ الحركة الفعلي؛ سيُحفظ في السجل التاريخي.'

    def clean_target_hr_code(self):
        return (self.cleaned_data.get('target_hr_code') or '').strip()

    def clean(self):
        cleaned = super().clean()
        if not self.asset:
            return cleaned

        action = cleaned.get('event_type')
        target_code = cleaned.get('target_hr_code', '')
        current_code = (self.asset.hr_code or '').strip()
        current_status = self.asset.asset_status
        is_assigned = bool(current_code) and current_status not in (Asset.Status.IN_STOCK, Asset.Status.SCRAPPED, Asset.Status.ARCHIVED)
        is_nonphysical_source_row = self.asset.asset_type in (
            Asset.Types.SCRAP, Asset.Types.NEW_2026, Asset.Types.REQUEST_2025,
        )

        if is_nonphysical_source_row:
            raise forms.ValidationError('هذا سجل مصدر/طلب وليس سجل أصل مادي قابلًا لنقل عهدته. اختَر الأصل الفعلي من شيت الأجهزة.')
        if current_status in (Asset.Status.SCRAPPED, Asset.Status.ARCHIVED):
            raise forms.ValidationError('لا يمكن إجراء حركة جديدة على أصل مخرد أو مؤرشف.')

        target_employee = None
        if action in (AssetMovement.EventTypes.ASSIGNED, AssetMovement.EventTypes.TRANSFERRED):
            if not target_code:
                self.add_error('target_hr_code', 'HR Code مطلوب لهذه الحركة.')
            else:
                target_employee = Employee.objects.filter(hr_code__iexact=target_code).first()
                if not target_employee:
                    self.add_error('target_hr_code', 'كود الموظف غير موجود في قائمة الموظفين.')
                elif target_employee.hr_code.casefold() == current_code.casefold():
                    self.add_error('target_hr_code', 'الموظف المحدد هو صاحب العهدة الحالي بالفعل.')
            if action == AssetMovement.EventTypes.ASSIGNED and is_assigned:
                self.add_error('event_type', 'الأصل على عهدة موظف بالفعل؛ استخدم حركة نقل العهدة.')
            if action == AssetMovement.EventTypes.TRANSFERRED and not is_assigned:
                self.add_error('event_type', 'لا يمكن نقل العهدة قبل تسليم الأصل لموظف.')
        elif action == AssetMovement.EventTypes.RETURNED:
            if not is_assigned:
                self.add_error('event_type', 'الأصل غير مسجل حاليًا على عهدة موظف.')
        elif action == AssetMovement.EventTypes.SCRAPPED:
            if not cleaned.get('reference_number'):
                self.add_error('reference_number', 'رقم محضر التخريد مطلوب لتسجيل التخريد.')
            if not cleaned.get('effective_date'):
                self.add_error('effective_date', 'تاريخ التخريد مطلوب.')
        else:
            self.add_error('event_type', 'نوع الحركة غير مدعوم.')

        cleaned['target_employee'] = target_employee
        return cleaned
