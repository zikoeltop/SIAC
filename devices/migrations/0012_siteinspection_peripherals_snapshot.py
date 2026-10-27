from django.db import migrations, models


class Migration(migrations.Migration):
    # Keep this migration dependent only on the existing merged visit-history
    # branch. The production database already has this migration applied, while
    # 0010_simplify_site_inspection_statuses is still unapplied there. Making
    # 0012 depend on 0010 causes Django's InconsistentMigrationHistory check to
    # stop the deployment before migrations can run.
    dependencies = [
        ('devices', '0011_merge_0010_leaves'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteinspection',
            name='peripherals_snapshot',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
