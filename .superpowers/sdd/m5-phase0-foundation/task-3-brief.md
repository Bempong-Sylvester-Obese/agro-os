### Task 3: Worker CRUD API routes

**Files:**
- Create: `backend/app/routes/workers.py`
- Modify: `backend/main.py` (register workers router)

**Step 1: Create workers router**

`backend/app/routes/workers.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import Cooperative, User
from app.models.worker import Worker, WorkerRole, WorkerStatus
from app.schemas.worker import WorkerCreate, WorkerResponse, WorkerUpdate
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/workers", tags=["workers"])


@router.get("/", response_model=list[WorkerResponse])
def list_workers(
    cooperative_id: int = Query(...),
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    return (
        db.query(Worker)
        .filter(Worker.cooperative_id == cooperative_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{worker_id}", response_model=WorkerResponse)
def get_worker(
    worker_id: int,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    worker = (
        db.query(Worker)
        .filter(Worker.id == worker_id, Worker.cooperative_id == cooperative_id)
        .first()
    )
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@router.post("/", response_model=WorkerResponse, status_code=201)
def create_worker(
    data: WorkerCreate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    existing = (
        db.query(Worker)
        .filter(Worker.cooperative_id == cooperative_id, Worker.phone == data.phone)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Worker with this phone already exists")

    worker = Worker(
        cooperative_id=cooperative_id,
        name=data.name,
        phone=data.phone,
        wage_rate=data.wage_rate,
        role=WorkerRole(data.role) if data.role else WorkerRole.worker,
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.patch("/{worker_id}", response_model=WorkerResponse)
def update_worker(
    worker_id: int,
    data: WorkerUpdate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    worker = (
        db.query(Worker)
        .filter(Worker.id == worker_id, Worker.cooperative_id == cooperative_id)
        .first()
    )
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "role" and value:
            value = WorkerRole(value)
        if field == "status" and value:
            value = WorkerStatus(value)
        setattr(worker, field, value)

    db.commit()
    db.refresh(worker)
    return worker


@router.delete("/{worker_id}", status_code=204)
def delete_worker(
    worker_id: int,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    worker = (
        db.query(Worker)
        .filter(Worker.id == worker_id, Worker.cooperative_id == cooperative_id)
        .first()
    )
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.status = WorkerStatus.inactive
    db.commit()
```

**Step 2: Register workers router in main.py**

In `backend/main.py`, add the import:

```python
from app.routes import workers as workers_router
```

And register with the other routers:

```python
app.include_router(workers_router.router)
```

Place it alphabetically (after webhooks, before agro_ai).
