from django import forms
class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label='ملف Excel', help_text='xlsx فقط')
    def clean_excel_file(self):
        f = self.cleaned_data['excel_file']
        if not f.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('يسمح بملفات XLSX فقط.')
        if f.size > 20 * 1024 * 1024:
            raise forms.ValidationError('حجم الملف يجب ألا يتجاوز 20 MB.')
        return f
