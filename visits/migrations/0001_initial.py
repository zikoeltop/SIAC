# Generated for the Smart IT Asset Dashboard project-visit module.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('devices', '0007_asset_in_stock_status'),
    ]
    operations = [
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project', models.CharField(db_index=True, max_length=255)),
                ('visit_date', models.DateField()),
                ('technician_name', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('draft', 'مسودة'), ('approved', 'معتمدة'), ('cancelled', 'ملغاة')], db_index=True, default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='project_visits', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_project_visits', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-visit_date', '-created_at']},
        ),
        migrations.CreateModel(
            name='VisitItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_name', models.CharField(blank=True, max_length=255)),
                ('device_type', models.CharField(blank=True, max_length=100)),
                ('model', models.CharField(blank=True, max_length=255)),
                ('serial_number', models.CharField(blank=True, db_index=True, max_length=180)),
                ('computer_name', models.CharField(blank=True, max_length=255)),
                ('monitor_model', models.CharField(blank=True, max_length=255)),
                ('monitor_serial', models.CharField(blank=True, max_length=180)),
                ('printer_model', models.CharField(blank=True, max_length=255)),
                ('printer_serial', models.CharField(blank=True, max_length=180)),
                ('comments', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inspection_rows', to='devices.asset')),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='visits.visit')),
            ],
            options={'ordering': ['serial_number', 'id']},
        ),
    ]
