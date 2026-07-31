# M5 Phase 1 — Tasks & Attendance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add task management (create/assign/status) and worker attendance logging for solo_farm organizations.

**Architecture:** 3 new DB tables (work_tasks, worker_assignments, worker_attendance) with associated models, Pydantic schemas, API routes, frontend components. Follows the same pattern as the Workers CRUD from Phase 0 — cooperative-scoped, role-gated, separate model files.

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic v2 (backend), React + Vite (frontend), SQLite dev / Postgres prod

## Global Constraints

- All new models go in separate files under `backend/app/models/` (matching `worker.py`)
- All new schemas go in separate files under `backend/app/schemas/` (matching `worker.py`)
- All new routes go in separate files under `backend/app/routes/` (matching `workers.py`)
- All endpoints require `cooperative_id` query param + `enforce_cooperative_scope`
- POST/PATCH/DELETE gated by `require_roles("admin", "farm_owner", "farm_manager")`
- Frontend components follow existing dashboard patterns (Workers.jsx as reference)
- Alembic migration appended to latest revision (branch from `006_farmer_finance_flows`)
- Tests follow pattern from `test_workers.py`

---

### Task 1: WorkTask + WorkerAssignment models and schemas

**Files:**
- Create: `backend/app/models/work_task.py`
- Create: `backend/app/schemas/work_task.py`

**Interfaces:**
- Produces: `WorkTask` model, `WorkerAssignment` model, `WorkerRole` enum (import from worker.py), `TaskType` enum, `TaskStatus` enum
- Produces: `TaskCreate`, `TaskUpdate`, `TaskResponse`, `TaskAssignmentCreate`, `TaskAssignmentResponse` schemas

**model:**
```python
import enum
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


class TaskType(str, enum.Enum):
    planting = "planting"
    weeding = "weeding"
    harvesting = "harvesting"
    irrigation = "irrigation"
    fertilizing = "fertilizing"
    general = "general"


class TaskStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class WorkTask(Base):
    __tablename__ = "work_tasks"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(Enum(TaskType), nullable=False)
    location = Column(String, nullable=True)
    scheduled_date = Column(Date, nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.open)
    created_at = Column(DateTime, default=datetime.utcnow)

    cooperative = relationship("Cooperative")
    assigner = relationship("User")
    assignments = relationship("WorkerAssignment", back_populates="task")


class WorkerAssignment(Base):
    __tablename__ = "worker_assignments"

    id = Column(Integer, primary_key=True, index=True)
    work_task_id = Column(Integer, ForeignKey("work_tasks.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("WorkTask", back_populates="assignments")
    worker = relationship("Worker")
```

**schemas:**
```python
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: Literal["planting", "weeding", "harvesting", "irrigation", "fertilizing", "general"]
    location: Optional[str] = None
    scheduled_date: date
    worker_ids: list[int] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[Literal["planting", "weeding", "harvesting", "irrigation", "fertilizing", "general"]] = None
    location: Optional[str] = None
    scheduled_date: Optional[date] = None
    status: Optional[Literal["open", "in_progress", "completed", "cancelled"]] = None


class WorkerAssignmentResponse(BaseModel):
    id: int
    work_task_id: int
    worker_id: int
    assigned_at: datetime

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: int
    cooperative_id: int
    title: str
    description: Optional[str] = None
    task_type: str
    location: Optional[str] = None
    scheduled_date: date
    assigned_by: int
    status: str
    created_at: datetime
    assignments: list[WorkerAssignmentResponse] = []

    class Config:
        from_attributes = True


class TaskAssignmentCreate(BaseModel):
    worker_ids: list[int]
```

- [ ] **Step 1: Create `backend/app/models/work_task.py`** with WorkTask and WorkerAssignment models, enums
- [ ] **Step 2: Create `backend/app/schemas/work_task.py`** with all schemas
- [ ] **Step 3: Verify imports work**

Run: `python -c "from app.models.work_task import WorkTask, WorkerAssignment, TaskType, TaskStatus; from app.schemas.work_task import TaskCreate, TaskUpdate, TaskResponse, WorkerAssignmentResponse"`
Expected: no import errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/work_task.py backend/app/schemas/work_task.py
git commit -m "feat: add WorkTask and WorkerAssignment models and schemas"
```

---

### Task 2: WorkerAttendance model and schemas

**Files:**
- Create: `backend/app/models/worker_attendance.py`
- Create: `backend/app/schemas/worker_attendance.py`

**Interfaces:**
- Consumes: `Worker` model (FK), `WorkTask` model (FK nullable)
- Produces: `WorkerAttendance` model, `AttendanceCreate`, `AttendanceResponse`, `AttendanceSummary` schemas

**model:**
```python
import enum
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


class Shift(str, enum.Enum):
    morning = "morning"
    afternoon = "afternoon"
    full_day = "full_day"


class WorkerAttendance(Base):
    __tablename__ = "worker_attendance"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    work_task_id = Column(Integer, ForeignKey("work_tasks.id"), nullable=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    hours_worked = Column(Float, nullable=True)
    shift = Column(Enum(Shift), nullable=False)
    logged_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    worker = relationship("Worker")
    work_task = relationship("WorkTask")
    cooperative = relationship("Cooperative")
    logger = relationship("User")
```

**schemas:**
```python
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class AttendanceCreate(BaseModel):
    worker_id: int
    work_task_id: Optional[int] = None
    date: date
    hours_worked: Optional[float] = None
    shift: Literal["morning", "afternoon", "full_day"]
    notes: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: int
    worker_id: int
    work_task_id: Optional[int] = None
    cooperative_id: int
    date: date
    hours_worked: Optional[float] = None
    shift: str
    logged_by: int
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceSummary(BaseModel):
    worker_id: int
    worker_name: str
    total_hours: float
    total_shifts: int
    period_start: date
    period_end: date
```

- [ ] **Step 1: Create `backend/app/models/worker_attendance.py`**
- [ ] **Step 2: Create `backend/app/schemas/worker_attendance.py`**
- [ ] **Step 3: Verify imports**

Run: `python -c "from app.models.worker_attendance import WorkerAttendance, Shift; from app.schemas.worker_attendance import AttendanceCreate, AttendanceResponse, AttendanceSummary"`
Expected: no import errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/worker_attendance.py backend/app/schemas/worker_attendance.py
git commit -m "feat: add WorkerAttendance model and schemas"
```

---

### Task 3: Task Management API routes

**Files:**
- Create: `backend/app/routes/tasks.py`

**Interfaces:**
- Consumes: `WorkTask`, `WorkerAssignment` models; `TaskCreate`, `TaskUpdate`, `TaskResponse` schemas; current_user, `enforce_cooperative_scope`, `require_roles` from auth_service
- Produces: GET /tasks, POST /tasks, PATCH /tasks/{id}, POST /tasks/{id}/assign

**Route file:**
```python
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
        assigned_by=current_user.id,
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
```

- [ ] **Step 1: Create `backend/app/routes/tasks.py`** with all 4 endpoints
- [ ] **Step 2: Verify syntax**

Run: `python -c "from app.routes.tasks import router"`
Expected: no import errors

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/tasks.py
git commit -m "feat: add task management API routes"
```

---

### Task 4: Attendance API routes

**Files:**
- Create: `backend/app/routes/attendance.py`

**Interfaces:**
- Consumes: `WorkerAttendance` model; `AttendanceCreate`, `AttendanceResponse`, `AttendanceSummary` schemas
- Produces: GET /attendance, POST /attendance, GET /attendance/summary

**Route file:**
```python
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
        logged_by=current_user.id,
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
```

- [ ] **Step 1: Create `backend/app/routes/attendance.py`** with all 3 endpoints
- [ ] **Step 2: Verify syntax**

Run: `python -c "from app.routes.attendance import router"`
Expected: no import errors

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/attendance.py
git commit -m "feat: add attendance logging API routes"
```

---

### Task 5: Register routers + Alembic migration

**Files:**
- Modify: `backend/main.py` (add router registrations)
- Create: `backend/alembic/versions/007_phase1.py`

**Router registration in main.py:**
```python
app.include_router(tasks.router)
app.include_router(attendance.router)
```
After line `app.include_router(workers.router)`.

With imports added at top:
```python
from app.routes import attendance, tasks
```

**Migration filename:** `007_phase1.py` (revision ID: `007_phase1`, down_revision: `006_farmer_finance_flows`)

Uses idempotent pattern (like `006`) — check tables/columns before creating:
```python
"""add work_tasks, worker_assignments, worker_attendance tables

Revision ID: 007_phase1
Revises: 006_farmer_finance_flows
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_phase1"
down_revision: Union[str, None] = "006_farmer_finance_flows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "work_tasks" not in table_names:
        op.create_table(
            "work_tasks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cooperative_id", sa.Integer(), sa.ForeignKey("cooperatives.id"), nullable=False, index=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("task_type", sa.String(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("scheduled_date", sa.Date(), nullable=False),
            sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(), server_default="open"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "worker_assignments" not in table_names:
        op.create_table(
            "worker_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("work_task_id", sa.Integer(), sa.ForeignKey("work_tasks.id"), nullable=False, index=True),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False, index=True),
            sa.Column("assigned_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "worker_attendance" not in table_names:
        op.create_table(
            "worker_attendance",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False, index=True),
            sa.Column("work_task_id", sa.Integer(), sa.ForeignKey("work_tasks.id"), nullable=True, index=True),
            sa.Column("cooperative_id", sa.Integer(), sa.ForeignKey("cooperatives.id"), nullable=False, index=True),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("hours_worked", sa.Float(), nullable=True),
            sa.Column("shift", sa.String(), nullable=False),
            sa.Column("logged_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("worker_attendance")
    op.drop_table("worker_assignments")
    op.drop_table("work_tasks")
```

- [ ] **Step 1: Register tasks + attendance routers in `backend/main.py`**
- [ ] **Step 2: Create migration file `backend/alembic/versions/007_phase1.py`**
- [ ] **Step 3: Run migration**

Run: `cd backend; alembic upgrade head`

- [ ] **Step 4: Verify**

Run: `cd backend; alembic current`
Expected: `007_phase1 (head)`

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/alembic/versions/007_phase1.py
git commit -m "feat: register task/attendance routers, add migration for 3 new tables"
```

---

### Task 6: Frontend API clients

**Files:**
- Create: `frontend/src/api/tasks.js`
- Create: `frontend/src/api/attendance.js`

**Interfaces:**
- Produces: `fetchTasks(cooperativeId, status?)`, `createTask(cooperativeId, data)`, `updateTask(cooperativeId, taskId, data)`, `assignWorkers(cooperativeId, taskId, workerIds)`
- Produces: `fetchAttendance(cooperativeId, filters?)`, `logAttendance(cooperativeId, data)`, `fetchAttendanceSummary(cooperativeId, periodStart, periodEnd)`

Pattern: copy `workers.js` exactly, replace function names and endpoints.

- [ ] **Step 1: Create `frontend/src/api/tasks.js`**

```javascript
import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchTasks(cooperativeId, status) {
  if (!cooperativeId) return []
  let url = `${API_URL}/tasks/?cooperative_id=${cooperativeId}`
  if (status) url += `&status=${status}`
  const res = await apiFetch(url, { headers: authHeaders() })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load tasks') }
  return res.json()
}

export async function createTask(cooperativeId, data) {
  const res = await apiFetch(`${API_URL}/tasks/?cooperative_id=${cooperativeId}`, {
    method: 'POST', headers: authHeaders(true), body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to create task') }
  return res.json()
}

export async function updateTask(cooperativeId, taskId, data) {
  const res = await apiFetch(`${API_URL}/tasks/${taskId}?cooperative_id=${cooperativeId}`, {
    method: 'PATCH', headers: authHeaders(true), body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to update task') }
  return res.json()
}

export async function assignWorkers(cooperativeId, taskId, workerIds) {
  const res = await apiFetch(`${API_URL}/tasks/${taskId}/assign?cooperative_id=${cooperativeId}`, {
    method: 'POST', headers: authHeaders(true), body: JSON.stringify({ worker_ids: workerIds }),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to assign workers') }
  return res.json()
}
```

- [ ] **Step 2: Create `frontend/src/api/attendance.js`**

```javascript
import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchAttendance(cooperativeId, filters = {}) {
  if (!cooperativeId) return []
  let url = `${API_URL}/attendance/?cooperative_id=${cooperativeId}`
  if (filters.worker_id) url += `&worker_id=${filters.worker_id}`
  if (filters.date_from) url += `&date_from=${filters.date_from}`
  if (filters.date_to) url += `&date_to=${filters.date_to}`
  const res = await apiFetch(url, { headers: authHeaders() })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load attendance') }
  return res.json()
}

export async function logAttendance(cooperativeId, data) {
  const res = await apiFetch(`${API_URL}/attendance/?cooperative_id=${cooperativeId}`, {
    method: 'POST', headers: authHeaders(true), body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to log attendance') }
  return res.json()
}

export async function fetchAttendanceSummary(cooperativeId, periodStart, periodEnd) {
  const res = await apiFetch(
    `${API_URL}/attendance/summary?cooperative_id=${cooperativeId}&period_start=${periodStart}&period_end=${periodEnd}`,
    { headers: authHeaders() },
  )
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load summary') }
  return res.json()
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/tasks.js frontend/src/api/attendance.js
git commit -m "feat: add frontend API clients for tasks and attendance"
```

---

### Task 7: Tasks section frontend component

**Files:**
- Create: `frontend/src/components/dashboard/Tasks.jsx`
- Create: `frontend/src/components/dashboard/TaskForm.jsx`

**Interfaces:**
- Consumes: `fetchTasks`, `createTask`, `updateTask`, `assignWorkers` from API; `fetchWorkers` for the assignment picker
- Produces: Tasks section rendered in dashboard when section="tasks"

**Tasks.jsx** (patterned after Workers.jsx with these changes):
- Table columns: Title, Type, Status, Scheduled Date, Assigned Workers, Actions
- Search bar filters by title
- Status filter dropdown
- "Create Task" button opens TaskForm modal
- Row actions: Edit (opens TaskForm), Mark Complete, Cancel
- Status badges: open (blue), in_progress (yellow), completed (green), cancelled (gray)
- Worker assignment via multi-select in TaskForm

**TaskForm.jsx** (patterned after WorkerForm.jsx):
- Fields: title (text), description (textarea), task_type (dropdown), location (text), scheduled_date (datepicker), worker_ids (multi-select checkboxes from workers list)
- Create mode: all fields editable
- Edit mode: title, description, location, scheduled_date, status editable; task_type locked

- [ ] **Step 1: Create `frontend/src/components/dashboard/Tasks.jsx`**
- [ ] **Step 2: Create `frontend/src/components/dashboard/TaskForm.jsx`**
- [ ] **Step 3: Verify syntax**

Run: `cd frontend; npx vite build 2>&1 | Select-String -Pattern "error" -NotMatch`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/Tasks.jsx frontend/src/components/dashboard/TaskForm.jsx
git commit -m "feat: add Tasks section component with TaskForm"
```

---

### Task 8: Attendance section frontend component

**Files:**
- Create: `frontend/src/components/dashboard/Attendance.jsx`

**Interfaces:**
- Consumes: `fetchAttendance`, `logAttendance` from API; `fetchWorkers` for worker dropdown
- Produces: Attendance section rendered when section="attendance"

**Attendance.jsx** (patterned after Workers.jsx):
- Table columns: Date, Worker Name, Task (if any), Shift, Hours Worked, Notes
- Date range filter (date_from, date_to inputs)
- Worker filter dropdown
- "Log Attendance" inline row adder (no modal — single row form at top)
  - Worker dropdown, date input, shift dropdown, hours input (optional), notes input
  - Submit button logs and refreshes list

- [ ] **Step 1: Create `frontend/src/components/dashboard/Attendance.jsx`**
- [ ] **Step 2: Verify syntax**

Run: `cd frontend; npx vite build 2>&1 | Select-String -Pattern "error" -NotMatch`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/Attendance.jsx
git commit -m "feat: add Attendance section component"
```

---

### Task 9: Frontend nav updates

**Files:**
- Modify: `frontend/src/constants/routes.js` (add 'tasks', 'attendance' to DASHBOARD_SECTIONS)
- Modify: `frontend/src/pages/DashboardPage.jsx` (add Tasks, Attendance to solo_farm getNavGroups)

**routes.js:**
```diff
 export const DASHBOARD_SECTIONS = [
   'overview',
   'members',
   'workers',
+  'tasks',
+  'attendance',
   'payments',
```

**DashboardPage.jsx — getNavGroups('solo_farm'):**
Add Tasks and Attendance under Operations:
```diff
 solo_farm: [
   { label: 'Overview', section: 'overview' },
   { label: 'Workers', section: 'workers' },
+  { label: 'Tasks', section: 'tasks' },
+  { label: 'Attendance', section: 'attendance' },
   { label: 'Production', section: 'production' },
   { label: 'Payroll', section: 'payroll' },
 ],
```

Also add section rendering:
```jsx
case 'tasks': return <Tasks />
case 'attendance': return <Attendance />
```
(alongside existing `case 'workers': return <Workers />`)

With imports:
```javascript
import Tasks from '../components/dashboard/Tasks'
import Attendance from '../components/dashboard/Attendance'
```

- [ ] **Step 1: Add 'tasks'/'attendance' to DASHBOARD_SECTIONS in `routes.js`**
- [ ] **Step 2: Add tasks/attendance to getNavGroups in `DashboardPage.jsx` + section rendering + imports**
- [ ] **Step 3: Verify build**

Run: `cd frontend; npx vite build 2>&1 | Select-String -Pattern "error" -NotMatch`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/constants/routes.js frontend/src/pages/DashboardPage.jsx
git commit -m "feat: add Tasks and Attendance to dashboard navigation"
```

---

### Task 10: Backend tests

**Files:**
- Create: `backend/tests/test_tasks.py`
- Create: `backend/tests/test_attendance.py`

**Interfaces:**
- Consumes: `auth_client`, `test_cooperative`, `another_cooperative` fixtures from conftest (already exist)

**test_tasks.py:**
```python
def test_create_task(auth_client, test_cooperative):
    """POST /tasks creates a task."""
    res = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Plant maize", "task_type": "planting", "scheduled_date": "2026-08-01"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Plant maize"
    assert data["status"] == "open"
    assert data["task_type"] == "planting"


def test_create_task_with_workers(auth_client, test_cooperative):
    """POST /tasks with worker_ids creates assignments."""
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Task Worker", "phone": "0241112240"},
    ).json()
    res = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={
            "title": "Weeding", "task_type": "weeding",
            "scheduled_date": "2026-08-05",
            "worker_ids": [worker["id"]],
        },
    )
    assert res.status_code == 201
    assert len(res.json()["assignments"]) == 1


def test_list_tasks(auth_client, test_cooperative):
    """GET /tasks lists tasks."""
    auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Harvest", "task_type": "harvesting", "scheduled_date": "2026-08-10"},
    )
    res = auth_client.get(f"/tasks/?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_update_task_status(auth_client, test_cooperative):
    """PATCH /tasks/{id} updates status."""
    created = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Irrigate", "task_type": "irrigation", "scheduled_date": "2026-08-15"},
    ).json()
    res = auth_client.patch(
        f"/tasks/{created['id']}?cooperative_id={test_cooperative.id}",
        json={"status": "in_progress"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"


def test_assign_workers_to_task(auth_client, test_cooperative):
    """POST /tasks/{id}/assign adds worker assignments."""
    task = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Fertilize", "task_type": "fertilizing", "scheduled_date": "2026-08-20"},
    ).json()
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Assign Me", "phone": "0241112241"},
    ).json()
    res = auth_client.post(
        f"/tasks/{task['id']}/assign?cooperative_id={test_cooperative.id}",
        json={"worker_ids": [worker["id"]]},
    )
    assert res.status_code == 200
    assert len(res.json()["assignments"]) == 1


def test_task_cross_coop_not_found(auth_client, test_cooperative, another_cooperative):
    """Task from coop A is not visible from coop B."""
    created = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Secret", "task_type": "general", "scheduled_date": "2026-09-01"},
    ).json()
    res = auth_client.get(f"/tasks/{created['id']}?cooperative_id={another_cooperative.id}")
    assert res.status_code == 404
```

**test_attendance.py:**
```python
def test_log_attendance(auth_client, test_cooperative):
    """POST /attendance logs worker attendance."""
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Attend Me", "phone": "0241112242"},
    ).json()
    res = auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={
            "worker_id": worker["id"],
            "date": "2026-08-01",
            "shift": "morning",
            "hours_worked": 4.0,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["shift"] == "morning"
    assert data["hours_worked"] == 4.0


def test_list_attendance(auth_client, test_cooperative):
    """GET /attendance lists records for cooperative."""
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "List Me", "phone": "0241112243"},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-08-02", "shift": "full_day"},
    )
    res = auth_client.get(f"/attendance/?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_attendance_summary(auth_client, test_cooperative):
    """GET /attendance/summary returns aggregated data."""
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Sum Me", "phone": "0241112244"},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-08-01", "shift": "morning", "hours_worked": 4.0},
    )
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-08-02", "shift": "afternoon", "hours_worked": 4.0},
    )
    res = auth_client.get(
        f"/attendance/summary?cooperative_id={test_cooperative.id}"
        f"&period_start=2026-08-01&period_end=2026-08-31"
    )
    assert res.status_code == 200
    assert len(res.json()) >= 1
    summary = next(s for s in res.json() if s["worker_id"] == worker["id"])
    assert summary["total_hours"] == 8.0
    assert summary["total_shifts"] == 2


def test_attendance_filter_by_worker(auth_client, test_cooperative):
    """GET /attendance?worker_id=N filters by worker."""
    w1 = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Filter A", "phone": "0241112245"},
    ).json()
    w2 = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Filter B", "phone": "0241112246"},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": w1["id"], "date": "2026-08-03", "shift": "morning"},
    )
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": w2["id"], "date": "2026-08-03", "shift": "afternoon"},
    )
    res = auth_client.get(f"/attendance/?cooperative_id={test_cooperative.id}&worker_id={w1['id']}")
    assert res.status_code == 200
    assert all(r["worker_id"] == w1["id"] for r in res.json())
```

- [ ] **Step 1: Create `backend/tests/test_tasks.py`** with 6 test functions
- [ ] **Step 2: Run task tests**

Run: `cd backend; python -m pytest tests/test_tasks.py -v`
Expected: 5 passed

- [ ] **Step 3: Create `backend/tests/test_attendance.py`** with 4 test functions
- [ ] **Step 4: Run attendance tests**

Run: `cd backend; python -m pytest tests/test_attendance.py -v`
Expected: 4 passed

- [ ] **Step 5: Run full test suite**

Run: `cd backend; python -m pytest tests/ -v --tb=short 2>&1 | tail -5`
Expected: no new failures (pre-existing 3 JWT failures unchanged)

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_tasks.py backend/tests/test_attendance.py
git commit -m "feat: add task and attendance CRUD tests"
```
