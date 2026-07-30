# M5 Phase 0 — Solo Farm Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay the foundation for Solo Farm by adding `organization_type` to cooperatives, creating the `workers` table, expanding roles, adding Worker CRUD API, and making the signup + nav org-type-aware.

**Architecture:** Expand existing Cooperative model with org type discriminator. Workers are a new entity parallel to Farmers (not members). Frontend nav becomes a function of org type.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React 18, Vite, Pydantic v2

## Global Constraints

- `organization_type` defaults to `"cooperative"` for backward compat
- Workers are scoped to `cooperative_id` — no cross-tenant access
- Existing cooperative/farmer models stay untouched
- Frontend role handling: cooperative sees existing nav, solo_farm sees new nav
- Python type hints throughout (Python 3.10+)

---

## File Structure

### New files:
- `backend/app/models/worker.py` — Worker ORM model + enums
- `backend/app/schemas/worker.py` — Worker Pydantic schemas
- `backend/app/routes/workers.py` — Worker CRUD endpoints
- `frontend/src/api/workers.js` — Worker API client
- `frontend/src/components/dashboard/Workers.jsx` — Workers section component
- `frontend/src/components/dashboard/WorkerForm.jsx` — Add/edit worker modal

### Modified files:
- `backend/app/models/models.py` — Add `organization_type` to Cooperative
- `backend/app/schemas/schemas.py` — Add `organization_type` to CooperativeResponse/CooperativeUpdate
- `backend/app/schemas/auth.py` — Add `organization_type` to SignupRequest/SignupResponse, expand role Literal
- `backend/app/routes/auth.py` — Pass organization_type on signup
- `backend/app/routes/cooperatives.py` — Return organization_type
- `backend/app/main.py` — Register workers router
- `frontend/src/constants/routes.js` — Add worker sections to DASHBOARD_SECTIONS
- `frontend/src/pages/DashboardPage.jsx` — Org-aware NAV_GROUPS, section rendering
- `frontend/src/pages/PricingPage.jsx` — Add solo plan
- `frontend/src/pages/SubscriptionPage.jsx` — Org type step
- `frontend/src/pages/AuthPage.jsx` — Org type in signup flow
- `frontend/src/api/auth.js` — Pass org_type in signup
- `frontend/src/api/cooperatives.js` — Pass org_type in responses

---

### Task 1: Add `organization_type` to Cooperative model + DB migration

**Files:**
- Modify: `backend/app/models/models.py:101`
- Modify: `backend/alembic/versions/007_organization_type.py` (new migration)
- Modify: `backend/app/schemas/schemas.py:40-46`
- Modify: `backend/app/schemas/auth.py:43`

- [ ] **Step 1: Add `organization_type` column to Cooperative model**

In `backend/app/models/models.py`, add after `subscription_plan` (line 101):

```python
organization_type = Column(String, default="cooperative", nullable=False)
```

- [ ] **Step 2: Create Alembic migration**

Create `backend/alembic/versions/007_organization_type.py`:

```python
"""add organization_type to cooperatives, create workers table

Revision ID: 007_organization_type
Revises: 006_farmer_finance_flows
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "007_organization_type"
down_revision = "006_farmer_finance_flows"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cooperatives",
        sa.Column("organization_type", sa.String(), server_default="cooperative", nullable=False),
    )


def downgrade():
    op.drop_column("cooperatives", "organization_type")
```

- [ ] **Step 3: Update CooperativeResponse schema**

In `backend/app/schemas/schemas.py`, add to `CooperativeResponse`:

```python
organization_type: str = "cooperative"
```

And add to `CooperativeUpdate`:

```python
organization_type: Optional[str] = None
```

- [ ] **Step 4: Update SignupRequest schema**

In `backend/app/schemas/auth.py`:

```python
organization_type: Literal["cooperative", "solo_farm"] = "cooperative"
```

Update `SignupResponse`:

```python
organization_type: str = "cooperative"
```

- [ ] **Step 5: Run migration**

```bash
cd backend && alembic upgrade head
```

---

### Task 2: Create Worker model + schemas

**Files:**
- Create: `backend/app/models/worker.py`
- Create: `backend/app/schemas/worker.py`

- [ ] **Step 1: Create Worker ORM model**

`backend/app/models/worker.py`:

```python
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from app.database.db import Base


class WorkerRole(str, enum.Enum):
    worker = "worker"
    supervisor = "supervisor"


class WorkerStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, index=True)
    wage_rate = Column(Float, default=0.0)
    role = Column(Enum(WorkerRole), default=WorkerRole.worker)
    status = Column(Enum(WorkerStatus), default=WorkerStatus.active)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cooperative = relationship("Cooperative")

    __table_args__ = (
        sa.UniqueConstraint("cooperative_id", "phone", name="uq_worker_phone_per_coop"),
    )
```

- [ ] **Step 2: Create Worker Pydantic schemas**

`backend/app/schemas/worker.py`:

```python
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class WorkerCreate(BaseModel):
    name: str
    phone: str
    wage_rate: float = 0.0
    role: Literal["worker", "supervisor"] = "worker"


class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    wage_rate: Optional[float] = None
    role: Optional[Literal["worker", "supervisor"]] = None
    status: Optional[Literal["active", "inactive"]] = None


class WorkerResponse(BaseModel):
    id: int
    cooperative_id: int
    name: str
    phone: str
    wage_rate: float
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Register model import in main.py**

Add to `backend/main.py`:

```python
from app.models import worker  # noqa: F401
```

---

### Task 3: Worker CRUD API routes

**Files:**
- Create: `backend/app/routes/workers.py`
- Modify: `backend/main.py:173`

- [ ] **Step 1: Create workers router**

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

- [ ] **Step 2: Register workers router in main.py**

In `backend/main.py`, add after the last `app.include_router(...)`:

```python
from app.routes import workers as workers_router
app.include_router(workers_router.router)
```

---

### Task 4: Expand role validators for solo_farm roles

**Files:**
- Modify: `backend/app/schemas/auth.py:9`

- [ ] **Step 1: Expand role Literal to include farm roles**

In `backend/app/schemas/auth.py`, change `UserCreate.role` and `UserUpdate.role`:

```python
role: Literal["admin", "finance_officer", "farm_owner", "farm_manager", "supervisor"] = "finance_officer"
```

And in `UserUpdate`:

```python
role: Literal["admin", "finance_officer", "farm_owner", "farm_manager", "supervisor"] | None = None
```

---

### Task 5: Wire organization_type through signup

**Files:**
- Modify: `backend/app/routes/auth.py:43-50`

- [ ] **Step 1: Pass organization_type when creating cooperative**

In `backend/app/routes/auth.py`, add to the `new_coop` creation:

```python
new_coop = Cooperative(
    name=data.cooperative_name,
    location=data.location,
    description=description,
    currency="GHS",
    subscription_plan=data.subscription_plan,
    organization_type=data.organization_type,
)
```

And in the signup response, return `organization_type`:

```python
return {
    "access_token": access_token,
    "token_type": "bearer",
    "cooperative_id": new_coop.id,
    "cooperative_name": new_coop.name,
    "subscription_plan": data.subscription_plan,
    "organization_type": data.organization_type,
    "onboarding_role": data.onboarding_role,
}
```

- [ ] **Step 2: Return organization_type from cooperative endpoints**

In `backend/app/routes/cooperatives.py`, the `CooperativeResponse` already includes it (from schema update in Task 1). Ensure the PUT handler passes `organization_type` through:

```python
organization_type: Optional[str] = None,  # in CooperativeUpdate
```

---

### Task 6: Frontend — Org-aware signup flow

**Files:**
- Modify: `frontend/src/pages/AuthPage.jsx`
- Modify: `frontend/src/pages/SubscriptionPage.jsx`
- Modify: `frontend/src/api/auth.js`

- [ ] **Step 1: Add org_type to auth API**

In `frontend/src/api/auth.js`, find the signup call and add `organization_type`:

```javascript
// In signup function, add to payload:
organization_type: formData.organization_type || 'cooperative',
```

- [ ] **Step 2: Add org type selector to signup**

In `AuthPage.jsx`, add a step/field in the signup form for org type:

```jsx
{/* After cooperative name field */}
<div className="form-group">
  <label>Organization type</label>
  <select
    name="organization_type"
    value={formData.organization_type}
    onChange={handleChange}
    className="form-input"
  >
    <option value="cooperative">Cooperative</option>
    <option value="solo_farm">Solo Farm</option>
  </select>
</div>
```

- [ ] **Step 3: Add org type step to subscription page**

In `SubscriptionPage.jsx`, include org type in the onboarding flow so it passes through to signup.

---

### Task 7: Frontend — Org-aware dashboard navigation

**Files:**
- Modify: `frontend/src/constants/routes.js`
- Modify: `frontend/src/pages/DashboardPage.jsx`

- [ ] **Step 1: Add new sections to DASHBOARD_SECTIONS**

In `frontend/src/constants/routes.js`:

```javascript
export const DASHBOARD_SECTIONS = [
  'overview',
  'members',
  'workers',
  'payments',
  'loans',
  'production',
  'scores',
  'sms',
  'ussd',
  'activity',
  'settings',
]
```

- [ ] **Step 2: Make NAV_GROUPS a function of org_type**

In `DashboardPage.jsx`, replace the static `NAV_GROUPS` with a function:

```javascript
function getNavGroups(organizationType) {
  if (organizationType === 'solo_farm') {
    return [
      {
        label: 'Operations',
        items: [
          { key: 'overview', icon: <BarChart3 size={18} />, label: 'Overview' },
          { key: 'workers', icon: <Users size={18} />, label: 'Workers' },
          { key: 'production', icon: <Tractor size={18} />, label: 'Production' },
        ],
      },
      {
        label: 'Communications',
        items: [
          { key: 'sms', icon: <MessageSquare size={18} />, label: 'SMS broadcasts' },
          { key: 'ussd', icon: <Phone size={18} />, label: 'USSD activity' },
        ],
      },
      {
        label: 'Governance',
        items: [
          { key: 'activity', icon: <ClipboardList size={18} />, label: 'Activity log' },
        ],
      },
    ]
  }
  // Default cooperative nav
  return [
    {
      label: 'Operations',
      items: [
        { key: 'overview', icon: <BarChart3 size={18} />, label: 'Overview' },
        { key: 'members', icon: <Users size={18} />, label: 'Members' },
        { key: 'production', icon: <Tractor size={18} />, label: 'Production' },
        { key: 'scores', icon: <Star size={18} />, label: 'Agro-AI scores' },
      ],
    },
    {
      label: 'Finance',
      items: [
        { key: 'payments', icon: <CreditCard size={18} />, label: 'Payments' },
        { key: 'loans', icon: <Banknote size={18} />, label: 'Loans' },
      ],
    },
    {
      label: 'Communications',
      items: [
        { key: 'sms', icon: <MessageSquare size={18} />, label: 'SMS broadcasts' },
        { key: 'ussd', icon: <Phone size={18} />, label: 'USSD activity' },
      ],
    },
    {
      label: 'Governance',
      items: [
        { key: 'activity', icon: <ClipboardList size={18} />, label: 'Activity log' },
      ],
    },
  ]
}
```

- [ ] **Step 3: Load org_type in DashboardPage state**

Add state and fetch for org type:

```javascript
const [organizationType, setOrganizationType] = useState('cooperative')

// In loadAll or a separate effect:
useEffect(() => {
  if (cooperativeId) {
    fetchCooperative(cooperativeId).then(coop => {
      if (coop) setOrganizationType(coop.organization_type || 'cooperative')
    })
  }
}, [cooperativeId])
```

- [ ] **Step 4: Use function-based nav groups**

Replace `NAV_GROUPS` usage with:

```javascript
const navGroups = getNavGroups(organizationType)
const NAV_ITEMS = navGroups.flatMap((group) => group.items)
```

- [ ] **Step 5: Add Workers section rendering**

In the section rendering block, add:

```jsx
section === 'workers' && <Workers cooperativeId={cooperativeId} />
```

- [ ] **Step 6: Import Workers component**

```javascript
import Workers from '../components/dashboard/Workers'
```

- [ ] **Step 7: Section gating - redirect members to workers for solo_farm**

At the top of the DashboardPage render, add:

```javascript
if (organizationType === 'solo_farm' && section === 'members') {
  return <Navigate to={dashboardPath('workers')} replace />
}
if (organizationType === 'cooperative' && section === 'workers') {
  return <Navigate to={dashboardPath('members')} replace />
}
```

---

### Task 8: Frontend — Workers section component

**Files:**
- Create: `frontend/src/components/dashboard/Workers.jsx`
- Create: `frontend/src/components/dashboard/WorkerForm.jsx`
- Create: `frontend/src/api/workers.js`

- [ ] **Step 1: Create workers API client**

`frontend/src/api/workers.js`:

```javascript
import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchWorkers(cooperativeId) {
  const res = await apiFetch(`${API_URL}/workers/?cooperative_id=${cooperativeId}`, {
    headers: authHeaders(),
  })
  if (!res.ok) return []
  return res.json()
}

export async function createWorker(cooperativeId, data) {
  const res = await apiFetch(`${API_URL}/workers/?cooperative_id=${cooperativeId}`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to create worker')
  }
  return res.json()
}

export async function updateWorker(cooperativeId, workerId, data) {
  const res = await apiFetch(`${API_URL}/workers/${workerId}?cooperative_id=${cooperativeId}`, {
    method: 'PATCH',
    headers: authHeaders(true),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to update worker')
  }
  return res.json()
}

export async function deleteWorker(cooperativeId, workerId) {
  const res = await apiFetch(`${API_URL}/workers/${workerId}?cooperative_id=${cooperativeId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to delete worker')
  }
  return true
}
```

- [ ] **Step 2: Create Workers section component**

`frontend/src/components/dashboard/Workers.jsx` — see full component below:

```jsx
import { useEffect, useState } from 'react'
import { Plus, UserMinus, UserCheck, Pencil } from 'lucide-react'
import { fetchWorkers, deleteWorker } from '../../api/workers'
import DashboardTableToolbar from './DashboardTableToolbar'
import DashboardPagination from './DashboardPagination'
import WorkerForm from './WorkerForm'
import ModalPresence from './ModalPresence'

const PAGE_SIZE = 20

export default function Workers({ cooperativeId }) {
  const [workers, setWorkers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [editingWorker, setEditingWorker] = useState(null)
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')

  function loadWorkers() {
    if (!cooperativeId) return
    setLoading(true)
    fetchWorkers(cooperativeId)
      .then(setWorkers)
      .catch(setError)
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadWorkers() }, [cooperativeId])

  const filtered = workers.filter(w =>
    !search || w.name.toLowerCase().includes(search.toLowerCase()) || w.phone.includes(search)
  )
  const pageCount = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  async function handleDelete(workerId) {
    if (!confirm('Deactivate this worker?')) return
    try {
      await deleteWorker(cooperativeId, workerId)
      loadWorkers()
    } catch (e) { alert(e.message) }
  }

  if (loading) return <div className="skeleton-box" style={{height:400}}/>
  if (error) return <div className="error-banner">Failed to load workers</div>

  return (
    <div className="section-card">
      <div className="section-header">
        <h2>Workers ({workers.length})</h2>
        <button className="btn btn-primary" onClick={() => { setEditingWorker(null); setShowForm(true) }}>
          <Plus size={16} /> Add worker
        </button>
      </div>

      <DashboardTableToolbar search={search} onSearch={setSearch} />

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Phone</th>
            <th>Wage rate</th>
            <th>Role</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {paged.map(w => (
            <tr key={w.id}>
              <td>{w.name}</td>
              <td>{w.phone}</td>
              <td>GHS {w.wage_rate?.toFixed(2)}</td>
              <td><span className="badge">{w.role}</span></td>
              <td>{w.status === 'active'
                ? <span className="status-active"><UserCheck size={14} /> Active</span>
                : <span className="status-inactive"><UserMinus size={14} /> Inactive</span>}
              </td>
              <td className="actions-cell">
                <button className="btn-icon" title="Edit" onClick={() => { setEditingWorker(w); setShowForm(true) }}>
                  <Pencil size={15} />
                </button>
                <button className="btn-icon btn-icon-danger" title="Deactivate"
                  onClick={() => handleDelete(w.id)} disabled={w.status === 'inactive'}>
                  <UserMinus size={15} />
                </button>
              </td>
            </tr>
          ))}
          {paged.length === 0 && (
            <tr><td colSpan={6} className="empty-state">No workers yet</td></tr>
          )}
        </tbody>
      </table>

      <DashboardPagination page={page} pageCount={pageCount} onPage={setPage} total={filtered.length}
        rangeStart={page * PAGE_SIZE + 1} rangeEnd={Math.min((page + 1) * PAGE_SIZE, filtered.length)} />

      <ModalPresence show={showForm} onClose={() => setShowForm(false)}>
        <WorkerForm
          cooperativeId={cooperativeId}
          worker={editingWorker}
          onSaved={() => { setShowForm(false); loadWorkers() }}
          onCancel={() => setShowForm(false)}
        />
      </ModalPresence>
    </div>
  )
}
```

- [ ] **Step 3: Create WorkerForm component**

`frontend/src/components/dashboard/WorkerForm.jsx`:

```jsx
import { useState } from 'react'
import { createWorker, updateWorker } from '../../api/workers'

export default function WorkerForm({ cooperativeId, worker, onSaved, onCancel }) {
  const isEdit = !!worker
  const [form, setForm] = useState({
    name: worker?.name || '',
    phone: worker?.phone || '',
    wage_rate: worker?.wage_rate || '',
    role: worker?.role || 'worker',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = { ...form, wage_rate: parseFloat(form.wage_rate) || 0 }
      if (isEdit) {
        await updateWorker(cooperativeId, worker.id, payload)
      } else {
        await createWorker(cooperativeId, payload)
      }
      onSaved()
    } catch (e) { setError(e.message) }
    finally { setSaving(false) }
  }

  return (
    <div className="modal-content">
      <h2>{isEdit ? 'Edit worker' : 'Add worker'}</h2>
      {error && <div className="error-banner">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Name</label>
          <input className="form-input" required value={form.name}
            onChange={e => setForm({...form, name: e.target.value})} />
        </div>
        <div className="form-group">
          <label>Phone</label>
          <input className="form-input" required value={form.phone}
            onChange={e => setForm({...form, phone: e.target.value})} />
        </div>
        <div className="form-group">
          <label>Wage rate (GHS per day)</label>
          <input className="form-input" type="number" step="0.01" min="0" value={form.wage_rate}
            onChange={e => setForm({...form, wage_rate: e.target.value})} />
        </div>
        <div className="form-group">
          <label>Role</label>
          <select className="form-input" value={form.role}
            onChange={e => setForm({...form, role: e.target.value})}>
            <option value="worker">Worker</option>
            <option value="supervisor">Supervisor</option>
          </select>
        </div>
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : isEdit ? 'Update' : 'Create'}
          </button>
        </div>
      </form>
    </div>
  )
}
```

---

### Task 9: Alembic migration for workers table

**Files:**
- Modify: `backend/alembic/versions/007_organization_type.py` (update existing)

- [ ] **Step 1: Add workers table creation to migration**

Append to the `upgrade()` function in the existing migration:

```python
def upgrade():
    op.add_column(...)  # from Task 1

    op.create_table(
        "workers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cooperative_id", sa.Integer(), sa.ForeignKey("cooperatives.id"), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False, index=True),
        sa.Column("wage_rate", sa.Float(), server_default="0.0"),
        sa.Column("role", sa.String(), server_default="worker"),
        sa.Column("status", sa.String(), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_worker_phone_per_coop", "workers", ["cooperative_id", "phone"])
```

---

### Task 10: Backend tests for Worker CRUD

**Files:**
- Create: `backend/tests/test_workers.py`

- [ ] **Step 1: Write tests**

`backend/tests/test_workers.py`:

```python
def test_create_worker(auth_client, test_cooperative):
    """POST /workers creates a worker for the cooperative."""
    res = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "John Doe", "phone": "0241112233", "wage_rate": 50.0, "role": "worker"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "John Doe"
    assert data["phone"] == "0241112233"
    assert data["wage_rate"] == 50.0
    assert data["status"] == "active"


def test_list_workers(auth_client, test_cooperative):
    """GET /workers lists workers for the cooperative."""
    auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Jane", "phone": "0241112234", "wage_rate": 45.0},
    )
    res = auth_client.get(f"/workers/?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_get_worker(auth_client, test_cooperative):
    """GET /workers/:id returns a worker."""
    created = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Bob", "phone": "0241112235", "wage_rate": 55.0},
    ).json()
    res = auth_client.get(f"/workers/{created['id']}?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Bob"


def test_update_worker(auth_client, test_cooperative):
    """PATCH /workers/:id updates worker fields."""
    created = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Alice", "phone": "0241112236", "wage_rate": 40.0},
    ).json()
    res = auth_client.patch(
        f"/workers/{created['id']}?cooperative_id={test_cooperative.id}",
        json={"name": "Alice Updated", "wage_rate": 45.0},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Alice Updated"
    assert res.json()["wage_rate"] == 45.0


def test_delete_worker_soft(auth_client, test_cooperative):
    """DELETE /workers/:id sets status to inactive."""
    created = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Charlie", "phone": "0241112237", "wage_rate": 50.0},
    ).json()
    res = auth_client.delete(f"/workers/{created['id']}?cooperative_id={test_cooperative.id}")
    assert res.status_code == 204
    get_res = auth_client.get(f"/workers/{created['id']}?cooperative_id={test_cooperative.id}")
    assert get_res.json()["status"] == "inactive"


def test_create_worker_duplicate_phone(auth_client, test_cooperative):
    """Creating a worker with duplicate phone returns 409."""
    auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "First", "phone": "0241112238"},
    )
    res = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Second", "phone": "0241112238"},
    )
    assert res.status_code == 409


def test_worker_cross_coop_not_found(auth_client, test_cooperative, another_cooperative):
    """Worker from coop A is not visible from coop B."""
    created = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Cross", "phone": "0241112239"},
    ).json()
    res = auth_client.get(f"/workers/{created['id']}?cooperative_id={another_cooperative.id}")
    assert res.status_code == 404
```
