from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database.db import get_db
from app.models.models import Cooperative, User
from app.models.work_task import TaskStatus, WorkTask, WorkerAssignment
from app.schemas.work_task import TaskAssignmentCreate, TaskCreate, TaskResponse, TaskUpdate
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    cooperative_id: int = Query(...),
    status: str | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    query = db.query(WorkTask).options(joinedload(WorkTask.assignments)).filter(WorkTask.cooperative_id == cooperative_id)
    if status:
        query = query.filter(WorkTask.status == TaskStatus(status))
    return query.order_by(WorkTask.scheduled_date.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(
    data: TaskCreate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    task = WorkTask(
        cooperative_id=cooperative_id,
        title=data.title,
        description=data.description,
        task_type=data.task_type,
        location=data.location,
        scheduled_date=data.scheduled_date,
        assigned_by=current_user.id if current_user else None,
    )
    db.add(task)
    db.flush()

    for worker_id in data.worker_ids:
        assignment = WorkerAssignment(work_task_id=task.id, worker_id=worker_id)
        db.add(assignment)

    db.commit()
    db.refresh(task)
    return db.query(WorkTask).options(joinedload(WorkTask.assignments)).filter(WorkTask.id == task.id).first()


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    data: TaskUpdate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    task = db.query(WorkTask).options(joinedload(WorkTask.assignments)).filter(
        WorkTask.id == task_id, WorkTask.cooperative_id == cooperative_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "status" and value:
            value = TaskStatus(value)
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/assign", response_model=TaskResponse)
def assign_workers(
    task_id: int,
    data: TaskAssignmentCreate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    task = db.query(WorkTask).options(joinedload(WorkTask.assignments)).filter(
        WorkTask.id == task_id, WorkTask.cooperative_id == cooperative_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    existing_ids = {a.worker_id for a in task.assignments}
    for worker_id in data.worker_ids:
        if worker_id not in existing_ids:
            assignment = WorkerAssignment(work_task_id=task_id, worker_id=worker_id)
            db.add(assignment)

    db.commit()
    db.refresh(task)
    return task
