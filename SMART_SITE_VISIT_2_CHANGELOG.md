# Smart Site Visit 2.0 – changes in this build

- Search in the visit page is limited to Serial Number and Computer Name (including the alternate Computer Name field).
- Computer, monitor, and printer inspection rows are displayed independently rather than hiding peripherals under a computer row.
- During visit setup, monitors/printers sharing a real HR Code with a computer in the project's checklist are included, even if their project field is blank or stale. The shared `Consaltant` marker is excluded from matching.
- When adding a computer as an additional device, peripherals with the same real HR Code are also added as independent inspection rows.
- The supported inspection statuses are reduced to `تم الفحص` and `لم يتم الفحص`. Migration 0010 converts legacy `needs_attention` to `inspected`, and `unable` to `pending`.
- The existing snapshot editing and optional change-reason fields continue to save changes to the visit snapshot, not to the main Asset record.

## Validation note

Python syntax compilation succeeded. Django checks and automated tests could not be run in this environment because Django is not installed and package download access is unavailable.

## Not included in this build

Creating a visit-only inspection row for a device that has no Asset record whatsoever is not yet implemented; the existing “additional device” flow still selects an existing SIAC Asset that is outside the visit project's scope. This is called out rather than represented as completed.
