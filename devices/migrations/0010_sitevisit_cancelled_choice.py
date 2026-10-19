from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0009_sitevisit_cancelled_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitevisit',
            name='status',
            field=models.CharField(choices=[('in_progress', '\u062c\u0627\u0631\u064a\u0629'), ('completed', '\u0645\u0643\u062a\u0645\u0644\u0629'), ('cancelled', '\u0645\u0644\u063a\u0627\u0629')], db_index=True, default='in_progress', max_length=20),
        ),
    ]
