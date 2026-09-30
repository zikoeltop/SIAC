from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    initial=True
    dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[migrations.CreateModel(name='AuditLog',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('action',models.CharField(choices=[('LOGIN','Login'),('LOGOUT','Logout'),('DEVICE_SEARCH','Device search'),('PDF_DOWNLOAD','PDF download'),('EXCEL_IMPORT','Excel import'),('USER_CREATE','User create'),('USER_EDIT','User edit'),('USER_DELETE','User delete'),('PASSWORD_CHANGE','Password change'),('PASSWORD_RESET','Password reset')],max_length=40)),('description',models.TextField(blank=True)),('ip_address',models.GenericIPAddressField(blank=True,null=True)),('created_at',models.DateTimeField(auto_now_add=True)),('user',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL))],options={'ordering':['-created_at']}),]
