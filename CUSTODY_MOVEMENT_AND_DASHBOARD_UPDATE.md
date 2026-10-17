# SIAC — Custody Movements, Management Dashboard, Permissions & Audit

## What's included

- Dedicated append-only custody workflows: assign from stock, transfer between employees, return to stock, and scrap with a required document number and date.
- A durable movement row for every operation containing the old/new employee snapshots, old/new statuses, effective date, reason, reference, notes, and authenticated user.
- Normal asset edit screens can no longer alter HR Code, status, scrap date, or scrap number directly; use the movement workflow so the event history remains complete.
- An admin-only management dashboard with active custody, in-stock, scrapped, pending and archived counts; PC versus laptop classification; monitor and printer totals; filtered model counts; charts by type/project/department; and an Excel report export.
- Admin-only routes for movement registration/listing and dashboard/reporting. Existing normal users retain search, custody history and PDF access. Movement operations, dashboard export, and Django Admin CRUD paths are logged in Audit Log; the Audit Log and movement history are read-only in Django Admin.
- New status choice `in_stock` and audit-action choices migrations.

## Deployment

1. Apply the files to the current project and review Git changes.
2. Commit and push to the GitHub repository currently attached to Railway.
3. Let Railway finish the deployment.
4. Run Django migrations in Railway Console before testing the new workflows:

   ```bash
   python manage.py migrate
   ```

5. Test the management dashboard, model filters and Excel export.
6. Test each movement against a test asset if available. Do not test by scrapping a live/important asset.

No data import is required. Existing assets and movement rows are preserved. The new `in_stock` choice is added by a non-destructive migration; older active assets without an HR Code are counted as stock for reporting compatibility.
