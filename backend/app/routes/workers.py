from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.services import entitlements
from app.services.organization_guards import WORKER_SOLO_FARM_ONLY, require_solo_farm

router = APIRouter(prefix="/workers", tags=["workers"])


def _validate_linked_user(db: Session, cooperative_id: int, user_id: int | None) -> None:
    if user_id is None:
        return
    linked = db.query(User).filter(User.id == user_id).first()
    if not linked:
        raise HTTPException(status_code=404, detail="User not found")
    if linked.cooperative_id != cooperative_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User belongs to another workspace",
        )


@router.get("/", response_model=list[WorkerResponse])
def list_workers(
    cooperative_id: int = Query(...),
    include_inactive: bool = Query(default=False),
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    query = db.query(Worker).filter(Worker.cooperative_id == cooperative_id)
    if not include_inactive:
        query = query.filter(Worker.status != WorkerStatus.inactive)
    return query.offset(skip).limit(limit).all()


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
    require_solo_farm(coop, detail=WORKER_SOLO_FARM_ONLY)
    entitlements.assert_within_limit(db, coop, "max_workers")

    existing = (
        db.query(Worker)
        .filter(Worker.cooperative_id == cooperative_id, Worker.phone == data.phone)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Worker with this phone already exists")
    _validate_linked_user(db, cooperative_id, data.user_id)

    worker = Worker(
        cooperative_id=cooperative_id,
        name=data.name,
        phone=data.phone,
        wage_rate=data.wage_rate,
        role=WorkerRole(data.role) if data.role else WorkerRole.worker,
        hire_date=data.hire_date,
        pay_type=data.pay_type,
        user_id=data.user_id,
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
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    require_solo_farm(coop, detail=WORKER_SOLO_FARM_ONLY)
    worker = (
        db.query(Worker)
        .filter(Worker.id == worker_id, Worker.cooperative_id == cooperative_id)
        .first()
    )
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    updates = data.model_dump(exclude_none=True)
    if "user_id" in updates:
        _validate_linked_user(db, cooperative_id, updates["user_id"])

    for field, value in updates.items():
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
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    require_solo_farm(coop, detail=WORKER_SOLO_FARM_ONLY)
    worker = (
        db.query(Worker)
        .filter(Worker.id == worker_id, Worker.cooperative_id == cooperative_id)
        .first()
    )
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.status = WorkerStatus.inactive
    db.commit()
