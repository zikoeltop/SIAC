# SIAC Device Inspection Web System

نظام Django لإدارة بيانات الأجهزة واستخراج تقارير PDF.

## الوظائف
- Login آمن باستخدام Django Authentication.
- Roles: Admin / User.
- Excel ثابت: الـAdmin يرفع XLSX مرة واحدة ويتم استيراده إلى Database.
- User يبحث بالـSerial Number ويحمّل PDF فقط.
- Admin يستطيع إضافة/تعديل/تعطيل/حذف المستخدمين.
- كل مستخدم يستطيع تغيير كلمة مروره.
- Admin يستطيع Reset كلمة مرور أي مستخدم.
- Audit Log للـLogin/Logout/بحث/PDF/Excel/إدارة المستخدمين وكلمات المرور.
- SQLite افتراضياً، ويمكن نقل قاعدة البيانات إلى PostgreSQL.

## التشغيل على Windows
```powershell
cd siac_django
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py manage.py migrate
py manage.py createsuperuser
py manage.py runserver
```

افتح:
http://127.0.0.1:8000/

> حساب superuser يُعامل كـAdmin داخل النظام.

## أول استخدام
1. ادخل بحساب Admin.
2. من "إدارة Excel" ارفع ملف الأجهزة XLSX.
3. البيانات ستُستورد إلى قاعدة البيانات.
4. أضف المستخدمين من "المستخدمون" واختر User.
5. المستخدم العادي يدخل ويبحث فقط.

## الأعمدة المدعومة من Excel
- Serial Number (إجباري)
- English Nmae
- Project
- Model
- processor
- ram
- Computer Name
- hdd

الأعمدة الأخرى يتم الاحتفاظ بها داخل `raw_data` ويمكن استخدامها لاحقاً.

## ملاحظة مهمة للإنتاج
غيّر `DJANGO_SECRET_KEY`، عطّل DEBUG، واضبط `DJANGO_ALLOWED_HOSTS`. استخدم HTTPS، ويفضل PostgreSQL على سيرفر الشركة.


## Excel Preview Workflow

رفع Excel من لوحة Admin أصبح على مرحلتين:
1. اختر الملف واضغط `عرض Preview`.
2. راجع عدد الصفوف، التكرارات، الأعمدة، وأول 25 صفاً.
3. اضغط `اعتماد الملف واستبدال البيانات` لتحديث قاعدة البيانات.

التكرارات في Serial Number داخل نفس الملف لا توقف الاستيراد؛ يتم الاحتفاظ بأول ظهور لكل Serial مع إظهار عدد التكرارات في الـPreview.
