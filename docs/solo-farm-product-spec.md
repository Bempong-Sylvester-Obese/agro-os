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
