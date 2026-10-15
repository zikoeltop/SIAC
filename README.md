# SIAC IT Asset & Custody System

نظام Django لإدارة أصول تكنولوجيا المعلومات وعهد الموظفين، مع البحث برقم Serial Number أو HR Code، وإنشاء PDF لبيان عهدة الموظف.

## الوظائف
- تسجيل دخول وصلاحيات Admin / User.
- البحث للمستخدمين المسجلين فقط عبر `Serial Number` أو `HR Code`.
- توليد تقرير عهدة PDF من صفحة واحدة بشعار SIAC، وبيانات الموظف والأصول النشطة، ومساحة ملاحظات فارغة، وحقول تاريخ التقرير ومسؤول الدعم الفني وتوقيع المستخدم. يستبعد التقرير ملخص العهدة وشيتَي طلبات 2025 والتعيينات 2026.
- Admin فقط: إضافة وتعديل الموظفين والأصول.
- Admin فقط: استيراد ملف المخزون متعدد الشيتات (ID، all، Printers 2027، Monitors 2، GStar، التعيينات الجديدة 2026، طلبات صرف وشراء 2025، Scraped).
- Admin فقط: تصدير قاعدة بيانات النظام إلى XLSX، مع سجل موحّد للأصول وتبويبات مصدر تحفظ البيانات الإضافية، بالإضافة إلى تبويب Movement History.
- سجل حركة مستمر لكل أصل: التسليم، النقل بين الموظفين، الإرجاع للمخزون، والتخريد؛ يظهر للأدمن والمستخدم العادي عند البحث، ويُسجل تاريخ الحركة وسببها ومن/إلى.
- إدارة المستخدمين وتغيير/إعادة تعيين كلمات المرور وسجل العمليات Audit Log.
- قاعدة بيانات PostgreSQL عبر `DATABASE_URL` عند توفره، مع SQLite للتشغيل المحلي.

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

افتح `http://127.0.0.1:8000/`.

## إعداد الإنتاج
- اضبط `DJANGO_SECRET_KEY` بمفتاح طويل وعشوائي.
- اضبط `DJANGO_DEBUG=0`.
- اضبط `DJANGO_ALLOWED_HOSTS` و`DJANGO_CSRF_TRUSTED_ORIGINS` على نطاق الموقع.
- عيّن `DATABASE_URL` إلى رابط PostgreSQL.
- أمر البناء `bash build.sh` ينزل خط Noto Sans Arabic، ثم يجمع الملفات الثابتة ويطبق migrations.

## أول استخدام بعد النشر
1. أنشئ حساب Admin باستخدام `python manage.py createsuperuser` من Console الاستضافة.
2. سجّل الدخول إلى الموقع.
3. من **استيراد الملف المرجعي** ارفع ملف `inventory_2027_linked` بصيغة XLSX، راجع شاشة المعاينة والأعداد، ثم اضغط **اعتماد الاستيراد** لتعبئة الموظفين والأصول الحالية.
4. بعد الاستيراد، يمكنك إضافة/تعديل الأصول والموظفين من صفحات الإدارة، أو تنزيل نسخة من البيانات من **تصدير Excel**.
5. المستخدم العادي يستطيع البحث فقط وعرض/تنزيل PDF.

## ملاحظات البيانات
- يتم ربط الأصول بالموظفين بواسطة HR Code؛ ويُحفظ الكود على الأصل حتى إذا لم يكن الموظف موجودًا في قائمة الموظفين.
- Serial Number غير فريد على مستوى جميع الشيتات، لذلك يحتفظ النظام بكل سجل مصدر مكرر ويعرض النتائج المطابقة بدل حذفها.
- رفع الملف المرجعي يحدّث السجلات المستوردة بحسب اسم الشيت ورقم الصف، ولا يحذف الأصول التي أضيفت يدويًا من الموقع.
- عند الاستيراد الأول، يُسجل النظام الحالة المعروفة من ملف المصدر. إذا لم يحتوِ الملف على تواريخ تسليم/نقل تاريخية، سيظهر التاريخ على أنه غير متاح بدل اختراع تاريخ. سجلات Scraped ذات الرقم التسلسلي المطابق تُربط بتاريخ تخريد، وتستبعد الأصول المطابقة من العهدة النشطة.
- حركات الإدارة الجديدة تُسجّل تلقائيًا عند إضافة أصل أو تغيير HR Code أو الحالة من صفحة تعديل الأصل. تاريخ وسبب الحركة يمكن إدخالهما من النموذج. سجل الحركة مخصص للإضافة فقط ولا يُعدّل أو يُحذف من واجهة الإدارة.
- لا يتم استيراد حقول HR الحساسة غير اللازمة لعمل IT inventory، مثل الرقم القومي والدين وتاريخ الميلاد والتأمين الصحي.


## Custody PDF

The employee custody PDF uses WeasyPrint for correct Arabic/English bidirectional rendering. `railpack.json` adds the required Linux runtime libraries, and `build.sh` downloads Noto Sans Arabic Regular/Bold during the build (font files are not committed to the repository). The report remains on one A4 page, omits the 2025 requests and 2026 new-hires categories, and provides a blank notes area before the date/support/signature footer.

## Update v9 - Approved custody PDF & HR search efficiency
- The custody PDF now follows the user-approved sample layout: SIAC logo at top-left; company and IT department at top-right; employee information cards; separate computer, monitor, and GStar tables; only printers in Other Custody Records; a blank Notes area and the support/date/signature footer. It intentionally omits Asset Summary, 2025 issue/purchase requests, and 2026 new assignments.
- `Employee` now stores `Cost Center` and `Hiring Date` because both appear in the approved report. Migration `0006_employee_report_fields` adds these nullable/blank fields without deleting existing records.
- Import maps `Cost Center` and `Hiring Date` from the ID worksheet (falling back to Employment Date or Contract Start Date only if Hiring Date is blank). Re-import the same workbook after deployment to populate these two new fields; the importer updates by HR Code and source sheet/row and retains manual entries.
- HR search now prefetches movement histories in batches rather than querying movements separately for every matched asset, reducing the chance of a slow request while rendering employee history.
