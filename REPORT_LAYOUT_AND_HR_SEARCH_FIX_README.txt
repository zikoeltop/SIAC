SIAC v9 - PDF layout and HR Code search update

Changes included:
1. Custody PDF is aligned to the supplied one-page sample. It keeps the SIAC logo/header, employee information cards, separate Computers/Monitors/GStar tables, printer count under Other Custody Records, a blank Notes area, and date/support-user/signature fields in the footer.
2. The Asset Summary, 2025 issue/purchase requests, and 2026 new-assignment sections are omitted from the custody PDF.
3. Employee Cost Center and Hiring Date are persisted and exported, using migration 0006. The workbook importer reads only those two additional fields from ID (and no extra HR sensitive columns).
4. HR code search prefetches movement histories to avoid an individual history query for each asset.

Deployment notes:
- Copy these project files into the existing local SIAC repository; do not delete .git.
- Commit and push as usual. Railway build.sh runs migrations automatically.
- After deployment, re-import the same reference workbook once to populate the newly stored Cost Center and Hiring Date. This importer uses upserts for imported employees/assets and keeps manually created records. Do not reset or delete the database.
- If HR Code search still returns HTTP 500 after this update, capture the traceback from that exact HR search request; the prefetch change is a targeted performance hardening, but the exact live exception is needed to diagnose any different underlying error.
