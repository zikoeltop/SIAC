from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('audit', '0001_initial')]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(
                max_length=40,
                choices=[
                    ('LOGIN', 'Login'),
                    ('LOGOUT', 'Logout'),
                    ('DEVICE_SEARCH', 'Device search'),
                    ('ASSET_SEARCH', 'Asset search'),
                    ('PDF_DOWNLOAD', 'PDF download'),
                    ('CUSTODY_PDF_DOWNLOAD', 'Custody PDF download'),
                    ('EXCEL_IMPORT', 'Excel import'),
                    ('EXCEL_PREVIEW', 'Excel preview'),
                    ('INVENTORY_PREVIEW', 'Inventory import preview'),
                    ('INVENTORY_IMPORT', 'Inventory import'),
                    ('INVENTORY_EXPORT', 'Inventory export'),
                    ('EMPLOYEE_CREATE', 'Employee create'),
                    ('EMPLOYEE_EDIT', 'Employee edit'),
                    ('ASSET_CREATE', 'Asset create'),
                    ('ASSET_EDIT', 'Asset edit'),
                    ('USER_CREATE', 'User create'),
                    ('USER_EDIT', 'User edit'),
                    ('USER_DELETE', 'User delete'),
                    ('ASSET_ASSIGN', 'Asset assigned'),
                    ('ASSET_TRANSFER', 'Asset custody transferred'),
                    ('ASSET_RETURN', 'Asset returned to stock'),
                    ('ASSET_SCRAP', 'Asset scrapped'),
                    ('DASHBOARD_EXPORT', 'Management dashboard export'),
                    ('EMPLOYEE_DELETE', 'Employee delete'),
                    ('LEGACY_DEVICE_CREATE', 'Legacy device create'),
                    ('LEGACY_DEVICE_EDIT', 'Legacy device edit'),
                    ('LEGACY_DEVICE_DELETE', 'Legacy device delete'),
                    ('LEGACY_IMPORT_CREATE', 'Legacy import create'),
                    ('LEGACY_IMPORT_EDIT', 'Legacy import edit'),
                    ('LEGACY_IMPORT_DELETE', 'Legacy import delete'),
                    ('PASSWORD_CHANGE', 'Password change'),
                    ('PASSWORD_RESET', 'Password reset'),
                ],
            ),
        ),
    ]
