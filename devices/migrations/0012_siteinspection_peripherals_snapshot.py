from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('devices', '0011_merge_0010_leaves')]
    operations = [
        migrations.AddField(
            model_name='siteinspection',
            name='peripherals_snapshot',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
