# SIAC Site Visits & Smart IT Asset Dashboard — Patch v14

This patch adds project site visits, recurring device inspections, and smart dashboard metrics to the existing SIAC Django project. It does not include or enable OneDrive sync.

## What is included

- Updates the main SIAC dashboard to show global asset-inspection and site-visit metrics.
- Adds inspection metrics to the existing management inventory dashboard, preserving its asset/model/brand reporting features.
- Adds a project selector in **Site Visits**. Selecting a project opens its Smart IT Asset Dashboard.
- Creates one visit header per project/date/technician and seeds the visit with a checklist of eligible physical assets registered to that project.
- Allows searching the eligible SIAC asset inventory by serial number, computer name, model/type, employee name, or HR Code and adding an asset found on site even when its source project differs. The asset's source project in the core `Asset` table is not changed.
- Stores the per-visit snapshot in separate `SiteInspection` records. Changes to USER NAME or monitor/printer fields are only changes to the inspection snapshot, never to the core asset record.
- Requires a reason whenever a snapshot value changes. A dated automatic audit comment records the old value, new value and reason; the Excel COMMENTS column combines these entries with the technician's own comments.
- Supports the results **Inspected / OK**, **Needs attention**, **Unable to inspect**, and **Pending**. Unable-to-inspect rows require a reason. Pending rows prevent visit completion.
- Locks completed visits to preserve the historical record; create a new visit to capture new inspection results.
- Tracks successful inspection counts and most recent inspection date per asset, repeat inspections, never-inspected devices, visit coverage, and date-range coverage.
- Exports a workbook named `Periodic Inspection` using these exact columns in order:

  `Project`, `visit date`, `IT TECH NAME`, `USER NAME`, `TYPE`, `MODEL`, `SERIAL NUMBER`, `COMPUTER NAME`, `Monitor Model`, `Monitor Serial`, `printer model`, `printer serial`, `COMMENTS`.

## Important behavior

- Dashboard coverage for a project only counts successful inspections captured on visits belonging to that project. An asset inspected as an extra on another project's visit does not inflate the source project's coverage.
- An inspection counts as completed only when its result is `inspected` or `needs_attention`. `unable` is recorded but does not count toward coverage.
- The default project checklist is generated from the current SIAC records when a visit is created/opened. Newly added project devices are also added to an open visit before it can be completed.
- Peripheral columns on a computer row are populated from monitor/printer assets associated with the same HR Code. The monitor/printer asset rows themselves remain separately available when those assets are included in the project's inventory.
- `SiteInspection.asset` uses `PROTECT`, and a visit keeps a per-asset snapshot for historical continuity.

## Files in this patch

The ZIP contains only the changed/new application files. It deliberately excludes `.git`, `.env`, local databases, user uploads and generated static files.

## Apply safely on a local copy first

1. Keep a separate backup/copy of the current working project.
2. Extract this patch ZIP and copy its contents into the **project root** (the folder containing `manage.py`), merging folders and replacing only matching application files.
3. In the project's active virtual environment, run:

   ```powershell
   python manage.py check
   python manage.py makemigrations --check --dry-run
   python manage.py test devices
   python manage.py migrate
   python manage.py runserver
   ```

4. Sign in and check the main dashboard, open **سجل زيارات المشاريع**, select a project, create a test visit, verify the checklist and cross-project search, save an inspection, and export the workbook. Confirm that the Excel headers match the list above and that the original `Asset` data did not change when snapshot fields were edited.
5. Only after local checks pass should the patch be committed and pushed to the repository connected to the active Railway service. Railway's existing build script runs `python manage.py migrate` during deployment.

## Validation note

The source files have passed Python bytecode compilation and `git diff --check` in the patch-preparation environment. Django is not installed in that environment, so `manage.py check` and the Django test suite could not be run here. Treat this as a patch to validate on your working copy before deployment; do not push it directly to production without those checks.
