from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('devices', '0006_employee_report_fields')]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='asset_status',
            field=models.CharField(
                choices=[
                    ('active', 'Active / Custody'),
                    ('in_stock', 'In Stock / المخزن'),
                    ('pending', 'Pending'),
                    ('scrapped', 'Scrapped'),
                    ('archived', 'Archived'),
                ],
                db_index=True,
                default='active',
                max_length=20,
                verbose_name='Asset Status',
            ),
        ),
    ]
