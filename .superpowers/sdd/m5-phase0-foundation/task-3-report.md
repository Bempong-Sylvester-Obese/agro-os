# Task 3: Worker CRUD API routes

**Status:** DONE
**Commit:** `2ba9ffdf3c85f86f8d7f6a138d7e032fd3354139`

## Summary

- Created `backend/app/routes/workers.py` with CRUD endpoints:
  - `GET /workers/` — list workers (requires cooperative_id)
  - `GET /workers/{worker_id}` — get worker by ID
  - `POST /workers/` — create worker (admin/farm_owner/farm_manager)
  - `PATCH /workers/{worker_id}` — update worker
  - `DELETE /workers/{worker_id}` — soft-delete (sets status to inactive)
- Registered workers router in `backend/main.py` (alphabetically after webhooks)
- Verified clean import: `python -c "from app.routes.workers import router; print('OK')"`
