from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0002_pendingexcelimport'),
    ]

    operations = [
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hr_code', models.CharField(db_index=True, max_length=80, unique=True, verbose_name='HR Code')),
                ('name', models.CharField(max_length=255, verbose_name='Employee Name')),
                ('arabic_name', models.CharField(blank=True, max_length=255, verbose_name='Arabic Name')),
                ('company', models.CharField(blank=True, max_length=255)),
                ('project', models.CharField(blank=True, max_length=255, verbose_name='Project / Site')),
                ('sector', models.CharField(blank=True, max_length=255, verbose_name='Sector')),
                ('department', models.CharField(blank=True, max_length=255, verbose_name='Department')),
                ('section', models.CharField(blank=True, max_length=255, verbose_name='Section')),
                ('unit', models.CharField(blank=True, max_length=255, verbose_name='Unit')),
                ('office', models.CharField(blank=True, max_length=255, verbose_name='Office')),
                ('team', models.CharField(blank=True, max_length=255, verbose_name='Team')),
                ('position', models.CharField(blank=True, max_length=255, verbose_name='Position')),
                ('employment_status', models.CharField(blank=True, max_length=80, verbose_name='Employment Status')),
                ('termination_date', models.DateField(blank=True, null=True, verbose_name='Termination Date')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['name', 'hr_code']},
        ),
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hr_code', models.CharField(blank=True, db_index=True, max_length=80, verbose_name='HR Code')),
                ('employee_name', models.CharField(blank=True, max_length=255, verbose_name='Employee Name (source)')),
                ('asset_type', models.CharField(choices=[('computer', 'Computers'), ('printer', 'Printers'), ('monitor', 'Monitors'), ('gstar_license', 'GStar CAD licenses'), ('new_2026', 'New hires 2026'), ('request_2025', 'Requests 2025'), ('scraped', 'Scrapped assets'), ('other', 'Other assets')], db_index=True, default='computer', max_length=30, verbose_name='Asset Type')),
                ('asset_status', models.CharField(choices=[('active', 'Active / Custody'), ('pending', 'Pending'), ('scrapped', 'Scrapped'), ('archived', 'Archived')], db_index=True, default='active', max_length=20, verbose_name='Asset Status')),
                ('source_sheet', models.CharField(db_index=True, default='manual', max_length=64, verbose_name='Source Sheet')),
                ('source_row', models.PositiveIntegerField(blank=True, null=True, verbose_name='Source Row')),
                ('company', models.CharField(blank=True, max_length=255)),
                ('project', models.CharField(blank=True, db_index=True, max_length=255)),
                ('sector', models.CharField(blank=True, max_length=255)),
                ('department', models.CharField(blank=True, max_length=255)),
                ('computer_name_new', models.CharField(blank=True, max_length=255, verbose_name='Computer Name New')),
                ('computer_name', models.CharField(blank=True, max_length=255, verbose_name='Computer Name')),
                ('item_type', models.CharField(blank=True, max_length=255, verbose_name='Item / Type')),
                ('brand', models.CharField(blank=True, max_length=255)),
                ('model', models.CharField(blank=True, max_length=255)),
                ('serial_number', models.CharField(blank=True, db_index=True, max_length=180, verbose_name='Serial Number')),
                ('asset_tag', models.CharField(blank=True, max_length=180, verbose_name='Asset Number')),
                ('manufacturing_year', models.CharField(blank=True, max_length=40, verbose_name='Manufacturing Year')),
                ('processor', models.CharField(blank=True, max_length=255)),
                ('ram', models.CharField(blank=True, max_length=120)),
                ('storage', models.CharField(blank=True, max_length=255, verbose_name='Storage / HDD')),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('toner_code', models.CharField(blank=True, max_length=180, verbose_name='Toner Code')),
                ('license_version', models.CharField(blank=True, max_length=180, verbose_name='License Version')),
                ('license_activated', models.CharField(blank=True, max_length=80, verbose_name='License Activated')),
                ('purchase_date', models.DateField(blank=True, null=True)),
                ('scrap_date', models.CharField(blank=True, max_length=80, verbose_name='Scrap Date')),
                ('scrap_number', models.CharField(blank=True, max_length=120, verbose_name='Scrap Number')),
                ('notes', models.TextField(blank=True)),
                ('software_licenses', models.JSONField(blank=True, default=dict)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets', to='devices.employee', verbose_name='Matched Employee')),
            ],
            options={'ordering': ['asset_type', 'employee_name', 'serial_number']},
        ),
        migrations.AddConstraint(
            model_name='asset',
            constraint=models.UniqueConstraint(fields=('source_sheet', 'source_row'), name='uniq_asset_source_row'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['hr_code', 'asset_status'], name='asset_hr_status_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['asset_type', 'asset_status'], name='asset_type_status_idx'),
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['name'], name='employee_name_idx'),
        ),
    ]
