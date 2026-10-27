from django.db import migrations, models


def normalize_statuses(apps, schema_editor):
    SiteInspection = apps.get_model('devices', 'SiteInspection')
    db = schema_editor.connection.alias
    SiteInspection.objects.using(db).filter(status='needs_attention').update(status='inspected')
    SiteInspection.objects.using(db).filter(status='unable').update(status='pending')


class Migration(migrations.Migration):
    dependencies = [('devices', '0012_siteinspection_peripherals_snapshot')]

    operations = [
        migrations.RunPython(normalize_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='siteinspection',
            name='status',
            field=models.CharField(
                choices=[('pending', 'لم يتم الفحص'), ('inspected', 'تم الفحص')],
                db_index=True,
                default='pending',
                max_length=24,
            ),
        ),
    ]
