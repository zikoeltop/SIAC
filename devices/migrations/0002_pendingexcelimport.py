from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        ('devices', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingExcelImport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='excel/pending/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('total_rows', models.PositiveIntegerField(default=0)),
                ('valid_rows', models.PositiveIntegerField(default=0)),
                ('duplicate_rows', models.PositiveIntegerField(default=0)),
                ('preview_rows', models.JSONField(blank=True, default=list)),
                ('columns', models.JSONField(blank=True, default=list)),
                ('is_approved', models.BooleanField(default=False)),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.user')),
            ],
            options={'ordering': ['-uploaded_at']},
        ),
    ]
