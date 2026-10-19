from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0007_asset_in_stock_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project', models.CharField(db_index=True, max_length=255, verbose_name='Project')),
                ('visit_date', models.DateField(db_index=True, default=django.utils.timezone.localdate, verbose_name='Visit Date')),
                ('technician_name', models.CharField(max_length=255, verbose_name='IT Tech Name')),
                ('status', models.CharField(choices=[('in_progress', 'جارية'), ('completed', 'مكتملة')], db_index=True, default='in_progress', max_length=20)),
                ('notes', models.TextField(blank=True, verbose_name='Visit Notes')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='site_visits_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-visit_date', '-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='SiteInspection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_additional', models.BooleanField(db_index=True, default=False)),
                ('source_project', models.CharField(blank=True, max_length=255)),
                ('source_user_name', models.CharField(blank=True, max_length=255)),
                ('user_name', models.CharField(blank=True, max_length=255)),
                ('type_snapshot', models.CharField(blank=True, max_length=120)),
                ('model_snapshot', models.CharField(blank=True, max_length=255)),
                ('serial_number_snapshot', models.CharField(blank=True, db_index=True, max_length=180)),
                ('computer_name_snapshot', models.CharField(blank=True, max_length=255)),
                ('source_monitor_model', models.CharField(blank=True, max_length=255)),
                ('monitor_model', models.CharField(blank=True, max_length=255)),
                ('source_monitor_serial', models.CharField(blank=True, max_length=255)),
                ('monitor_serial', models.CharField(blank=True, max_length=255)),
                ('source_printer_model', models.CharField(blank=True, max_length=255)),
                ('printer_model', models.CharField(blank=True, max_length=255)),
                ('source_printer_serial', models.CharField(blank=True, max_length=255)),
                ('printer_serial', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('pending', 'لم يتم الفحص'), ('inspected', 'تم الفحص - سليم'), ('needs_attention', 'تم الفحص - يحتاج متابعة'), ('unable', 'تعذر الفحص')], db_index=True, default='pending', max_length=24)),
                ('comments', models.TextField(blank=True, verbose_name='Technician Comments')),
                ('auto_comments', models.TextField(blank=True, verbose_name='Automatic Change Comments')),
                ('inspected_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='site_inspections', to='devices.asset')),
                ('inspected_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='site_inspections_saved', to=settings.AUTH_USER_MODEL)),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inspections', to='devices.sitevisit')),
            ],
            options={'ordering': ['serial_number_snapshot', 'id']},
        ),
        migrations.AddIndex(
            model_name='sitevisit',
            index=models.Index(fields=['project', 'visit_date'], name='sitevisit_project_date_idx'),
        ),
        migrations.AddIndex(
            model_name='sitevisit',
            index=models.Index(fields=['status', 'visit_date'], name='sitevisit_status_date_idx'),
        ),
        migrations.AddConstraint(
            model_name='siteinspection',
            constraint=models.UniqueConstraint(fields=('visit', 'asset'), name='uniq_site_inspection_visit_asset'),
        ),
        migrations.AddIndex(
            model_name='siteinspection',
            index=models.Index(fields=['asset', 'status'], name='siteinspect_asset_status_idx'),
        ),
        migrations.AddIndex(
            model_name='siteinspection',
            index=models.Index(fields=['visit', 'status'], name='siteinspect_visit_status_idx'),
        ),
    ]
