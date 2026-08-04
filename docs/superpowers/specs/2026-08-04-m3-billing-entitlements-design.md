# M3 — B2B Billing & Entitlements Design

**Date:** 2026-08-04
**Milestone:** M3

---

## Current Bugs (Fixed)

### #230 — Growth Plan Granted Before Payment
BUG: Webhook sets subscription_status="active" but never updates subscription_plan. Paying Growth customers stay on Starter.
FIX: Embed plan key in external_ref (`sub_upg_{coop_id}_{plan}_{ts}`). Update subscription_plan on webhook success.

### #231 — Subscription Fields Missing from API
BUG: CooperativeResponse schema doesn't include subscription_plan/status/expires_at. Settings always shows "Inactive".
FIX: Add fields to CooperativeResponse and CooperativeUpdate schemas.

## New Features

### #232 — Backend Plan Catalog
Create `backend/app/services/plans.py` with plan definitions:
| Plan | Price | Members | Workers | SMS/mo | Features |
|------|-------|---------|---------|--------|----------|
| starter | Free | 10 | N/A | 100 | members, payments |
| solo | GHS 99 | N/A | 20 | 200 | workers, tasks, attendance, payroll |
| growth | GHS 299 | 500 | N/A | 1000 | scores, loans, USSD, commerce |
| enterprise | Custom | Unlimited | Custom | Unlimited | multi-coop, SLA |

### #233 — Enforce Entitlements
- Member creation: check against plan member cap on POST /farmers
- SMS dispatch: check against plan SMS quota (track via cooperative.sms_count_this_month)
- Feature gating: honor plan feature list

### #234 — Subscription Lifecycle
States: trial → active → past_due → expired. Renewal extends active. Cancel sets to expire. Webhook auto-extends 30 days.

### #235 — Payment Intent Verification
- external_ref encodes plan + cooperative + timestamp
- Webhook verifies amount matches plan price before activation
- Idempotent: same webhook replayed doesn't double-extend

### #236 — Billing Portal UI
Enhance Settings page: plan badge, status indicator, member usage bar, upgrade/downgrade buttons, billing history stub.

### #237 — Enterprise Multi-Coop (p2)
Deferred — requires significant architectural changes. Document in plans.py as future.
