# M5 — Solo Farm / Worker Platform Completion Design

**Date:** 2026-08-03
**Milestone:** [M5 — Solo Farm / Worker Platform](https://github.com/Bempong-Sylvester-Obese/agro-os/milestone/9)
**Status:** Design

---

## Context

Significant M5 work was merged into `dev` from `feat/m5-solo-farm-phase0`. This spec covers only the **remaining gaps** identified against the 9 milestone issues.

### Already complete (no action needed)

| # | Issue | Status |
|---|-------|--------|
| 256 | Labor attendance / task logging | Backend + frontend done |
| 257 | Wage payout via payment provider (Moolre) | Payroll summary -> approve -> disburse with Moolre transfers done |
| 258 | Solo-farm dashboard IA | Conditional sidebar, redirects, tab titles all done |
| 259 | Worker-facing USSD/SMS | `/ussd/worker/menu` exists; SMS sent on task assign + payout |
| 260 | Solo Farm pricing tier | GHS 99/mo plan in PricingPage + SubscriptionPage |

---

## Remaining Work

### 1. #252 — Research Spec Document

Write a concise product spec clarifying:

- **Workers vs Members:** Workers are non-member laborers managed by a farm owner. They have no cooperative membership, no AgroCredit eligibility, no trust scores. Members are cooperative farmers with equity, dues, loans, scoring.
- **Modules to hide for solo_farm orgs:** Members, Payments, Loans, Commerce (intake/aggregation/buyers/sales/settlements), Agro-AI scores.
- **Modules to show for solo_farm orgs:** Workers, Tasks, Attendance, Payroll, Farm Production, SMS, USSD, Activity.
- **Modules shared:** Overview (dashboard), Settings, Activity log, SMS broadcasts, USSD activity.

**Artifact:** `docs/solo-farm-product-spec.md` (completed)

### 2. #253 — Complete Organization Type Integration

- **PricingPage:** Add Solo Farm column to the comparison table (currently only Starter, Growth, Enterprise). Also cap Starter plan member capacity at 10 (was 50).
- **Supabase migration:** Add missing columns to supabase schema: `organization_type`, `subscription_plan`, `subscription_status`, `ussd_code`, `onboarding_role`, `is_active`, `updated_at` on cooperatives table

### 3. #254 — Worker CRUD Supabase Sync

Create supabase migration for M5 tables with proper RLS:

- `workers` table with `(cooperative_id, phone)` unique constraint
- `work_tasks` table
- `worker_assignments` table
- `worker_attendance` table
- `wage_payouts` table
- `farm_productions` table

All tables: RLS enabled with fail-closed, `service_role`-only policies. Browser
clients use FastAPI; direct Supabase `authenticated` access is unsupported
because the application uses custom FastAPI JWTs. Current tenant isolation is
provided by authenticated API scope checks, not by RLS on the backend's
owner/superuser connection. Enforced database RLS requires a future restricted
runtime role and transaction-scoped cooperative context.

### 4. #255 — 3-Tier RBAC for Dashboard Users

Role hierarchy for dashboard users:

| Capability | farm_owner | farm_manager | supervisor |
|---|---|---|---|
| Workers CRUD | Full | Full | None |
| Tasks CRUD | Full | Full | None |
| Attendance CRUD | Full | Full | Log only |
| Payroll View | Full | Full | None |
| Payroll Approve | Full | Full | None |
| Payroll Disburse | Full | None | None |
| Production CRUD | Full | Full | None |

**Backend changes:**
- Update `require_roles()` guards on each route to match the matrix
- `farm_owner`: allowed on all M5 routes
- `farm_manager`: blocked from POST `/payroll/disburse`
- `supervisor`: only allowed on POST `/attendance/`

**Frontend changes:**
- Resolve user role from JWT/auth info
- DashboardPage: conditionally hide sections per role
- Workers: hide Add/Edit/Deactivate for supervisor
- Tasks: hide Create/Edit/Complete/Cancel for supervisor
- Payroll: hide Approve for supervisor; hide Disburse for farm_manager and supervisor
- Production: hide Add/Edit for supervisor

---

## Implementation Order

1. **#252** — Research spec doc (no code, informs everything)
2. **#253** — Org type integration (foundation)
3. **#254** — Worker CRUD supabase sync (data layer)
4. **#255** — RBAC enforcement (access control)

---

## Existing Infrastructure (Reference)

### Backend
- **Models:** `worker.py`, `worker_attendance.py`, `work_task.py`, `wage_payout.py`, `farm_production.py`, `models.py` (Cooperative with `organization_type`)
- **Routes:** `workers.py`, `attendance.py`, `tasks.py`, `payroll.py`, `farm_production.py`, `worker_ussd.py`
- **Schemas:** `worker.py`, `worker_attendance.py`, `work_task.py`, `wage_payout.py`, `farm_production.py`, `ussd_schemas.py`, `auth.py` (organization_type in SignupRequest)
- **RBAC:** `require_roles(*allowed_roles)` dependency in `auth_service.py`
- **Payment:** `moolre_service.py` (843 lines, no provider abstraction)

### Frontend
- **API:** `workers.js`, `attendance.js`, `tasks.js`, `payroll.js`, `farm_production.js`
- **Components:** `Workers.jsx`, `WorkerForm.jsx`, `Attendance.jsx`, `Tasks.jsx`, `TaskForm.jsx`, `Payroll.jsx`, `FarmProduction.jsx`
- **Pages:** `DashboardPage.jsx` (conditional nav groups), `PricingPage.jsx`, `SubscriptionPage.jsx`
- **Auth:** `auth.js` (signup with organization_type), `utils/auth.js` (getOrganizationType, getAuthInfo)

### Database
- **Alembic:** `007_organization_type.py`, `007_phase1.py`, `011_merge_heads.py`
- **Supabase:** Missing worker tables and org type columns

### Tests
- `test_attendance.py`, `test_farm_production.py`, `test_payroll.py`, `test_tasks.py` (16 tests total)
- Frontend: no M5-specific tests
