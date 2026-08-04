# Task 2 Report — Worker model + schemas

## Files created/modified
- Created: `backend/app/models/worker.py`
- Created: `backend/app/schemas/worker.py`
- Modified: `backend/main.py` (added `from app.models import worker  # noqa: F401`)

## Commands and output
```
> python -c "from app.models.worker import Worker, WorkerRole, WorkerStatus; print('Worker model OK')"
Worker model OK

> python -c "from app.schemas.worker import WorkerCreate, WorkerUpdate, WorkerResponse; print('Worker schemas OK')"
Worker schemas OK
```

## Commit
`c466b7e` — `feat: add Worker model and schemas`

## Concerns
None.
