from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
from .models import Asset, AssetMovement, Employee


User = get_user_model()


class CustodyMovementWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='siacadmin', password='Secure-test-password-123', role='ADMIN'
        )
        self.regular = User.objects.create_user(
            username='siacuser', password='Secure-test-password-123', role='USER'
        )
        self.employee1 = Employee.objects.create(hr_code='1001', name='Employee One')
        self.employee2 = Employee.objects.create(hr_code='1002', name='Employee Two')
        self.asset = Asset.objects.create(
            asset_type=Asset.Types.COMPUTER,
            asset_status=Asset.Status.IN_STOCK,
            serial_number='SN-TEST-100',
            brand='Dell', model='OptiPlex 7010', item_type='Desktop PC',
            source_sheet='manual',
        )
        self.client.force_login(self.admin)

    def test_assign_then_transfer_then_return_preserves_all_events(self):
        response = self.client.post(reverse('movement_create', args=[self.asset.pk]), {
            'event_type': AssetMovement.EventTypes.ASSIGNED,
            'target_hr_code': self.employee1.hr_code,
            'effective_date': '2026-10-17',
            'reason': 'تسليم جهاز للموظف',
            'reference_number': 'HANDOVER-1',
            'notes': 'اختبار حركة',
        })
        self.assertEqual(response.status_code, 302)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.hr_code, self.employee1.hr_code)
        self.assertEqual(self.asset.asset_status, Asset.Status.ACTIVE)
        self.assertEqual(AssetMovement.objects.count(), 1)
        self.assertEqual(AssetMovement.objects.get().created_by, self.admin)
        self.assertTrue(AuditLog.objects.filter(action='ASSET_ASSIGN').exists())

        response = self.client.post(reverse('movement_create', args=[self.asset.pk]), {
            'event_type': AssetMovement.EventTypes.TRANSFERRED,
            'target_hr_code': self.employee2.hr_code,
            'effective_date': '2026-10-18',
            'reason': 'نقل عهدة', 'reference_number': 'TRANSFER-1', 'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.hr_code, self.employee2.hr_code)
        self.assertEqual(AssetMovement.objects.count(), 2)
        latest_transfer = AssetMovement.objects.order_by('-id').first()
        self.assertEqual(latest_transfer.from_hr_code, self.employee1.hr_code)
        self.assertEqual(latest_transfer.to_hr_code, self.employee2.hr_code)
        self.assertTrue(AuditLog.objects.filter(action='ASSET_TRANSFER').exists())

        response = self.client.post(reverse('movement_create', args=[self.asset.pk]), {
            'event_type': AssetMovement.EventTypes.RETURNED,
            'target_hr_code': '', 'effective_date': '2026-10-19',
            'reason': 'إرجاع للمخزن', 'reference_number': 'RETURN-1', 'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.hr_code, '')
        self.assertEqual(self.asset.asset_status, Asset.Status.IN_STOCK)
        self.assertEqual(AssetMovement.objects.count(), 3)
        self.assertTrue(AuditLog.objects.filter(action='ASSET_RETURN').exists())

    def test_scrap_requires_number_and_records_holder_then_scrap_state(self):
        self.asset.hr_code = self.employee1.hr_code
        self.asset.employee = self.employee1
        self.asset.employee_name = self.employee1.name
        self.asset.asset_status = Asset.Status.ACTIVE
        self.asset.save()

        response = self.client.post(reverse('movement_create', args=[self.asset.pk]), {
            'event_type': AssetMovement.EventTypes.SCRAPPED,
            'effective_date': '2026-10-17', 'reason': 'تخريد رسمي',
            'reference_number': 'SCRAP-77', 'notes': 'محضر تخريد معتمد',
        })
        self.assertEqual(response.status_code, 302)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.asset_status, Asset.Status.SCRAPPED)
        self.assertEqual(self.asset.scrap_number, 'SCRAP-77')
        self.assertEqual(self.asset.scrap_date, '2026-10-17')
        movement = AssetMovement.objects.get(event_type=AssetMovement.EventTypes.SCRAPPED)
        self.assertEqual(movement.from_hr_code, self.employee1.hr_code)
        self.assertEqual(movement.to_employee_name, 'التخريد')
        self.assertTrue(AuditLog.objects.filter(action='ASSET_SCRAP').exists())

    def test_regular_user_cannot_open_admin_movement_or_dashboard_pages(self):
        self.client.force_login(self.regular)
        for url in [reverse('movement_list'), reverse('movement_asset_search'), reverse('inventory_dashboard'), reverse('inventory_dashboard_export')]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)

    def test_dashboard_filters_model_counts(self):
        Asset.objects.create(
            asset_type=Asset.Types.COMPUTER, asset_status=Asset.Status.ACTIVE,
            serial_number='SN-LAPTOP-1', brand='HP', model='EliteBook 840', item_type='Laptop',
            hr_code=self.employee1.hr_code, employee=self.employee1, employee_name=self.employee1.name,
            source_sheet='manual',
        )
        response = self.client.get(reverse('inventory_dashboard'), {'model_type': 'laptop', 'model_q': 'EliteBook'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EliteBook 840')
        self.assertContains(response, 'Laptop')
