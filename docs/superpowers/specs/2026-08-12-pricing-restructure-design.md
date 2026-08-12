# Pricing Restructure Design

Date: 2026-08-12
Status: Approved (pending spec review)

## Context

The existing pricing system is mature but has three problems:

1. **Plan-to-audience mismatch.** Starter → Growth → Enterprise is a cooperative journey, but Solo Farm (an individual-farmer product) sits in the middle of that ladder. Features don't connect, and a cooperative on the free tier has no natural upgrade path (10 members free → GHS 299 Growth).
2. **Deceptive order summary.** `SubscriptionPage` shows "Billing today: GHS 0" for paid plans, then redirects to a Moolre payment after signup. Users are ambushed by payment.
3. **Unpaid accounts in limbo + backend drift.** Users create accounts before paying, leaving unpaid cooperatives in the DB. The backend `plan_prices` dict only has `growth`, so Solo Farm checkout is broken. The webhook hardcodes a 30-day extension regardless of amount.

## Target audience

Mostly cooperatives, with individual farmers as a real but secondary segment.

## Plan structure

Two tracks, displayed as two stacked sections on the pricing page.

### Cooperative track

| Plan | Capacity | Price |
|---|---|---|
| Starter | 10 members | Free |
| Growth (base) | 50 members | GHS 299/mo |
| Growth (+50) | 100 members | GHS 449/mo |
| Growth (+100) | 200 members | GHS 599/mo |
| Enterprise | Unlimited, multi-coop | Custom |

Feature gating:

- **Starter:** member register, MoMo collections, member/dues dashboard, 100 SMS/mo, email support.
- **Growth:** everything in Starter plus AgroCredit Trust Scores, USSD access, higher SMS, priority support.
- **Enterprise:** multi-cooperative administration, API and integrations, custom USSD, migration support, dedicated account manager, SLA.

### Solo Farm track

| Tier | Workers | Price |
|---|---|---|
| Solo Farm | 20 workers | GHS 99/mo |
| Solo Farm | 50 workers | GHS 199/mo |
| Solo Farm | 100 workers | GHS 349/mo |
| Solo Farm | Custom count | Custom quote |

Feature gating: worker management, task management, attendance tracking, wage payroll, worker USSD access.

## Payment flow

### Paid plans (Growth, Solo Farm)

1. Pricing page → user picks plan and selects member/worker band (card shows the real computed total).
2. Order form (single step): org name, location, member/worker count, role.
3. Order summary with the real total (plan + band).
4. Moolre checkout for the exact total.
5. On success → redirect to signup with a `checkout_id`.
6. Signup creates admin + cooperative, persisted with `subscription_plan`, `subscription_band`, `subscription_status=active`, `subscription_expires_at = now + 30 days`.
7. Workspace activated immediately.

### Free plan (Starter)

1. Pricing page → Starter → order form → summary → signup directly (no checkout).
2. Signup persists `subscription_status=active`, no expiry.

## Backend changes

### 1. Single pricing source

- New module `backend/app/config/plans.py` holding plan keys, bands, prices, and feature lists.
- New public endpoint `GET /plans` (no auth) returning this data.
- Checkout, webhook, and signup read prices from this module.
- Frontend `PLANS` and `PLAN_DETAILS` fetch from `GET /plans` instead of hardcoding.

### 2. Pre-checkout endpoint

- New `POST /subscriptions/pre-checkout` (no auth).
- Request: `plan_key`, `band`, org details.
- Validates plan + band, computes exact amount from the pricing module.
- Creates a `PendingCheckout` record (new table) with the amount, plan, band, and org details.
- Returns Moolre `authorization_url`; `external_ref = sub_pre_{checkout_id}`.

### 3. Webhook

- Handle `sub_pre_*` external refs: mark the `PendingCheckout` as paid, storing plan/band/amount.
- Keep `sub_upg_*` for future in-app upgrades.
- Map band → correct expiry. Remove hardcoded 30-day logic; derive from plan/band.

### 4. Signup

- `SignupRequest` accepts `checkout_id` (optional) and `subscription_band` (optional).
- If `checkout_id` is present, verify the pending checkout is paid; otherwise reject.
- Persist `subscription_plan`, `subscription_band`, `subscription_status=active`, and correct `subscription_expires_at`.

### 5. Data model

- New `PendingCheckout` table: id, plan_key, band, amount, org details, status (pending/paid/expired), created_at.
- `Cooperative` gains `subscription_band` column (nullable).

## Frontend changes

### PricingPage

- Two stacked sections: "For Cooperatives" (Starter/Growth/Enterprise) and "For Independent Farmers" (Solo Farm tiers).
- Growth card has a member-band selector; Solo Farm has a worker-band selector.
- Cards compute and show real totals. Data from `GET /plans`.

### SubscriptionPage

- Single form → order summary with real total → "Pay GHS X" (paid) or "Start free workspace" (Starter).
- On payment success, redirect to signup with `checkout_id`.

### AuthPage

- Reads `checkout_id` param, keeps intent prefill, calls signup with `checkout_id`.

### Upgrade trigger (minimal)

- Small "Upgrade"/capacity CTA that calls existing `POST /subscriptions/checkout` (auth-required, reused for upgrades) when a user hits a cap.
- Full billing management (downgrade, cancel, proration) deferred to a follow-up.

## Out of scope (this round)

- Full self-serve billing settings page (downgrade, cancel, proration, plan history).
- DB-backed admin UI for plan configuration.
- Custom-quote workflow for Enterprise and Solo Farm custom counts (talk-to-sales remains a contact form).

## Error handling

- Pre-checkout: invalid plan/band → 400; Moolre link failure → 400 with "Failed to generate payment link".
- Signup with `checkout_id`: unpaid/expired/missing checkout → 403/404, no cooperative created.
- Webhook: idempotent — already-paid checkout is a no-op, never double-extends expiry.

## Testing

- Backend: pre-checkout computes correct band totals; signup rejects unpaid checkout; webhook marks paid and sets correct expiry; `GET /plans` returns both tracks.
- Frontend: pricing page renders two tracks with computed totals; subscription flow shows real total; Starter skips checkout; signup carries `checkout_id`.
