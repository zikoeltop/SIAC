from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    initial=True
    dependencies=[('accounts','0001_initial')]
    operations=[
        migrations.CreateModel(name='Device',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('serial_number',models.CharField(db_index=True,max_length=150,unique=True)),('user_name',models.CharField(blank=True,max_length=255)),('project',models.CharField(blank=True,max_length=255)),('model',models.CharField(blank=True,max_length=255)),('processor',models.CharField(blank=True,max_length=500)),('ram',models.CharField(blank=True,max_length=255)),('computer_name',models.CharField(blank=True,max_length=255)),('hdd',models.CharField(blank=True,max_length=500)),('raw_data',models.JSONField(blank=True,default=dict)),('imported_at',models.DateTimeField(auto_now=True))]),
        migrations.CreateModel(name='DeviceImport',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('file',models.FileField(upload_to='excel/')),('uploaded_at',models.DateTimeField(auto_now_add=True)),('rows_imported',models.PositiveIntegerField(default=0)),('is_current',models.BooleanField(default=True)),('uploaded_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user'))]),
    ]
