from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("devices", "0005_assetmovement")]

    operations = [
        migrations.AddField(model_name="employee", name="cost_center", field=models.CharField(blank=True, max_length=255, verbose_name="Cost Center")),
        migrations.AddField(model_name="employee", name="hiring_date", field=models.DateField(blank=True, null=True, verbose_name="Hiring Date")),
    ]
