# Solo Farm — Product Specification

This is the product spec for the Solo Farm tier (#252). Implementation
details of the original design live in
[`superpowers/specs/2026-07-30-m5-solo-farm-platform-design.md`](superpowers/specs/2026-07-30-m5-solo-farm-platform-design.md);
this document is the shorter, binding rule set.

## Overview

AgroOS serves two distinct organizational models:
- **Cooperative** — democratically governed groups of farmer-members with dues, loans, trust scoring, and commerce.
- **Solo Farm** — independent farm owners managing wage laborers with task tracking, attendance, and payroll.

A workspace is one or the other (`cooperatives.organization_type`). The same
Postgres schema holds both; visibility and write-guards decide which modules
apply.

## Rule: workers are never memberships

**Do not model workers as `CooperativeMembership` (or `Farmer`) rows.**

| | Worker | Member |
|---|---|---|
| Table | `workers` | `farmers` + `cooperative_memberships` |
| Money | Wage payout (`wage_payouts`) | Dues, loans, produce settlements |
| Score | None | AgroCredit trust score |
| Identity | Phone within one farm | Farmer record, optionally shared across cooperatives |
| Channel | Worker USSD (schedule / pay) | Member USSD (dues / loans / announcements) |

Overloading membership would mix wage labour into dues ageing, trust scores,
loan eligibility and produce entitlements. New solo-farm features must FK to
`workers.id`, never to `cooperative_memberships.id`. A future "this person is
both a member of Coop A and a worker on Farm B" story is two rows in two
tables, not one polymorphic record.

This rule is enforced in code by `organization_type` guards (#254, #256):
worker/task/labor-attendance/payroll mutations return 403 on a cooperative;
member/dues/loan/score mutations stay cooperative-only.

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
- Cooperative *meeting* attendance (that feed is a trust-score input, not a shift log)

### Cooperative (`organization_type = "cooperative"`)

**Visible:**
- Overview dashboard
- Members
- Meeting attendance (Trust Score input)
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
- Labor attendance / payroll
- Farm-level production (cooperatives use per-member production)

Cooperatives **do** have meeting attendance (`/farmers/{id}/attendance`) as a
Trust Score input. That is a different table and UI from worker shift logs.

## Subscription Tiers

| Tier | Price | Target | Member cap | Worker cap | Key features |
|------|-------|--------|------------|------------|--------------|
| **Starter** | Free | Emerging cooperatives | 10 | not included | Member register, dues, dashboard |
| **Solo** | GHS 99/mo | Independent farms | not included | 20 / 50 / 100 / custom bands | Workers, tasks, labor attendance, payroll, USSD |
| **Growth** | GHS 299/mo | Operating cooperatives | 50 / 100 / 200 bands | not included | AgroCredit, USSD, commerce |
| **Enterprise** | Custom | Networks / institutions | unlimited | custom | Multi-cooperative parent, SLA |

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

`admin` exists on both tracks (the signup account). Invite/update must only
offer `SOLO_ROLES` inside a solo farm and `COOP_ROLES` inside a cooperative
(#255).

## MVP vs later

The original M5 design phased foundation → tasks → production → payroll →
billing/USSD. Most of that is already on `dev`. What remains, and what is
explicitly later:

| Slice | Status | Issue |
|---|---|---|
| `organization_type` + solo signup + nav gating | Shipped | — |
| `workers` CRUD, tasks, labor attendance, farm production, wage payroll | Shipped | — |
| Solo plan + worker bands in the catalogue | Shipped | — |
| Refuse worker create on a cooperative; `hire_date` / `pay_type` / `user_id` on `Worker` | Shipped | #254 |
| Invite/update roles filtered by org type | Shipped | #255 |
| `solo_farm` guard on task and labor-attendance mutations | **MVP remaining** | #256 |
| Band-aware `max_workers` + payroll feature gate | **MVP remaining** | #260 |
| Worker USSD (schedule / last pay) | Later | out of M5 close-out |
| Worker SMS (task assigned, payout, reminder) | Later | out of M5 close-out |
| Cooperative spawning a solo-farm sub-entity | Later | out of M5 close-out |
| A person who is both a coop member and a farm worker | Later — two rows, never one | — |

## Non-goals (this milestone)

- Treating workers as members, or giving workers trust scores, dues or loans.
- Opening the commerce stack (intake → settlement) on a solo farm.
- Sharing one `User` login between a worker's USSD identity and a dashboard role (optional `workers.user_id` is a future link, not required for payroll).
- Changing tenancy: a solo farm is still one cooperative-scoped tenant.
