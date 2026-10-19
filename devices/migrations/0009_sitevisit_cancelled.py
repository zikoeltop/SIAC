from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0008_site_visits'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitevisit',
            name='status',
            field=models.CharField(
                choices=[('in_progress', 'جارية'), ('completed', 'مكتملة'), ('cancelled', 'ملغاة')],
                db_index=True,
                default='in_progress',
                max_length=20,
            ),
        ),
    ]
