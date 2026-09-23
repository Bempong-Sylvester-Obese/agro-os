# M1 Production Hardening + M2 Architecture Decoupling — Design Spec

**Date:** 2026-08-18
**Milestones:** M1 (3 open issues), M2 (7 open issues)
**Status:** Approved

---

## Overview

Close all open issues in M1 (Production Hardening) and M2 (Architecture Decoupling). M1 locks down production safety: demo gating, API-only tenancy documentation, and docs rewrite. M2 decouples the backend from Moolre-specific coupling: rename DB columns, wire the PaymentEvent domain model, extract domain services, unify USSD gateways, and document boundaries.

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tenancy model | API-only (JWT + route filtering) | Low risk, already consistently applied, sufficient for trusted B2B platform |
| DB column rename | Clean break (no dual-column transition) | No external consumers, cleaner long-term |
| Frontend rename | Full rename (CSS + functional + marketing) | Consistent, no half-measures |
| USSD unification | Application service + thin adapters | Cleanest architecture, eliminates all duplication |
| Execution order | Strict dependency chain | Each step builds on the previous, lowest merge risk |

---

## M1 — Production Hardening

### M1 #223 — Gate demo seed/reset in production

**Already mostly done.** Backend gates `seed_demo_data` and admin demo-reset behind `APP_ENV != production`.

Changes:
- **Backend**: Add explicit `DEMO_DATA_ALLOWED=true` env check as second guard on demo-reset endpoints.
- **Frontend `Settings.jsx`**: Hide "Demo data danger zone" section when `import.meta.env.PROD` is true.
- **Frontend `config.js`**: Remove dead `withDemoFallback` export (never imported anywhere).
- **Frontend `plans.js`**: Remove `PLANS_FALLBACK` hardcoding — show error toast in production instead of fake pricing.
- **Docs**: Note demo gating in SECURITY.md.

### M1 #240 — API-only tenancy lockdown

Adopt API-only approach. Document and harden.

Changes:
- **`SECURITY.md`**: Document tenancy model — JWT `cooperative_id` as primary isolation, route handlers must filter by cooperative, DB role is superuser (bypasses RLS). Add threat model section.
- **`cooperative_scope.py`**: Add `require_cooperative_scope()` that raises 403 if no cooperative resolved (fail-closed).
- **`COMPLIANCE.md`**: Update to reflect API-only tenancy is enforced, RLS SQL retained for future.

### M1 #241 — Rewrite README/SECURITY/COMPLIANCE

- **README.md**: Remove hackathon MVP framing. Rewrite as B2B cooperative platform. Add solo-farm tier pointer. Update production setup instructions.
- **SECURITY.md**: Update auth model, webhook verification, rate limits, tenancy model, open gaps with issue links.
- **COMPLIANCE.md**: Remove draft/hackathon caveats, align with current auth and data model.

---

## M2 — Architecture Decoupling

**Execution order:** #229 → #228 → #242 → #225 → #226 → #227 → #243

### M2 #229 — Deduplicate subscriptions router + remove patch file

Quick win, no dependencies.

- **`backend/main.py`**: Remove duplicate `include_router(subscriptions.router)`.
- **Repo root**: Delete `ussdk-payment-flow.patch`.
- Verify app boots and OpenAPI lists subscription routes once.

### M2 #228 — Remove hardcoded webhook URL + Moolre-named paths

Quick win, no dependencies.

- **`moolre_service.py`**: Replace hardcoded `settings.agroos_base_url + "/webhooks/moolre/payment"` with configurable `settings.webhook_callback_path` (default `/webhooks/payment`).
- **`rate_limit.py`**: Replace hardcoded Moolre webhook path strings with config constants.
- **`main.py`**: Remove "Powered by Moolre" from app description.
- **Route paths**: Keep `/webhooks/moolre/*` for backward compat. Add provider-neutral aliases (`/webhooks/payment`, `/webhooks/ussd`).

### M2 #242 — Rename moolre_* columns to provider-neutral names

Foundation for all subsequent refactoring. Alembic migration + full code update.

**Column renames:**

| Table | Old | New |
|-------|-----|-----|
| `cooperatives` | `moolre_account_number` | `wallet_account_id` |
| `transactions` | `moolre_reference` | `provider_payment_ref` |
| `transactions` | `moolre_transfer_ref` | `provider_transfer_ref` |
| `loans` | `moolre_transfer_ref` | `provider_transfer_ref` |
| `communication_logs` | `moolre_ref` | `provider_ref` |
| `payment_webhook_events` | `moolre_reference` | `provider_payment_ref` |

**Backend changes:**
- `models.py`: Rename 6 columns
- `schemas.py`: Rename 11 moolre_* fields
- All route/service files referencing these columns

**Frontend changes:**
- `Settings.jsx`: `moolre_account_number` → `wallet_account_id`
- `Loans.jsx`: `moolre_transfer_ref` → `provider_transfer_ref`
- `Payments.jsx`: `moolre_ussd` → `farmer_ussd`
- `Payroll.jsx`: `moolre_reference` → `provider_payment_ref`
- CSS: Rename all `moolre-*` classes → `integration-*`
- Marketing copy: Remove "Moolre" references from homepage

### M2 #225 — Normalize inbound webhooks to PaymentEvent

Wire the existing but unused `PaymentEvent` domain model into the webhook flow.

- **`webhooks.py` `_normalize_payload`**: Update to use new column names from #242.
- **`webhooks.py` `_process_payment_payload`**: Refactor to:
  1. Call `_normalize_payload()` → `PaymentEvent`
  2. Pass to `services/payment_service.py::process_payment_event()`
  3. Remove inline Moolre-specific status parsing
- **`services/payment_service.py`**: Use `provider_payment_ref` instead of `moolre_reference`. Handle all three payment types via `PaymentEvent.metadata`.
- **Moolre adapter** (`providers/moolre_adapter.py`): Only place that knows Moolre webhook shape. Translates `X-Moolre-Signature` + Moolre JSON → `PaymentEvent`.

### M2 #226 — Extract domain services

Extract business logic from fat route modules into callable domain services.

**New/expanded services:**

| Service | Source | Responsibility |
|---------|--------|----------------|
| `dues_service.py` (expand) | `webhooks.py`, `ussdk_hooks.py` | Dues collection orchestration |
| `loan_workflow.py` (expand) | `webhooks.py`, `ussdk_hooks.py` | Loan repay/disburse via mobile money |
| `subscription_service.py` (new) | `webhooks.py` lines 174-303 | Pre-checkout + upgrade activation |

**Pattern:** Routes and USSD adapters call services only. No route imports from other routes. Services are stateless functions taking `db` + domain objects.

### M2 #227 — Unify three USSD gateways

One application service, three thin adapters.

**New structure:**

```
backend/app/
  services/
    ussd_application.py    ← menu state machine + finance orchestration
  adapters/
    moolre_ussd.py         ← Moolre JSON → UssdRequest → MoolreResponse
    ussdk_adapter.py       ← USSDK JSON → UssdRequest → USSDKResponse
    at_adapter.py          ← Africa's Talking form → UssdRequest → AT response
```

**`UssdApplicationService`** owns:
- Menu navigation state machine (currently 700+ lines in `webhooks.py`)
- Finance operations (calls domain services from #226)
- Session management
- Returns provider-neutral `UssdResponse` (text + session state)

Each adapter: ~30-50 lines translating gateway format ↔ `UssdRequest`/`UssdResponse`.

### M2 #243 — Document external-service boundaries

Last, after all refactoring.

- **`docs/architecture.md`** (new): Ports/adapters pattern, provider coupling boundaries, `PaymentProvider`/`SmsProvider` ports, webhook normalization flow, steps to add a new provider.
- **`CONTRIBUTING.md`**: Architecture constraints section — "Do not import moolre_* in domain code", "New providers implement the port interface".
- **README.md**: Link to architecture doc.

---

## Files Modified

### Backend (estimated)
- `backend/main.py` — router dedup, description update
- `backend/app/config.py` — new env vars (`webhook_callback_path`)
- `backend/app/models/models.py` — column renames
- `backend/app/schemas/schemas.py` — field renames
- `backend/app/routes/webhooks.py` — major refactor (PaymentEvent wiring, USSD extraction)
- `backend/app/routes/admin.py` — demo gating polish
- `backend/app/routes/ussd.py` — becomes thin adapter
- `backend/app/routes/ussdk_hooks.py` — becomes thin adapter
- `backend/app/routes/transactions.py` — column name updates
- `backend/app/routes/loans.py` — column name updates
- `backend/app/routes/subscriptions.py` — column name updates
- `backend/app/routes/communications.py` — column name updates
- `backend/app/services/moolre_service.py` — webhook URL config
- `backend/app/services/payment_service.py` — PaymentEvent wiring, column names
- `backend/app/services/dues_service.py` — expanded with extracted logic
- `backend/app/services/loan_workflow.py` — expanded with extracted logic
- `backend/app/services/subscription_service.py` — new
- `backend/app/services/ussd_application.py` — new
- `backend/app/middleware/rate_limit.py` — config-driven paths
- `backend/app/dependencies/cooperative_scope.py` — fail-closed helper
- `backend/app/domain/payment_event.py` — unchanged (already correct)
- `backend/app/adapters/moolre_ussd.py` — new
- `backend/app/adapters/ussdk_adapter.py` — new
- `backend/app/adapters/at_adapter.py` — new

### Frontend (estimated)
- `frontend/src/api/config.js` — remove dead `withDemoFallback`
- `frontend/src/api/plans.js` — remove `PLANS_FALLBACK`
- `frontend/src/components/dashboard/Settings.jsx` — field rename, demo section hide
- `frontend/src/components/dashboard/Loans.jsx` — field rename
- `frontend/src/components/dashboard/Payments.jsx` — field rename
- `frontend/src/components/dashboard/Payroll.jsx` — field rename
- `frontend/src/styles/global.css` — CSS class renames
- `frontend/src/pages/HomePage.jsx` — marketing copy update
- `frontend/src/components/Footer.jsx` — anchor link update

### Docs
- `README.md` — rewrite
- `SECURITY.md` — rewrite
- `COMPLIANCE.md` — rewrite
- `CONTRIBUTING.md` — add architecture constraints
- `docs/architecture.md` — new

### DB
- New Alembic migration for column renames

### Deleted
- `ussdk-payment-flow.patch` (repo root)

---

## Testing Strategy

- **Existing tests**: Run `npm run test:backend` after each milestone step. Critical paths: webhook processing, USSD flows, subscription activation, loan disbursement.
- **Migration smoke test**: Verify Alembic migration runs cleanly, data backfills correctly.
- **Manual verification**: Boot app, check OpenAPI spec (no duplicate routes), verify frontend builds.
- **Column rename**: Spot-check that all `moolre_*` references are gone via grep.

---

## Risks

1. **DB migration on live data**: Clean break rename means any external integrations reading `moolre_*` columns will break. Mitigated by no known external consumers.
2. **USSD regression**: The state machine refactor is the highest-risk change. Mitigated by keeping the existing behaviour parity and testing all menu paths.
3. **Frontend CSS rename churn**: ~52 matches across CSS. Mitigated by find-and-replace with no functional change.
