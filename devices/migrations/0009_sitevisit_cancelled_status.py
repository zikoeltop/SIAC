from django.db import migrations, models


def align_existing_computer_names(apps, schema_editor):
    SiteInspection = apps.get_model('devices', 'SiteInspection')
    Asset = apps.get_model('devices', 'Asset')
    db_alias = schema_editor.connection.alias
    for inspection in SiteInspection.objects.using(db_alias).select_related('asset').iterator():
        asset = inspection.asset
        preferred = (asset.computer_name_new or asset.computer_name or '').strip()
        if preferred and inspection.computer_name_snapshot != preferred:
            SiteInspection.objects.using(db_alias).filter(pk=inspection.pk).update(
                computer_name_snapshot=preferred
            )


class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0008_site_visits'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitevisit',
            name='status',
            field=models.CharField(
                choices=[
                    ('in_progress', 'جارية'),
                    ('completed', 'مكتملة'),
                    ('cancelled', 'ملغاة'),
                ],
                db_index=True,
                default='in_progress',
                max_length=20,
            ),
        ),
        migrations.RunPython(align_existing_computer_names, migrations.RunPython.noop),
    ]
