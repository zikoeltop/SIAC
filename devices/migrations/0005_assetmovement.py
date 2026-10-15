from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        ('devices', '0004_pendinginventoryimport'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[
                    ('source_state', 'الحالة المسجلة في الملف المرجعي'),
                    ('added_to_stock', 'إضافة إلى المخزون'),
                    ('assigned', 'تسليم لموظف'),
                    ('transferred', 'نقل عهدة بين موظفين'),
                    ('returned', 'إرجاع إلى المخزون'),
                    ('scrapped', 'تخريد'),
                    ('status_changed', 'تغيير حالة الأصل'),
                ], db_index=True, max_length=32)),
                ('effective_date', models.DateField(blank=True, db_index=True, null=True, verbose_name='تاريخ الحركة')),
                ('from_hr_code', models.CharField(blank=True, db_index=True, max_length=80)),
                ('from_employee_name', models.CharField(blank=True, max_length=255)),
                ('to_hr_code', models.CharField(blank=True, db_index=True, max_length=80)),
                ('to_employee_name', models.CharField(blank=True, max_length=255)),
                ('from_status', models.CharField(blank=True, max_length=20)),
                ('to_status', models.CharField(blank=True, max_length=20)),
                ('reason', models.CharField(blank=True, max_length=255, verbose_name='سبب الحركة')),
                ('reference_number', models.CharField(blank=True, max_length=120, verbose_name='رقم المستند')),
                ('notes', models.TextField(blank=True)),
                ('source_sheet', models.CharField(blank=True, max_length=64)),
                ('source_row', models.PositiveIntegerField(blank=True, null=True)),
                ('source_event_key', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movements', to='devices.asset', verbose_name='الأصل')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='asset_movement_events', to=settings.AUTH_USER_MODEL)),
                ('from_employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='asset_movements_from', to='devices.employee', verbose_name='الموظف السابق')),
                ('to_employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='asset_movements_to', to='devices.employee', verbose_name='الموظف الجديد')),
            ],
            options={'ordering': ['effective_date', 'created_at', 'id']},
        ),
        migrations.AddIndex(
            model_name='assetmovement',
            index=models.Index(fields=['asset', 'effective_date'], name='move_asset_date_idx'),
        ),
        migrations.AddIndex(
            model_name='assetmovement',
            index=models.Index(fields=['from_hr_code', 'effective_date'], name='move_from_hr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='assetmovement',
            index=models.Index(fields=['to_hr_code', 'effective_date'], name='move_to_hr_date_idx'),
        ),
    ]
