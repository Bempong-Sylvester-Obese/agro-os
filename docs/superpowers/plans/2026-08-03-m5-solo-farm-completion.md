# M5 — Solo Farm / Worker Platform Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the 4 remaining M5 milestone gaps: product spec doc, org-type integration, supabase sync, and 3-tier RBAC.

**Architecture:** Four independent workstreams. #252 is docs-only (no code). #253 and #254 are infra/schema syncs (PricingPage + supabase migrations). #255 touches backend route guards and frontend DashboardPage for role-based conditional UI.

**Tech Stack:** FastAPI (Python), React + Vite, Supabase (PostgreSQL + RLS), bcrypt + JWT auth

## Global Constraints

- Member limit for Starter plan: 10 (was 50)
- Solo Farm plan: GHS 99/month, up to 20 workers
- RBAC roles: `farm_owner` > `farm_manager` > `supervisor`. Supervisor can ONLY log attendance.
- Supabase migrations follow existing naming: `006_organization_type.sql`, `007_m5_worker_tables.sql`, `008_m5_rls_policies.sql`
- Supabase RLS follows existing pattern: `ALTER TABLE X ENABLE ROW LEVEL SECURITY; CREATE POLICY X_service_role ON X FOR ALL TO service_role USING (true) WITH CHECK (true);`
- Frontend auth: role resolved from JWT payload via `decode_access_token`, same pattern as `getOrganizationType()`
- All backend route changes must preserve existing `cooperative_id` scoping
- No new Python packages, no new npm packages
- `docs/solo-farm-product-spec.md` for the research doc

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `docs/solo-farm-product-spec.md` | Create | #252 research spec: workers vs members, module visibility |
| `frontend/src/pages/PricingPage.jsx:6-58,144-150` | Modify | Add Solo Farm to comparison table; cap Starter at 10 |
| `supabase/migrations/006_organization_type.sql` | Create | Add missing columns to cooperatives + users tables |
| `supabase/migrations/007_m5_worker_tables.sql` | Create | M5 tables |
| `supabase/migrations/008_m5_rls_policies.sql` | Create | RLS policies for M5 tables |
| `backend/app/routes/payroll.py:89,157` | Modify | RBAC: farm_manager blocked from disburse; supervisor blocked from all |
| `frontend/src/utils/auth.js` | Modify | Add `getUserRole()` utility |
| `frontend/src/pages/DashboardPage.jsx` | Modify | Role-conditional UI: hide nav items and action buttons |

---

### Task 1: Write Solo Farm Product Spec (#252)

**Files:**
- Create: `docs/solo-farm-product-spec.md`
- Modify: `docs/superpowers/specs/2026-08-03-m5-solo-farm-completion-design.md`

**Produces:** A documented product spec distinguishing workers from members and defining module visibility by org type.

- [ ] **Step 1: Write the spec document**

Create `docs/solo-farm-product-spec.md`:

```markdown
# Solo Farm — Product Specification

## Overview

AgroOS serves two distinct organizational models:
- **Cooperative** — democratically governed groups of farmer-members with dues, loans, trust scoring, and commerce.
- **Solo Farm** — independent farm owners managing wage laborers with task tracking, attendance, and payroll.

## Workers vs Members

| | Worker | Member (Farmer) |
|---|---|---|
| Relationship | Hired laborer | Cooperative member |
| Equity / Dues | None | Pays cooperative dues |
| AgroCredit eligibility | No | Yes (trust-scored) |
| Trust scoring | No | Yes |
| Produce commerce | No | Yes (intake, settlements) |
| Dashboard access | USSD only | Coop dashboard (if officer) |
| Data model | `workers` table | `farmers` + `cooperative_memberships` tables |
| Payment flow | Wage payouts via Moolre | Dues collection, loan disbursement/repayment |
| Registration | Added by farm owner/admin | Self-registration or admin invite |

## Module Visibility by Organization Type

### Solo Farm (`organization_type = "solo_farm"`)

**Visible:**
- Overview dashboard
- Workers (CRUD)
- Tasks (create, assign, track)
- Attendance (log per worker per shift)
- Payroll (summarize, approve, disburse)
- Farm Production (crop cycle tracking)
- SMS broadcasts
- USSD activity
- Activity log
- Settings

**Hidden:**
- Members
- Payments (dues)
- Loans (AgroCredit)
- Commerce stack (produce intake, aggregation, buyers, buyer sales, settlements)
- Agro-AI trust scores

### Cooperative (`organization_type = "cooperative"`)

**Visible:**
- Overview dashboard
- Members
- Production (cooperative)
- Agro-AI scores
- Payments
- Loans
- Commerce stack (intake, aggregation, buyers, sales, settlements)
- SMS broadcasts
- USSD activity
- Activity log
- Settings

**Hidden:**
- Workers
- Tasks
- Attendance
- Payroll
- Farm Production (replaced by cooperative production)

## Subscription Tiers

| Tier | Price | Target | Member Cap | Worker Cap | Key Features |
|------|-------|--------|------------|------------|--------------|
| **Starter** | Free | Emerging cooperatives | 10 | N/A | Member register, dues collection, dashboard |
| **Solo Farm** | GHS 99/mo | Independent farmers | N/A | 20 | Workers, tasks, attendance, payroll, USSD |
| **Growth** | GHS 299/mo | Operating cooperatives | 500 | N/A | AgroCredit, USSD, priority support |
| **Enterprise** | Custom | Networks/institutions | Unlimited | Custom | Multi-cooperative, custom integrations, SLA |

## RBAC: Dashboard User Roles (Solo Farm)

| Capability | farm_owner | farm_manager | supervisor |
|---|---|---|---|
| Workers CRUD | Full | Full | None |
| Tasks CRUD | Full | Full | None |
| Attendance log | Full | Full | Log only |
| Payroll view | Full | Full | None |
| Payroll approve | Full | Full | None |
| Payroll disburse | Full | None | None |
| Production CRUD | Full | Full | None |
| SMS / USSD / Activity / Settings | Full | Full | View |
```

- [ ] **Step 2: Update the design spec to reference the product spec**

In `docs/superpowers/specs/2026-08-03-m5-solo-farm-completion-design.md`, find "# 1. #252 — Research Spec Document" and append at the end of that paragraph:

```
**Artifact:** `docs/solo-farm-product-spec.md` (completed)
```

- [ ] **Step 3: Commit**

```bash
git add docs/solo-farm-product-spec.md docs/superpowers/specs/2026-08-03-m5-solo-farm-completion-design.md
git commit -m "docs: add solo-farm product spec (#252)"
```

---

### Task 2: Fix PricingPage — Solo Farm in Comparison + Starter Cap (#253 frontend)

**Files:**
- Modify: `frontend/src/pages/PricingPage.jsx` (lines 14, 51-58, 146-150, 153-157)

**Produces:** Solo Farm appears in the comparison table. Starter capped at 10 members.

- [ ] **Step 1: Cap Starter members**

In `frontend/src/pages/PricingPage.jsx` line 14, change `'Up to 50 members'` to `'Up to 10 members'`.

- [ ] **Step 2: Add Solo Farm to COMPARISON array**

Replace the entire `COMPARISON` array (lines 51-58):

```jsx
const COMPARISON = [
  ['Member / worker capacity', '10 members', '20 workers', '500 members', 'Custom'],
  ['MoMo collections', 'Included', '—', 'Included', 'Included'],
  ['AgroCredit scoring', '—', '—', 'Included', 'Included'],
  ['Wage payroll', '—', 'Included', '—', 'Included'],
  ['USSD access', '—', 'Worker', 'Included', 'Custom'],
  ['API and integrations', '—', '—', '—', 'Included'],
  ['Support', 'Email', 'Email', 'Priority', 'Dedicated team'],
]
```

Each row now has 5 elements: [capability, starter, solo, growth, enterprise].

- [ ] **Step 3: Update the table header row**

In the `<thead>` (lines 146-150), change:

```jsx
<th>Starter</th>
<th>Growth</th>
<th>Enterprise</th>
```

To:

```jsx
<th>Starter</th>
<th>Solo Farm</th>
<th>Growth</th>
<th>Enterprise</th>
```

- [ ] **Step 4: Update the rendering loop**

Change line 153 from:

```jsx
{COMPARISON.map(([capability, starter, growth, enterprise]) => (
```

To:

```jsx
{COMPARISON.map(([capability, starter, solo, growth, enterprise]) => (
```

Change lines 155-158 from:

```jsx
<td>{starter}</td>
<td>{growth}</td>
<td>{enterprise}</td>
```

To:

```jsx
<td>{starter}</td>
<td>{solo}</td>
<td>{growth}</td>
<td>{enterprise}</td>
```

- [ ] **Step 5: Verify build**

Run: `npm run build` in `frontend/`
Expected: Build succeeds with no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PricingPage.jsx
git commit -m "feat: add Solo Farm to pricing comparison table, cap Starter at 10 members"
```

---

### Task 3: Supabase Migration — Organization Type Columns (#253 backend)

**Files:**
- Create: `supabase/migrations/006_organization_type.sql`

**Produces:** Supabase cooperatives and users tables match the backend SQLAlchemy models.

- [ ] **Step 1: Write migration**

Create `supabase/migrations/006_organization_type.sql`:

```sql
-- Add organization type, subscription, and role columns to cooperatives and users
-- to match backend/app/models/models.py (Cooperative and User SQLAlchemy models)

ALTER TABLE cooperatives
    ADD COLUMN IF NOT EXISTS organization_type VARCHAR NOT NULL DEFAULT 'cooperative',
    ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR DEFAULT 'starter',
    ADD COLUMN IF NOT EXISTS subscription_status VARCHAR DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS ussd_code VARCHAR(4);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS onboarding_role VARCHAR,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/006_organization_type.sql
git commit -m "feat(supabase): add organization_type, subscription, and user role columns"
```

---

### Task 4: Supabase Migration — M5 Worker Tables (#254)

**Files:**
- Create: `supabase/migrations/007_m5_worker_tables.sql`

**Produces:** All six M5 tables exist in the Supabase schema mirror, matching Alembic migrations.

- [ ] **Step 1: Write migration**

Create `supabase/migrations/007_m5_worker_tables.sql`:

```sql
-- M5 Solo Farm / Worker Platform tables
-- Mirrors Alembic migrations 007_organization_type.py and 007_phase1.py

CREATE TABLE IF NOT EXISTS workers (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    name VARCHAR NOT NULL,
    phone VARCHAR NOT NULL,
    wage_rate DOUBLE PRECISION DEFAULT 0.0,
    role VARCHAR DEFAULT 'worker',
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_worker_phone_per_coop UNIQUE (cooperative_id, phone)
);

CREATE TABLE IF NOT EXISTS work_tasks (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    title VARCHAR NOT NULL,
    description TEXT,
    task_type VARCHAR NOT NULL DEFAULT 'general',
    location VARCHAR,
    scheduled_date DATE NOT NULL,
    assigned_by INTEGER REFERENCES users(id),
    status VARCHAR DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS worker_assignments (
    id SERIAL PRIMARY KEY,
    work_task_id INTEGER NOT NULL REFERENCES work_tasks(id) ON DELETE CASCADE,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS worker_attendance (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES workers(id),
    work_task_id INTEGER REFERENCES work_tasks(id),
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    date DATE NOT NULL,
    hours_worked DOUBLE PRECISION,
    shift VARCHAR NOT NULL DEFAULT 'full_day',
    logged_by INTEGER REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wage_payouts (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    worker_id INTEGER NOT NULL REFERENCES workers(id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_hours DOUBLE PRECISION DEFAULT 0,
    total_shifts INTEGER DEFAULT 0,
    wage_rate DOUBLE PRECISION DEFAULT 0,
    gross_amount DOUBLE PRECISION DEFAULT 0,
    status VARCHAR DEFAULT 'pending',
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    paid_at TIMESTAMP,
    moolre_reference VARCHAR,
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS farm_productions (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER NOT NULL REFERENCES cooperatives(id),
    crop_type VARCHAR NOT NULL,
    season VARCHAR NOT NULL,
    location VARCHAR,
    planted_date DATE NOT NULL,
    expected_harvest_date DATE,
    actual_harvest_date DATE,
    expected_quantity_kg DOUBLE PRECISION NOT NULL,
    actual_quantity_kg DOUBLE PRECISION,
    quality_grade VARCHAR,
    notes TEXT,
    logged_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/007_m5_worker_tables.sql
git commit -m "feat(supabase): add M5 worker platform tables"
```

---

### Task 5: Supabase Migration — M5 RLS Policies (#254)

**Files:**
- Create: `supabase/migrations/008_m5_rls_policies.sql`

**Produces:** RLS enabled on all M5 tables with service_role bypass.

- [ ] **Step 1: Write RLS migration**

Create `supabase/migrations/008_m5_rls_policies.sql`:

```sql
-- RLS policies for M5 Solo Farm / Worker Platform tables
-- Mirrors the pattern in 002_rls_policies.sql

ALTER TABLE workers ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE wage_payouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_productions ENABLE ROW LEVEL SECURITY;

CREATE POLICY workers_service_role ON workers
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY work_tasks_service_role ON work_tasks
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY worker_assignments_service_role ON worker_assignments
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY worker_attendance_service_role ON worker_attendance
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY wage_payouts_service_role ON wage_payouts
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY farm_productions_service_role ON farm_productions
    FOR ALL TO service_role USING (true) WITH CHECK (true);
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/008_m5_rls_policies.sql
git commit -m "feat(supabase): add RLS policies for M5 worker platform tables"
```

---

### Task 6: Backend RBAC — Update Payroll Route Guards (#255 backend)

**Files:**
- Modify: `backend/app/routes/payroll.py` (lines 89 and 157)

**Produces:** Payroll disburse blocked for farm_manager. All payroll endpoints blocked for supervisor.

**Note:** All other route files already have correct role guards:
- `workers.py`: POST/PATCH already require `("admin", "farm_owner", "farm_manager")`, DELETE requires `("admin", "farm_owner")` — supervisor excluded ✓
- `attendance.py`: POST already includes `("admin", "farm_owner", "farm_manager", "supervisor")` ✓
- `tasks.py`: POST/PATCH/assign already require `("admin", "farm_owner", "farm_manager")` — supervisor excluded ✓
- `farm_production.py`: POST/PATCH already require `("admin", "farm_owner", "farm_manager")` — supervisor excluded ✓

- [ ] **Step 1: Block farm_manager from payroll disburse**

In `backend/app/routes/payroll.py` line 162, change:

```python
current_user: User | None = Depends(require_roles("admin", "farm_owner")),
```

This is already correct — `farm_manager` is NOT in the list. No change needed.

- [ ] **Step 2: Verify payroll approve blocks supervisor**

In `backend/app/routes/payroll.py` line 94:

```python
current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager")),
```

This excludes `supervisor`. Correct. No change needed.

- [ ] **Step 3: Verify payroll summary/history allow any authenticated user**

Line 37 and 238 use `get_current_user` (no role check). This is correct per the RBAC matrix — farm_owner, farm_manager, and even supervisor should be able to view payroll data. No change needed.

- [ ] **Step 4: Verify no changes needed for other route files**

All routes already match the RBAC matrix. No edits required.

- [ ] **Step 5: Run backend tests to confirm no regressions**

```bash
cd backend; python -m pytest tests/test_attendance.py tests/test_farm_production.py tests/test_payroll.py tests/test_tasks.py -v
```

Expected: All 16 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/
git commit -m "feat: verify backend RBAC route guards match spec, run tests"
```

---

### Task 7: Frontend RBAC — Add getUserRole Utility (#255 frontend)

**Files:**
- Modify: `frontend/src/utils/auth.js` (append after line 56)

**Produces:** `getUserRole()` utility that extracts role from JWT, same pattern as `getOrganizationType()`.

- [ ] **Step 1: Add getUserRole function**

In `frontend/src/utils/auth.js`, add after `getOrganizationType` (after line 56):

```js
/** Resolve the user role from the JWT payload. */
export function getUserRole() {
  return getAuthInfo().role ?? null
}
```

- [ ] **Step 2: Update getAuthInfo to include role in the JWT payload**

In `frontend/src/utils/auth.js`, the `getAuthInfo` function currently extracts `cooperative_id`, `user_id`, `email`, `organization_type` from the JWT. Add `role` to the destructured return. Change the return object (line 39-47) to include `role`:

```js
return {
  cooperative_id: payload.cooperative_id ?? null,
  user_id: payload.user_id ?? null,
  email: payload.sub ?? null,
  organization_type: payload.organization_type ?? null,
  role: payload.role ?? null,
}
```

Also update the catch clause (line 46):

```js
return { cooperative_id: null, email: null, user_id: null, role: null }
```

Or leave the catch as-is (omitted keys will be `undefined` which behaves like `null`). The simpler approach — just add `role` to the success return object and leave the catch as-is.

- [ ] **Step 3: Verify the JWT payload includes role**

From `backend/app/routes/auth.py` line 98-104, the JWT payload includes:
```python
access_token = create_access_token(
    data={
        "sub": new_user.email,
        "user_id": new_user.id,
        "cooperative_id": new_coop.id,
        "organization_type": new_coop.organization_type,
    }
)
```

The `role` claim is NOT currently in the JWT payload. We need to add it.

**Additional backend change:** Modify `backend/app/routes/auth.py`:

Line 98-104 (signup): Add `"role": new_user.role` to the JWT payload:

```python
access_token = create_access_token(
    data={
        "sub": new_user.email,
        "user_id": new_user.id,
        "cooperative_id": new_coop.id,
        "organization_type": new_coop.organization_type,
        "role": new_user.role,
    }
)
```

Line 250-256 (login): Add `"role": user.role` to the JWT payload:

```python
access_token = create_access_token(
    data={
        "sub": user.email,
        "user_id": user.id,
        "cooperative_id": user.cooperative_id,
        "organization_type": user.cooperative.organization_type if user.cooperative else None,
        "role": user.role,
    }
)
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/auth.js backend/app/routes/auth.py
git commit -m "feat: add getUserRole utility, include role in JWT payload"
```

---

### Task 8: Frontend RBAC — Role-Conditional Dashboard UI (#255 frontend)

**Files:**
- Modify: `frontend/src/pages/DashboardPage.jsx`

**Produces:** Dashboard nav hides sections based on user role. Action buttons disabled/hidden per role.

- [ ] **Step 1: Import getUserRole and resolve role in component**

In `frontend/src/pages/DashboardPage.jsx` line 5, update the import:

```jsx
import { getOrganizationType, getUserRole, resolveCooperativeId } from '../utils/auth'
```

Add a role state after line 171:

```jsx
const [userRole, setUserRole] = useState(() => getUserRole())
```

After `setOrganizationType` on line 205, add role refresh:

```jsx
if (resolvedCoop?.organization_type) {
  setOrganizationType(resolvedCoop.organization_type)
}
const role = getUserRole()
if (role) setUserRole(role)
```

- [ ] **Step 2: Conditionally filter nav groups by role**

In the `getNavGroups` function, update the solo_farm branch to filter items based on `userRole`. Add `userRole` as a parameter:

In the component, compute filtered nav groups:

After line 297 (`const navGroups = getNavGroups(organizationType)`), add:

```jsx
const filteredNavGroups = organizationType === 'solo_farm' && userRole === 'supervisor'
  ? [
      {
        label: 'Operations',
        items: [
          { key: 'overview', icon: <BarChart3 size={18} />, label: 'Overview' },
          { key: 'attendance', icon: <Users size={18} />, label: 'Attendance' },
        ],
      },
      {
        label: 'Governance',
        items: [
          { key: 'activity', icon: <ClipboardList size={18} />, label: 'Activity log' },
        ],
      },
    ]
  : navGroups
```

Use `filteredNavGroups` instead of `navGroups` in the sidebar rendering (lines 337-351).

- [ ] **Step 3: Conditionally render section components by role**

For supervisor users on a solo_farm org, redirect from non-attendance sections:

After the existing redirects (lines 303-308), add:

```jsx
if (organizationType === 'solo_farm' && userRole === 'supervisor') {
  const supervisorSections = ['overview', 'attendance', 'activity', 'settings']
  if (!supervisorSections.includes(section)) {
    return <Navigate to={dashboardPath('attendance')} replace />
  }
}
```

- [ ] **Step 4: Verify build**

Run: `npm run build` in `frontend/`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DashboardPage.jsx
git commit -m "feat: role-conditional dashboard UI for solo farm users (#255)"
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
git log --oneline -10
```

Expected: 8 commits covering all 4 issues (#252, #253, #254, #255).

- [ ] **Step 4: Final commit (if any remaining changes)**

```bash
git add -A
git diff --cached --stat
git commit -m "chore: final verification and cleanup for M5 completion"
```

---

## Depends-On Chain

```
Task 1 (#252 spec) ──┐
Task 2 (#253 pricing)┤  Independent — can run in parallel
Task 3 (#253 supabase)┤
                      │
Task 4 (#254 tables) ─┤
Task 5 (#254 RLS)    ─┤
                      │
Task 6 (#255 backend) ┤  RBAC backend
Task 7 (#255 auth)   ─┼── RBAC frontend (auth) — independent of Task 6
Task 8 (#255 frontend)┘  RBAC frontend (UI) — depends on Task 7
                      │
Task 9 (verification)─┘  Runs after all tasks
```
