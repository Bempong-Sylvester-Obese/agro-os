# M5 — Solo Farm / Worker Platform Design Spec

**Date:** 2026-07-30  
**Status:** Draft  
**Milestone:** M5 — Solo Farm / Worker Platform  
**Issues:** #252, #253, #254, #255, #256, #257, #258, #259, #260

---

## 1. Overview

Solo Farm is a new product tier for individual farmland owners who manage hired workers. It is distinct from the cooperative product (member farmers with trust scores, loans, dues). A business can be either a `cooperative` or a `solo_farm` at signup, and cooperatives can also spawn solo farm sub-entities.

---

## 2. Data Model

### 2.1 Organization Type

Add `organization_type` column to `cooperatives` table:

```
cooperatives.organization_type: Literal["cooperative", "solo_farm"]
```

Default is `"cooperative"`. Signup flow asks for org type. The organization_type determines which dashboard IA and feature set is shown.

### 2.2 Workers Table

```
workers
  id (PK)
  cooperative_id (FK -> cooperatives.id)
  name (string)
  phone (string, unique within cooperative)
  wage_rate (decimal, per day/shift)
  role (enum: "worker", "supervisor")
  status (enum: "active", "inactive")
  created_at, updated_at
```

Workers are **not** farmers. They exist only within a cooperative (solo_farm) scope. No trust scores, no loans, no dues. Phone is the identifier for USSD/SMS.

### 2.3 Work Tasks

```
work_tasks
  id (PK)
  cooperative_id (FK -> cooperatives.id)
  title (string)
  description (text, nullable)
  task_type (enum: "planting", "weeding", "harvesting", "irrigation", "fertilizing", "general")
  plot / location (string, nullable)
  scheduled_date (date)
  assigned_by (FK -> users.id)
  status (enum: "open", "in_progress", "completed", "cancelled")
  created_at
```

```
worker_assignments
  id (PK)
  work_task_id (FK -> work_tasks.id)
  worker_id (FK -> workers.id)
  assigned_at (datetime)
```

### 2.4 Worker Attendance (Labor Logging)

```
worker_attendance
  id (PK)
  worker_id (FK -> workers.id)
  work_task_id (FK -> work_tasks.id, nullable)
  cooperative_id (FK -> cooperatives.id)
  date (date)
  hours_worked (decimal, nullable)
  shift (enum: "morning", "afternoon", "full_day")
  logged_by (FK -> users.id)
  notes (text, nullable)
  created_at
```

This is **separate** from `cooperative_attendances` (which is for member meeting attendance / trust scoring).

### 2.5 Farm-Level Production

```
farm_productions
  id (PK)
  cooperative_id (FK -> cooperatives.id)
  crop_type (string)
  season (string)
  plot / location (string, nullable)
  planted_date (date)
  expected_harvest_date (date, nullable)
  actual_harvest_date (date, nullable)
  expected_quantity_kg (decimal)
  actual_quantity_kg (decimal, nullable)
  quality_grade (string, nullable)
  notes (text, nullable)
  logged_by (FK -> users.id)
  created_at
```

Production is at the farm level (not per-member). The farm owner/manager logs plantings and harvests directly.

### 2.6 Wage Payroll

```
wage_payouts
  id (PK)
  cooperative_id (FK -> cooperatives.id)
  worker_id (FK -> workers.id)
  period_start (date)
  period_end (date)
  total_hours / total_shifts (decimal)
  wage_rate (decimal)
  gross_amount (decimal)
  status (enum: "pending", "approved", "paid", "failed")
  approved_by (FK -> users.id, nullable)
  approved_at (datetime, nullable)
  paid_at (datetime, nullable)
  moolre_reference (string, nullable)
  failure_reason (text, nullable)
  created_at
```

### 2.7 Roles

New roles for solo_farm orgs (on the `users` table, existing `role` field):

- `farm_owner` — full access (admin-equivalent for solo org)
- `farm_manager` — manage workers, tasks, attendance, approve payouts
- `supervisor` — log attendance, view schedules

Existing roles (`admin`, `finance_officer`) remain for cooperative orgs.

---

## 3. API Endpoints

### 3.1 Worker CRUD (`/workers`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/workers` | List workers (scoped to current coop) |
| POST | `/workers` | Create worker |
| PATCH | `/workers/{id}` | Update worker |
| DELETE | `/workers/{id}` | Soft-delete (status=inactive) |

Gated by `farm_owner`, `farm_manager` roles.

### 3.2 Task Management (`/tasks`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List work tasks |
| POST | `/tasks` | Create task + assign workers |
| PATCH | `/tasks/{id}` | Update task status |
| POST | `/tasks/{id}/assign` | Assign workers to task |

### 3.3 Attendance (`/attendance`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/attendance` | List attendance records |
| POST | `/attendance` | Log worker attendance (with task reference) |
| GET | `/attendance/summary` | Aggregate for payroll period |

### 3.4 Farm Production (`/production/farm`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/production/farm` | List farm production records |
| POST | `/production/farm` | Log planting/harvest |
| PATCH | `/production/farm/{id}` | Update record |

### 3.5 Payroll (`/payroll`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/payroll/summary` | Pending payroll summary for period |
| POST | `/payroll/approve` | Approve wage run (creates payout records) |
| POST | `/payroll/disburse` | Process approved payouts via Moolre |
| GET | `/payroll/history` | Past payout history |

### 3.6 Organization Type

| Method | Path | Description |
|--------|------|-------------|
| PATCH | `/cooperatives/{id}/type` | Set organization_type (or spawn solo sub-entity) |

### 3.7 Signup

Add `organization_type` field to signup request. If `solo_farm`, default subscription_plan to `"solo"`.

---

## 4. Frontend Changes

### 4.1 Org-Aware Navigation

`NAV_GROUPS` in `DashboardPage.jsx` becomes a function:
```
getNavGroups(organization_type) -> NavGroup[]
```

**Cooperative** (unchanged):
Operations: Overview, Members, Production, Agro-AI Scores  
Finance: Payments, Loans  
Communications: SMS, USSD  
Governance: Activity  
Account: Settings

**Solo Farm**:
Operations: Overview, Workers, Tasks, Attendance, Production, Payroll  
Communications: SMS, USSD  
Governance: Activity  
Account: Settings

### 4.2 New Pages/Sections

- **Workers** — table CRUD (name, phone, wage_rate, role, status), add/edit modal
- **Tasks** — create task form, assignment picker, status board (open/in_progress/completed)
- **Attendance** — calendar/list view, log attendance per worker/task, summary for payroll
- **Production** — log planting/harvest, farm-level records
- **Payroll** — pending summary with approve button, payout history with status

### 4.3 Shared Components

Reuse from existing dashboard: `DashboardTableToolbar`, `DashboardPagination`, `useDashboardTable` hook, `ModalPresence`, skeleton loaders.

### 4.4 Section Gating

If a solo_farm user navigates to `/dashboard/members`, redirect to `/dashboard/workers`. Show empty states for cooperative-only sections: "This feature is only available for cooperatives."

### 4.5 Pricing Page

Add Solo plan to `PLANS` array in `PricingPage.jsx`:
- GHS 99/mo, up to 20 workers, tasks + attendance + payroll, 200 SMS/mo, worker USSD

---

## 5. Worker USSD/SMS

### 5.1 USSD Menus

Workers authenticate by phone (same pattern as farmers but resolved via `workers` table):

- Option 1: "My schedule" — today's/upcoming assigned tasks
- Option 2: "My pay" — last payout amount + date, next expected payout

No access to member flows (loans, dues, trust scores).

### 5.2 SMS Notifications

Automated SMS for:
- Task assigned
- Payout confirmation
- Schedule reminder

Reuse existing SMS infrastructure (`communications_service.py` + `MoolreService.send_sms()`).

---

## 6. Billing

### 6.1 Solo Plan

Add `"solo"` to valid `subscription_plan` values on `cooperatives`.

Solo plan entitlements:
- Worker fleet: up to 20
- SMS quota: 200/mo
- Feature flags: tasks, attendance, payroll, farm production

### 6.2 Entitlement Enforcement

Reuse the M3 plan catalog approach (issue #232). The solo plan is added to the catalog with its limits. Enforcement middleware checks plan caps on worker count, SMS usage.

---

## 7. Implementation Phases

### Phase 0: Foundation
- DB migration: `organization_type` on cooperatives, `workers` table, new roles
- Backend: signup org type, worker CRUD API, role enforcement
- Frontend: org-aware signup, nav gating
- Tests: worker CRUD, role gating, org-type signup

### Phase 1: Tasks + Attendance
- DB: `work_tasks`, `worker_assignments`, `worker_attendance` tables
- Backend: task CRUD, assignment, attendance logging
- Frontend: Tasks section, Attendance section

### Phase 2: Farm Production
- DB: `farm_productions` table
- Backend: farm production CRUD
- Frontend: Production section for solo farms

### Phase 3: Wage Payroll
- DB: `wage_payouts` table
- Backend: payroll calculation, approval workflow, Moolre transfer
- Frontend: Payroll section

### Phase 4: Billing + USSD
- Solo plan in catalog
- Worker USSD menus
- Worker SMS notifications

---

## 8. Open Questions

- Should a cooperative be able to spawn a solo_farm sub-entity, or should that be a separate signup? (Design assumes signup-level choice, with potential for sub-entity later.)
- Worker wage payout: use existing Moolre `initiate_transfer` directly, or wait for M2 PaymentProvider port? (Design assumes direct use of existing transfer path, with port adoption as future refactor.)
