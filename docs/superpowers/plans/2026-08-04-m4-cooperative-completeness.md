# M4 — Cooperative Product Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete 8 remaining M4 issues: RBAC nav gating, attendance UI, announcements CRUD+USSD, SMS consent, auth lifecycle hardening, animal settlement, Agro-AI warnings, and dead-code cleanup.

**Architecture:** Mostly independent workstreams. #248 (auth) is the largest — new User model fields + 4 endpoints + frontend flow. Other issues are 1-2 tasks each with minimal cross-dependencies.

**Tech Stack:** FastAPI (Python), React + Vite, Supabase (PostgreSQL), bcrypt + JWT, Moolre SDK (SMS)

## Global Constraints

- Password reset token: single-use, 15-min expiry, 64-char random hex
- Invite token: single-use, 72-hour expiry, 64-char random hex
- Access token TTL: 15 min in production, configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` env var (not overwriting hardcoded 7-day dev default)
- SMS consent: `sms_consent` boolean on CooperativeMembership, default `true`
- Announcements: `send_sms` bool controls whether SMS is broadcast on creation
- USSD option 4: returns latest 3 announcements (title + body)
- Agro-AI: no model changes — just expose `is_synthetic` flag, add UI warning
- `must_change_password` defaults to `true` for admin-created users (via `/auth/register`), `false` for self-signup
- Production access token TTL picks up env var; hardcoded 1-week stays as dev default
- No new Python packages, no new npm packages

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models/models.py:138-155,212-260` | Modify | Add User reset/invite/must_change_password fields; add sms_consent to CooperativeMembership; add Announcement model |
| `backend/app/routes/auth.py` | Modify | Add reset request/confirm, invite, accept-invite endpoints |
| `backend/app/routes/announcements.py` | Create | Announcement CRUD + SMS broadcast |
| `backend/app/routes/ussd.py:413,594` | Modify | USSD option 4: show announcements |
| `backend/app/routes/ussdk_hooks.py:540-567` | Modify | USSDk announcements: show real announcements |
| `backend/app/routes/intake.py:56-60` | Modify | Remove animal-only block |
| `backend/app/services/auth_service.py:15` | Modify | Token TTL from env var |
| `backend/app/routes/agro_ai.py` | Modify | Expose is_synthetic in response |
| `backend/app/schemas/auth.py` | Modify | Add password reset/invite schemas |
| `backend/app/schemas/announcement.py` | Create | Announcement schemas |
| `frontend/src/components/dashboard/GovernanceSettings.jsx` | Modify | Expand role dropdown to 5 roles, update invite form |
| `frontend/src/pages/DashboardPage.jsx` | Modify | Role-based cooperative nav gating |
| `frontend/src/components/dashboard/CooperativeAttendance.jsx` | Create | Meeting attendance recording UI |
| `frontend/src/components/dashboard/Announcements.jsx` | Create | Announcement create/list UI |
| `frontend/src/pages/AuthPage.jsx` | Modify | Add forgot password flow, force-password-change flow |
| `frontend/src/api/governance.js` | Modify | Add invite API function |
| `frontend/src/api/auth.js` | Modify | Add password reset API functions |
| `frontend/src/components/dashboard/Scores.jsx` | Modify | Add synthetic model warning banner |
| `frontend/src/data/payments.js` | Delete | Dead code removal |
| `frontend/src/components/DashboardMock.jsx` | Delete | Dead code removal |

---

### Task 1: Backend — User Model Fields + Announcement Model + SMS Consent (#246, #247, #248 foundation)

**Files:**
- Modify: `backend/app/models/models.py` (User model lines 138-155, CooperativeMembership lines 212-260, add Announcement model)

**Produces:** User has reset_token, reset_token_expires_at, invite_token, invite_token_expires_at, must_change_password. CooperativeMembership has sms_consent. New Announcement model exists.

- [ ] **Step 1: Add fields to User model**

In `backend/app/models/models.py`, after line 151 (`updated_at = ...`), add:

```python
reset_token = Column(String, nullable=True)
reset_token_expires_at = Column(DateTime, nullable=True)
invite_token = Column(String, nullable=True)
invite_token_expires_at = Column(DateTime, nullable=True)
must_change_password = Column(Boolean, default=False, nullable=False)
```

- [ ] **Step 2: Add sms_consent to CooperativeMembership**

In `backend/app/models/models.py`, after line 243 (`updated_at = ...`), add:

```python
sms_consent = Column(Boolean, default=True, nullable=False)
```

- [ ] **Step 3: Create Announcement model**

In `backend/app/models/models.py`, add before the last line of the file:

```python
class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    send_sms = Column(Boolean, default=False, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cooperative = relationship("Cooperative")
    creator = relationship("User")
```

- [ ] **Step 4: Run migration to verify no issues**

```bash
cd backend; python -c "from app.models.models import Announcement; print('OK')"
```

Expected: "OK" printed, no import errors.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/models.py
git commit -m "feat: add auth lifecycle fields, sms_consent, and Announcement model"
```

---

### Task 2: Backend — Auth Endpoints (Password Reset + Invite + Force Password) (#248)

**Files:**
- Modify: `backend/app/services/auth_service.py:15`
- Modify: `backend/app/routes/auth.py`
- Modify: `backend/app/schemas/auth.py`

**Produces:** 4 new endpoints: password-reset-request, password-reset-confirm, invite, accept-invite. Token TTL configurable. must_change_password enforced on login.

- [ ] **Step 1: Make token TTL configurable**

In `backend/app/services/auth_service.py`, replace line 15:

```python
import os
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))
```

- [ ] **Step 2: Add auth schemas**

In `backend/app/schemas/auth.py`, add after existing schemas:

```python
from pydantic import BaseModel, EmailStr

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    reset_token: str
    new_password: str

class InviteUserRequest(BaseModel):
    email: str
    role: str

class AcceptInviteRequest(BaseModel):
    invite_token: str
    password: str

class PasswordChangeResponse(BaseModel):
    password_change_required: bool
```

- [ ] **Step 3: Add reset/invite helper functions to auth_service.py**

In `backend/app/services/auth_service.py`, after the `enforce_cooperative_scope` function:

```python
import secrets

def generate_reset_or_invite_token() -> str:
    return secrets.token_hex(32)

def reset_token_valid(user) -> bool:
    if not user.reset_token or not user.reset_token_expires_at:
        return False
    return datetime.utcnow() < user.reset_token_expires_at

def invite_token_valid(user) -> bool:
    if not user.invite_token or not user.invite_token_expires_at:
        return False
    return datetime.utcnow() < user.invite_token_expires_at
```

- [ ] **Step 4: Add password reset endpoints**

In `backend/app/routes/auth.py`, add after existing routes:

```python
@router.post("/password-reset-request", status_code=200)
def password_reset_request(data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user and user.is_active:
        user.reset_token = generate_reset_or_invite_token()
        user.reset_token_expires_at = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        # Interim: log token for manual sharing (no email infra)
        import logging
        logging.getLogger(__name__).info(
            "Password reset token for %s: %s", user.email, user.reset_token
        )
    return {"message": "If that account exists, a reset link has been generated."}

@router.post("/password-reset-confirm", status_code=200)
def password_reset_confirm(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == data.reset_token).first()
    if not user or not reset_token_valid(user):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    user.hashed_password = get_password_hash(data.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    user.must_change_password = False
    db.commit()
    return {"message": "Password has been reset successfully."}
```

- [ ] **Step 5: Update register to set must_change_password**

In `backend/app/routes/auth.py` POST /register, find the User creation block (around line 138-157). Add `must_change_password=True` to the User constructor:

```python
new_user = User(
    email=data.email,
    hashed_password=get_password_hash(data.password),
    role=data.role,
    cooperative_id=current_user.cooperative_id,
    must_change_password=True,
    onboarding_role=data.onboarding_role if hasattr(data, 'onboarding_role') else None,
)
```

- [ ] **Step 6: Update login to signal force-password-change**

In `backend/app/routes/auth.py` POST /login, after the JWT creation (around line 265), add to the return dict:

```python
"password_change_required": user.must_change_password,
```

Also in signup response (around line 109), add:

```python
"password_change_required": new_user.must_change_password,
```

- [ ] **Step 7: Add invite endpoint**

In `backend/app/routes/auth.py`, add:

```python
@router.post("/invite", response_model=UserResponse, status_code=201)
def invite_user(
    data: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    token = generate_reset_or_invite_token()
    expires = datetime.utcnow() + timedelta(hours=72)
    new_user = User(
        email=data.email,
        hashed_password="",
        role=data.role,
        cooperative_id=current_user.cooperative_id,
        invite_token=token,
        invite_token_expires_at=expires,
        must_change_password=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    # Interim: log invite link for admin to share manually
    import logging
    logging.getLogger(__name__).info(
        "Invite for %s: token=%s (valid until %s)", new_user.email, token, expires
    )
    return new_user

@router.post("/accept-invite", status_code=200)
def accept_invite(data: AcceptInviteRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.invite_token == data.invite_token).first()
    if not user or not invite_token_valid(user):
        raise HTTPException(status_code=400, detail="Invalid or expired invite token.")
    user.hashed_password = get_password_hash(data.password)
    user.invite_token = None
    user.invite_token_expires_at = None
    user.must_change_password = False
    db.commit()
    return {"message": "Account activated. You may now login."}
```

- [ ] **Step 8: Import new schemas in auth.py**

Add to the imports at top of `backend/app/routes/auth.py`:

```python
from app.schemas.auth import (
    ...
    PasswordResetRequest,
    PasswordResetConfirm,
    InviteUserRequest,
    AcceptInviteRequest,
    PasswordChangeResponse,
)
from app.services.auth_service import (
    ...
    generate_reset_or_invite_token,
    reset_token_valid,
    invite_token_valid,
)
from datetime import datetime
```

- [ ] **Step 9: Run backend tests**

```bash
cd backend; python -m pytest tests/test_attendance.py tests/test_farm_production.py tests/test_payroll.py tests/test_tasks.py -v -x
```

Expected: All 18 tests pass (auth endpoints not tested in these files, but no regressions).

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/auth_service.py backend/app/routes/auth.py backend/app/schemas/auth.py
git commit -m "feat: add password reset, invite token, force-password-change, configurable token TTL"
```

---

### Task 3: Backend — Announcements CRUD + SMS Broadcast (#246)

**Files:**
- Create: `backend/app/routes/announcements.py`
- Create: `backend/app/schemas/announcement.py`
- Modify: `backend/main.py` (register router)

**Produces:** Announcement CRUD API with optional SMS broadcast on creation.

- [ ] **Step 1: Create announcement schemas**

Create `backend/app/schemas/announcement.py`:

```python
from datetime import datetime
from pydantic import BaseModel

class AnnouncementCreate(BaseModel):
    title: str
    body: str
    send_sms: bool = False

class AnnouncementResponse(BaseModel):
    id: int
    cooperative_id: int
    title: str
    body: str
    send_sms: bool
    created_by: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Create announcements route**

Create `backend/app/routes/announcements.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import Announcement, Cooperative, CooperativeMembership, User
from app.schemas.announcement import AnnouncementCreate, AnnouncementResponse
from app.services.auth_service import enforce_cooperative_scope, get_current_user, require_roles

router = APIRouter(prefix="/announcements", tags=["announcements"])

@router.get("/", response_model=list[AnnouncementResponse])
def list_announcements(
    cooperative_id: int = Query(...),
    skip: int = 0,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    return (
        db.query(Announcement)
        .filter(Announcement.cooperative_id == cooperative_id)
        .order_by(Announcement.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

@router.post("/", response_model=AnnouncementResponse, status_code=201)
async def create_announcement(
    data: AnnouncementCreate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    announcement = Announcement(
        cooperative_id=cooperative_id,
        title=data.title,
        body=data.body,
        send_sms=data.send_sms,
        created_by=current_user.id if current_user else None,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    if data.send_sms:
        from app.services.communications_service import CommunicationsService
        comm = CommunicationsService()
        memberships = (
            db.query(CooperativeMembership)
            .filter(
                CooperativeMembership.cooperative_id == cooperative_id,
                CooperativeMembership.membership_status == "active",
                CooperativeMembership.sms_consent == True,
            )
            .all()
        )
        for m in memberships:
            if m.phone:
                await comm.send_single_sms(
                    recipient=m.phone,
                    message=f"[{announcement.title}] {announcement.body}",
                    db=db,
                    cooperative_id=cooperative_id,
                )

    return announcement

@router.delete("/{announcement_id}", status_code=204)
def delete_announcement(
    announcement_id: int,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    announcement = (
        db.query(Announcement)
        .filter(Announcement.id == announcement_id, Announcement.cooperative_id == cooperative_id)
        .first()
    )
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    db.delete(announcement)
    db.commit()
```

- [ ] **Step 3: Register router in main.py**

In `backend/main.py`, add after other router registrations:
```python
from app.routes.announcements import router as announcements_router
app.include_router(announcements_router)
```

- [ ] **Step 4: Verify imports**

```bash
cd backend; python -c "from app.routes.announcements import router; print('OK')"
```

Expected: "OK"

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/announcement.py backend/app/routes/announcements.py backend/main.py
git commit -m "feat: add announcements CRUD with SMS broadcast"
```

---

### Task 4: Backend — USSD Option 4 + Animal Intake + Agro-AI Warning (#246, #249, #250)

**Files:**
- Modify: `backend/app/routes/ussd.py` (option 4 announcement text)
- Modify: `backend/app/routes/ussdk_hooks.py` (announcements placeholder)
- Modify: `backend/app/routes/intake.py:56-60` (remove animal block)
- Modify: `backend/app/routes/agro_ai.py` (expose is_synthetic)

**Produces:** USSD shows real announcements, intake accepts animal products, Agro-AI returns is_synthetic flag.

- [ ] **Step 1: Update USSD option 4 (webhooks.py)**

In `backend/app/routes/webhooks.py`, find the announcement_text block (around line 594). Replace:

```python
announcement_text = "No new announcements. Check with your cooperative leader."
```

With:

```python
from app.models.models import Announcement
announcements = (
    db.query(Announcement)
    .filter(Announcement.cooperative_id == membership.cooperative_id)
    .order_by(Announcement.created_at.desc())
    .limit(3)
    .all()
)
if announcements:
    lines = []
    for a in announcements:
        lines.append(f"{a.title}: {a.body[:120]}")
    announcement_text = "\n---\n".join(lines)
else:
    announcement_text = "No announcements yet. Check with your cooperative leader."
```

- [ ] **Step 2: Update USSDk announcements (ussdk_hooks.py)**

In `backend/app/routes/ussdk_hooks.py`, around line 553, replace the static text with the same pattern:

```python
from app.models.models import Announcement
announcements = (
    db.query(Announcement)
    .filter(Announcement.cooperative_id == cooperative_id)
    .order_by(Announcement.created_at.desc())
    .limit(3)
    .all()
)
if announcements:
    lines = []
    for a in announcements:
        lines.append(f"{a.title}: {a.body[:120]}")
    announcement_text = "\n---\n".join(lines)
else:
    announcement_text = "No announcements yet. Check with your cooperative leader."
```

- [ ] **Step 3: Remove animal-only block from intake**

In `backend/app/routes/intake.py`, remove lines 56-60 (the animal-only membership check):

```python
# DELETE these lines:
if membership.production_focus == ProductionFocus.animal:
    raise HTTPException(
        status_code=409,
        detail="Produce intake is crop-only and unavailable to animal-only members",
    )
```

- [ ] **Step 4: Expose is_synthetic in Agro-AI**

In `backend/app/routes/agro_ai.py`, find the prediction endpoint. Add `is_synthetic` to the response. If the model has `model.is_synthetic_fallback`, include it in the JSON response alongside the score, risk_band, etc. Add `"is_synthetic": model.is_synthetic_fallback` to the prediction response dict.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/webhooks.py backend/app/routes/ussdk_hooks.py backend/app/routes/intake.py backend/app/routes/agro_ai.py
git commit -m "feat: USSD real announcements, animal intake unblocked, Agro-AI synthetic flag"
```

---

### Task 5: Frontend — RBAC Nav Gating + Governance Roles (#244)

**Files:**
- Modify: `frontend/src/components/dashboard/GovernanceSettings.jsx`
- Modify: `frontend/src/pages/DashboardPage.jsx`

**Produces:** 5 roles in governance UI, cooperative nav gating per role.

- [ ] **Step 1: Expand role dropdown in GovernanceSettings**

In `GovernanceSettings.jsx`, update the role `<select>` for existing users (lines 102-104) from 2 options to 5:

```jsx
<option value="admin">Administrator</option>
<option value="finance_officer">Finance officer</option>
<option value="farm_owner">Farm owner</option>
<option value="farm_manager">Farm manager</option>
<option value="supervisor">Supervisor</option>
```

Same for the invite form dropdown (lines 143-144):

```jsx
<option value="finance_officer">Finance officer</option>
<option value="admin">Administrator</option>
<option value="farm_owner">Farm owner</option>
<option value="farm_manager">Farm manager</option>
<option value="supervisor">Supervisor</option>
```

- [ ] **Step 2: Add role-based nav gating in DashboardPage.jsx**

In `DashboardPage.jsx`, after the existing `filteredNavGroups` logic for solo_farm + supervisor (around line 297-310 from Task 8 of previous plan), add cooperative role gating:

```jsx
const coopedNavGroups = organizationType !== 'solo_farm' && userRole === 'finance_officer'
  ? [
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
  : organizationType !== 'solo_farm' && userRole && ['farm_owner', 'farm_manager', 'supervisor'].includes(userRole)
  ? [
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
  : null
```

Then update the navGroups resolution to use the filtered value:
```jsx
const displayNavGroups = filteredNavGroups || coopedNavGroups || navGroups
```

And update sidebar rendering to use `displayNavGroups.map(...)` instead of `filteredNavGroups.map(...)`.

Also add redirect for cooperative role-restricted sections:
```jsx
if (organizationType !== 'solo_farm' && userRole && ['farm_owner', 'farm_manager', 'supervisor'].includes(userRole)) {
  const allowedSections = ['overview', 'members', 'production', 'scores', 'sms', 'ussd', 'activity', 'settings']
  if (!allowedSections.includes(section)) {
    return <Navigate to={dashboardPath('overview')} replace />
  }
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend; npm run build
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/GovernanceSettings.jsx frontend/src/pages/DashboardPage.jsx
git commit -m "feat: expand RBAC roles in UI, add cooperative role-based nav gating (#244)"
```

---

### Task 6: Frontend — Attendance UI + Announcements Tab (#245, #246)

**Files:**
- Create: `frontend/src/components/dashboard/CooperativeAttendance.jsx`
- Create: `frontend/src/components/dashboard/Announcements.jsx`
- Create: `frontend/src/api/announcements.js`
- Modify: `frontend/src/pages/DashboardPage.jsx` (add tabs)

**Produces:** Attendance recording UI and Announcements create/list UI integrated into dashboard.

- [ ] **Step 1: Create API client for announcements**

Create `frontend/src/api/announcements.js`:

```js
import api from './config'

export async function fetchAnnouncements(cooperativeId) {
  const { data } = await api.get('/announcements/', { params: { cooperative_id: cooperativeId } })
  return data
}

export async function createAnnouncement(cooperativeId, payload) {
  const { data } = await api.post('/announcements/', payload, { params: { cooperative_id: cooperativeId } })
  return data
}

export async function deleteAnnouncement(cooperativeId, id) {
  await api.delete(`/announcements/${id}`, { params: { cooperative_id: cooperativeId } })
}
```

- [ ] **Step 2: Create CooperativeAttendance component**

Create `frontend/src/components/dashboard/CooperativeAttendance.jsx`:

A component that:
- Fetches all cooperative members (farmers list via props or API)
- Shows a date picker + event name input
- Renders a checkbox list of members with name + phone
- "Mark all present" / "Mark all absent" bulk toggle buttons
- On submit: calls `POST /farmers/{farmer_id}/attendance` per selected member with event_name, event_date, attended=true/false
- Shows past attendance records below the form

Implementation uses existing `fetchFarmers` API and `api.post('/farmers/{id}/attendance', ...)` pattern.

- [ ] **Step 3: Create Announcements component**

Create `frontend/src/components/dashboard/Announcements.jsx`:

A component that:
- Shows a create form at top: title, body (textarea), SMS broadcast toggle checkbox
- Lists past announcements in reverse chronological order
- Delete button per announcement (admin only)
- Uses the API client from Step 1

- [ ] **Step 4: Wire both into DashboardPage.jsx**

In `DashboardPage.jsx`:
- Import CooperativeAttendance and Announcements
- Add `attendance` to the cooperative Operations nav group (after `members`)
- Add `announcements` to the cooperative Communications nav group (after `ussd`)
- Add `attendance` and `announcements` to `TITLES` object
- Add section rendering:
```jsx
{section === 'attendance' && organizationType !== 'solo_farm' && (
  <CooperativeAttendance cooperativeId={cooperativeId} farmers={farmers} />
)}
{section === 'announcements' && (
  <Announcements cooperativeId={cooperativeId} />
)}
```

- [ ] **Step 5: Add attendance and announcements to DASHBOARD_SECTIONS in routes.js**

In `frontend/src/constants/routes.js`, add `'attendance'` and `'announcements'` to the DASHBOARD_SECTIONS array.

- [ ] **Step 6: Build and verify**

```bash
cd frontend; npm run build
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/announcements.js frontend/src/components/dashboard/CooperativeAttendance.jsx frontend/src/components/dashboard/Announcements.jsx frontend/src/pages/DashboardPage.jsx frontend/src/constants/routes.js
git commit -m "feat: add cooperative attendance UI and announcements tab (#245, #246)"
```

---

### Task 7: Frontend — Auth Flows (Forgot Password + Force Change + Invite UI) (#248)

**Files:**
- Modify: `frontend/src/pages/AuthPage.jsx`
- Modify: `frontend/src/api/auth.js`
- Modify: `frontend/src/api/governance.js`
- Modify: `frontend/src/components/dashboard/GovernanceSettings.jsx`

**Produces:** Forgot password flow, force-password-change screen, invite-by-token UI.

- [ ] **Step 1: Add auth API functions**

In `frontend/src/api/auth.js`, add:

```js
export async function requestPasswordReset(email) {
  await api.post('/auth/password-reset-request', { email })
}

export async function confirmPasswordReset(resetToken, newPassword) {
  await api.post('/auth/password-reset-confirm', { reset_token: resetToken, new_password: newPassword })
}

export async function acceptInvite(inviteToken, password) {
  await api.post('/auth/accept-invite', { invite_token: inviteToken, password })
}
```

- [ ] **Step 2: Add invite API function**

In `frontend/src/api/governance.js`, add:

```js
export async function inviteCooperativeUser(email, role) {
  const { data } = await api.post('/auth/invite', { email, role })
  return data
}
```

- [ ] **Step 3: Update AuthPage.jsx with forgot password flow**

In `AuthPage.jsx`:
- Add a "Forgot password?" link below the login form
- `mode === 'forgot'`: show email input → submit → show "If account exists, reset instructions sent" confirmation
- `mode === 'reset'` (accessed via URL param `?token=...`): show new password form → submit → redirect to login
- `mode === 'accept-invite'` (accessed via URL param `?invite=...`): show password setup form → submit → redirect to login

- [ ] **Step 4: Add force-password-change flow**

In `AuthPage.jsx`:
- After successful login, if response contains `password_change_required: true`, redirect to set-password mode
- In set-password mode: show "Set your new password" form → submit → login automatically

- [ ] **Step 5: Update GovernanceSettings invite form**

In `GovernanceSettings.jsx`:
- Remove the password input from the invite form
- Change "Add user" button to call `inviteCooperativeUser(email, role)` instead of `registerCooperativeUser(invite)`
- Show success message: "Invite sent. Share the invite link from the backend logs with the user."

- [ ] **Step 6: Build and verify**

```bash
cd frontend; npm run build
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/auth.js frontend/src/api/governance.js frontend/src/pages/AuthPage.jsx frontend/src/components/dashboard/GovernanceSettings.jsx
git commit -m "feat: add forgot password, invite-by-token, and force-password-change UI (#248)"
```

---

### Task 8: Frontend — Agro-AI Warning + Dead Code Cleanup + Build (#250, #251)

**Files:**
- Modify: `frontend/src/components/dashboard/Scores.jsx`
- Delete: `frontend/src/data/payments.js`
- Delete: `frontend/src/components/DashboardMock.jsx`

**Produces:** Agro-AI synthetic warning banner, dead code removed.

- [ ] **Step 1: Add warning banner to Scores**

In `Scores.jsx`, find the existing info banner or add one near the top of the component (before the scores list):

```jsx
<div className="info-banner" style={{ background: '#FFFBEB', borderColor: '#FCD34D', marginBottom: 16 }}>
  <strong>Experimental — </strong>
  Trust scores are trained on synthetic data, not real repayment history.
  Use as an advisory tool only.
</div>
```

- [ ] **Step 2: Remove dead code**

- Delete `frontend/src/data/payments.js`
- Delete `frontend/src/components/DashboardMock.jsx`
- Remove the import of `DashboardMock` from any file that imports it (e.g., `HomePage.jsx` — move its static data inline if needed)

Verify no broken imports:
```bash
cd frontend; grep -r "data/payments\|DashboardMock" src/
```

Expected: No matches found.

- [ ] **Step 3: Build and verify**

```bash
cd frontend; npm run build
```

Expected: Build succeeds with no warnings about missing imports.

- [ ] **Step 4: Commit**

```bash
git rm frontend/src/data/payments.js frontend/src/components/DashboardMock.jsx
git add frontend/src/components/dashboard/Scores.jsx
git commit -m "feat: Agro-AI synthetic warning, remove dead demo code (#250, #251)"
```

---

### Task 9: Final Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run all backend tests**

```bash
cd backend; python -m pytest tests/ -v
```

Expected: All existing tests pass. No regressions.

- [ ] **Step 2: Build frontend**

```bash
cd frontend; npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Review git log**

```bash
git log --oneline -15
```

Expected: 8+ commits covering all M4 issues.

- [ ] **Step 4: Final commit if needed**

```bash
git add -A
git diff --cached --stat
git commit -m "chore: final verification and cleanup for M4 completion"
```

---

## Task Dependencies

```
Task 1 (models) ───┐
                   ├── Task 2 (auth endpoints) ──┐
                   ├── Task 3 (announcements api)─┤
                   ├── Task 4 (USSD/intake/ai) ───┤
                   │                              ├── Task 5 (RBAC frontend) ──┐
                   │                              ├── Task 6 (attendance+announcements ui) ──┤
                   │                              ├── Task 7 (auth flows frontend) ──┤
                   │                              └── Task 8 (warnings+cleanup) ──┤
                   │                                                             └── Task 9 (verification)
```

Tasks 1 must go first (model changes). Tasks 2-4 can run in parallel after Task 1. Tasks 5-8 can run in parallel (different frontend files). Task 9 runs after all others.
