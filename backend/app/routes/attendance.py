from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.database.db import get_db
from app.models.models import Cooperative, User
from app.models.worker import Worker
from app.models.worker_attendance import Shift, WorkerAttendance
from app.schemas.worker_attendance import AttendanceCreate, AttendanceResponse, AttendanceSummary
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/", response_model=list[AttendanceResponse])
def list_attendance(
    cooperative_id: int = Query(...),
    worker_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    query = db.query(WorkerAttendance).filter(WorkerAttendance.cooperative_id == cooperative_id)
    if worker_id:
        query = query.filter(WorkerAttendance.worker_id == worker_id)
    if date_from:
        query = query.filter(WorkerAttendance.date >= date_from)
    if date_to:
        query = query.filter(WorkerAttendance.date <= date_to)
    return query.order_by(WorkerAttendance.date.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=AttendanceResponse, status_code=201)
def log_attendance(
    data: AttendanceCreate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager", "supervisor")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    record = WorkerAttendance(
        worker_id=data.worker_id,
        work_task_id=data.work_task_id,
        cooperative_id=cooperative_id,
        date=data.date,
        hours_worked=data.hours_worked,
        shift=Shift(data.shift),
        logged_by=current_user.id if current_user else None,
        notes=data.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/summary", response_model=list[AttendanceSummary])
def attendance_summary(
    cooperative_id: int = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    rows = (
        db.query(
            WorkerAttendance.worker_id,
            Worker.name.label("worker_name"),
            func.coalesce(func.sum(WorkerAttendance.hours_worked), 0).label("total_hours"),
            func.count(WorkerAttendance.id).label("total_shifts"),
        )
        .join(Worker, WorkerAttendance.worker_id == Worker.id)
        .filter(
            WorkerAttendance.cooperative_id == cooperative_id,
            WorkerAttendance.date >= period_start,
            WorkerAttendance.date <= period_end,
        )
        .group_by(WorkerAttendance.worker_id, Worker.name)
        .all()
    )
    return [
        AttendanceSummary(
            worker_id=r.worker_id,
            worker_name=r.worker_name,
            total_hours=float(r.total_hours),
            total_shifts=r.total_shifts,
            period_start=period_start,
            period_end=period_end,
        )
        for r in rows
    ]
