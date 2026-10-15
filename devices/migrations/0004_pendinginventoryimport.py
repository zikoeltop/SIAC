from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0003_employee_asset'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingInventoryImport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='excel/inventory-pending/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('summary', models.JSONField(blank=True, default=dict)),
                ('is_approved', models.BooleanField(default=False)),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.user')),
            ],
            options={'ordering': ['-uploaded_at']},
        ),
    ]
