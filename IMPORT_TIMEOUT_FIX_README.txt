SIAC Inventory Import Timeout Fix
=================================

This update optimizes the Scraped-to-physical-asset reconciliation during the
reference workbook import. Previously, creating one movement with get_or_create
per matching pair could create many database round trips and hit Gunicorn's
request timeout on Railway.

Deploy steps:
1. Do NOT retry the workbook import until checking current DB counts.
2. Copy this project update over the existing local project, preserving .git.
3. Commit and push to GitHub.
4. In Railway > SIAC > Settings > Deploy, set Custom Start Command to:
   gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --timeout 300
   Save it and wait for a successful deployment.
5. In Railway Console, run this read-only check before attempting import:
   python manage.py shell -c "from devices.models import Employee, Asset, AssetMovement; print('Employees:', Employee.objects.count()); print('Assets:', Asset.objects.count()); print('Movements:', AssetMovement.objects.count())"
6. Review the counts. Only retry the workbook import once the failed attempt's
   state has been confirmed and the new deployment is active.

The reference import itself is wrapped in transaction.atomic(), so an interrupted
request is expected to roll back its uncommitted database changes when the DB
connection closes. Always verify counts instead of assuming.
