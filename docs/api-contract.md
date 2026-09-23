# Frontend–Backend API Contract

Base URL: `VITE_API_URL` (default `http://localhost:8000`). CORS allows all origins in development and the Vercel frontend URL in production.

Interactive OpenAPI docs: `{VITE_API_URL}/docs`

## ID schemes

| Surface | ID format | Example | Notes |
|---------|-----------|---------|-------|
| CRM farmers (`/farmers/*`) | Integer DB primary key | `1` | Canonical CRM identifier; used in POST bodies and path params. |
| Agro-AI assessments (`/api/farmers`) | Zero-padded member code string | `GH-0001` | Backend assigns `GH-{db_id:04d}` when assessments are built from DB farmers (`format_member_code` in `db_bridge.py`). |
| Frontend display (CRM tabs) | Padded member code (display only) | `GH-0001` | `formatFarmerId()` in `frontend/src/api/transactions.js` pads integer `farmer.id` / `transaction.farmer_id` for Payments and related views. |

**Canonical rule:** CRM routes expose the raw integer `id`. Agro-AI routes expose a `farmer_id` string that is already formatted by the backend — never a bare integer. The frontend does not re-pad Agro-AI `farmer_id` values; it renders them as returned. Padding for CRM integer IDs happens only in frontend display helpers, not in API responses from `/farmers/*`.

When the database is seeded, Agro-AI assessments are built from DB farmer records and the backend emits `GH-0001`-style codes (`GH-` + four-digit zero-padded DB id). When the DB is empty, Agro-AI falls back to synthetic demo farmers with fixed member codes (`GH-0103`, `GH-0042`, etc.) that are not tied to a DB row.

## Dashboard routes

### Overview / Members

| UI | Method | Path | Response |
|----|--------|------|----------|
| Member list | GET | `/farmers/` | `FarmerResponse[]` |
| Add member | POST | `/farmers/` | `FarmerResponse` |
| Agro-AI scores | GET | `/api/farmers` | Assessment objects (see below) |
| Credit summary | GET | `/api/agro-ai/credit-summary` | Summary object |

**FarmerResponse** (abbreviated):

```json
{
  "id": 1,
  "name": "Abena Mensah",
  "phone": "+233552341234",
  "location": "Ashanti",
  "production_focus": "mixed",
  "crop_type": "Maize",
  "animal_type": "Goats",
  "animal_scale": 12,
  "cooperative_id": 1,
  "membership_status": "active",
  "trust_score": 58.0,
  "created_at": "2026-06-01T00:00:00",
  "updated_at": "2026-06-01T00:00:00"
}
```

**Agro-AI assessment** (abbreviated):

```json
{
  "farmer_id": "GH-0001",
  "name": "Abena Mensah",
  "score": 72,
  "eligible": true,
  "risk_band": "Moderate risk",
  "recommendation": "Approve with standard monitoring",
  "top_reasons": ["Strong dues consistency improves repayment confidence"]
}
```

### Payments

| UI | Method | Path | Response |
|----|--------|------|----------|
| Payment history | GET | `/transactions/` | `TransactionResponse[]` |
| Wallet balance | GET | `/transactions/provider/wallet-balance` | Provider wallet object (`/transactions/moolre/wallet-balance` is a legacy alias) |
| Wallet transactions | GET | `/transactions/provider/account-transactions` | Provider transaction list (`/transactions/moolre/account-transactions` is a legacy alias) |
| Webhook audit | GET | `/transactions/webhook-events` | `PaymentWebhookEventResponse[]` |
| Reconcile payment | POST | `/transactions/{transaction_id}/reconcile` | Reconciliation result |

**TransactionResponse** statuses: `pending`, `completed`, `failed`. Channel `13` = MoMo.
Pending collections also expose `customer_action` (`initiating`, `otp`,
`processing_otp`, `approval`, or `none`), `action_expires_at`, and
`initiation_channel`. Production debits originate only from the farmer's
signed USSD session. The dashboard never initiates a debit or accepts an OTP.

### Loans, Production, SMS

| UI | Method | Path |
|----|--------|------|
| Loans tab | GET | `/loans/` |
| Approve/reject request | POST | `/loans/{loan_id}/approve`, `/loans/{loan_id}/reject` |
| Disburse loan | POST | `/loans/{loan_id}/disburse` |
| Send repayment reminder | POST | `/loans/{loan_id}/reminders` |
| Production tab | GET | `/production/` |
| SMS tab | GET/POST | `/communications/logs`, `/communications/sms/broadcast` |

Members use `production_focus` (`crop`, `animal`, or `mixed`). Animal and mixed
members may include `animal_type` and `animal_scale`; legacy `crop_type` and
`acreage` remain available for crop compatibility.

Production records use `production_kind`, `product_name`, `activity`,
`expected_quantity`, `quantity`, `unit`, and `production_date`. Legacy
`crop_type`, `expected_kg`, `quantity_kg`, and harvest fields remain in the
contract during migration. Expected and actual quantities must be compared
within the record's own unit; quantities with different units are not summed.

### USSD & webhooks

| UI | Method | Path |
|----|--------|------|
| USSD log | GET | `/webhooks/ussd/logs` |
| USSD handler (Moolre JSON contract) | POST | `/webhooks/ussd` (legacy alias: `/webhooks/moolre/ussd`) |
| Payment webhook | POST | `/webhooks/payment` (legacy alias: `/webhooks/moolre/payment`) |
| USSD handler (Africa's Talking) | POST | `/ussd/callback` |
| USSDK loan request | POST | `/ussdk/loan-request` |
| USSDK pending payment | POST | `/ussdk/pending-payment` |
| USSDK dues payment | POST | `/ussdk/pay-dues` |
| USSDK loan repayment | POST | `/ussdk/loan-repayment` |

Farmers originate loan requests from the Moolre menu or signed USSDK
`/loan-request` hook. Staff do not create requests; they only review the
resulting `requested` loan. Farmers also initiate dues and loan repayments in
their own signed USSD session. Moolre sends and verifies any required OTP;
AgroOS reuses the original payment reference and never stores OTP values in
transactions or USSD logs. **Complete Pending Payment** is a recovery path for
an interrupted farmer session, not a staff-started collection flow.

### Cooperative profile

| UI | Method | Path |
|----|--------|------|
| Settings sidebar | GET | `/cooperatives/` or `/cooperatives/{id}` |

Optional env: `VITE_COOPERATIVE_ID`.

### Subscriptions and billing

| UI | Method | Path | Notes |
|----|--------|------|-------|
| Pricing page | GET | `/plans` | Plan catalogue (public) |
| Pricing page checkout | POST | `/subscriptions/pre-checkout` | Public. Creates a `pre_checkout` intent (`sub_pre_*`) and returns `{checkout_id, reference, authorization_url, amount}` |
| Settings → change plan | POST | `/subscriptions/checkout` | Auth. Body `{cooperative_id, plan_key, band?}`. Creates a single-use `upgrade` intent for the caller's cooperative and returns `{intent_id, reference, authorization_url, plan_key, band, amount}` |
| Settings → usage bars | GET | `/cooperatives/{id}/usage` | Auth. Usage vs band-aware limits (`members`, `workers`, `sms`) and `features` map for the effective plan; see `docs/billing.md` |
| Settings → billing panel | GET | `/subscriptions/status` | Auth. Applies pending time-based transitions and returns the lifecycle view (`status`, `effective_plan_key`, `paid_access`, `in_grace`, `days_remaining`, ...) |
| Settings → payment history | GET | `/subscriptions/history` | Admin. Intents for the cooperative (signup pre-checkout + upgrades/renewals), newest first: `{items: [{plan_name, band_label, amount, currency, kind, status, outcome: pending\|paid, provider_transaction_id, created_at, paid_at}], total_paid, currency}` |
| Settings → renew | POST | `/subscriptions/renew` | Admin. Single-use intent for the plan/band already on record; 400 on free tier or trial |
| Settings → cancel | POST | `/subscriptions/cancel` | Admin. `{cooperative_id, immediately?: bool}`. Default keeps access until period end |
| Settings → resume | POST | `/subscriptions/resume` | Admin. Undo a cancellation before the period ends (409 otherwise) |

### Organizations (Enterprise)

All routes require `admin`. `/organizations/{id}/...` returns 404 unless `{id}`
is the caller's own `organization_id` (same rule as cooperative scope). The JWT
and `/auth/login` user payload carry `organization_id` (nullable).

| UI | Method | Path | Notes |
|----|--------|------|-------|
| Settings → Organization → create | POST | `/organizations` | `{name, description?, billing_email?}`. Caller's cooperative becomes the first member and the caller becomes organization admin. 409 if either already belongs to an organization |
| Settings → Organization, sidebar switcher | GET | `/organizations/me` | Organization row plus `cooperatives: [{id, name, location, organization_type, is_active_scope}]` |
| Settings → Organization → edit | PATCH | `/organizations/{id}` | Profile fields only (`name`, `description`, `billing_email`). Subscription fields are operator-managed |
| Settings → Organization | GET | `/organizations/{id}/cooperatives` | Member cooperatives |
| Settings → Organization → add cooperative | POST | `/organizations/{id}/cooperatives` | `{name, location?, organization_type?}`. New cooperative starts on the free plan and inherits Enterprise while the contract is live |
| Sidebar switcher / table row → Switch | POST | `/organizations/{id}/switch` | `{cooperative_id}`. Updates the admin's active cooperative and returns a fresh `Token` (`access_token`, `token_type`) with the new scope. Audited as `organization.scope_switched` |
| Settings → Organization → billing | GET | `/organizations/{id}/billing` | `{organization, cooperatives: [{..., effective_plan_key, inherits_organization_plan, members, workers, sms}], totals: {cooperatives, members, workers, sms_this_month, paid, currency}, history}` |

**Payment intents.** Every paid flow records a `PendingCheckout` intent
(plan, band, amount, cooperative) *before* a payment link is issued, and the
link is non-reusable. The payment webhook resolves the provider's
`externalref` to that intent and:

- refuses activation when the paid amount differs from the intent amount
  (recorded as an unprocessed `PaymentWebhookEvent`, "subscription amount mismatch");
- activates the plan/band exactly once (`pending → consumed`); duplicate
  deliveries return "already processed" and do not extend the expiry again;
- never infers the plan from the amount or from the reference string for
  intent-backed payments. References issued before intents existed
  (`sub_upg_<coop>_<plan>_<ts>_<band>`) are still accepted via a legacy path.

`pre_checkout` intents move `pending → paid` on webhook and `paid → consumed`
when signup redeems them with `checkout_ref`.

**Lifecycle.** Free signups start a 14-day Growth trial (`subscription_status =
trial`, plan stays `starter`); paid periods are 30 days with a 7-day grace
period (`past_due`) before `expired`. Limits and feature gates always use the
*effective* plan from `subscription_lifecycle.effective_plan_key`, never the
raw `subscription_plan` column. Routes that need a live paid plan use
`Depends(require_active_subscription(...))`, which returns `402
{"code": "subscription_required"}`. States, transitions, and renewal semantics
are documented in [`docs/billing.md`](billing.md).

**Entitlement errors.** Member caps, SMS quotas, and feature gates respond
`403` with a structured `detail` — `{"code": "plan_limit_reached" |
"sms_quota_exceeded" | "feature_not_in_plan", "message", "plan", ...}` —
rather than a plain string. Clients should read `detail.message` for display
and `detail.code` to decide whether to show an upgrade prompt
(`frontend/src/components/dashboard/UpgradePrompt.jsx`).

### Cooperative commerce

Commerce records are cooperative-scoped and follow explicit state transitions.
Unlike production tracking and scoring, this release's intake, aggregation,
buyer-sale, and settlement workflow remains crop-only:

- Produce intake: record, accept or reject, then assign accepted weight to one
  open aggregation batch.
- Aggregation: close a batch before recording its buyer sale.
- Buyer sale: confirm the commercial terms, record buyer-payment evidence, and
  require a different authorized user to verify receipt of funds.
- Settlement: calculate a snapshot of farmer gross amounts and deductions,
  review it, approve it under maker-checker controls, then execute Moolre
  farmer payouts.

Settlement APIs expose every farmer line with accepted quantity, unit price,
gross amount, itemized deductions, and net payable. Payout retries operate only
on failed lines and preserve the original idempotent references. Loan payouts,
settlement payouts, dues payments, and loan repayments remain separate
transaction purposes.

Core endpoints:

- `POST/GET /intakes/`, then `POST /intakes/{id}/accept|reject|cancel`
- `POST/GET /aggregation-batches/`, `POST /aggregation-batches/{id}/intakes`,
  and `POST /aggregation-batches/{id}/close`
- `POST/GET/PATCH /buyers/`
- `POST/GET /sales/`, `POST /sales/{id}/confirm`, and buyer receipt
  submission plus independent `verify|reject` decisions
- `POST /settlements/sales/{sale_id}/calculate`, `GET /settlements/`,
  and settlement `submit|approve|disburse|retry-failed|reconcile` actions
- CSV exports under `/reports/intake.csv`, `/reports/aggregation.csv`,
  `/reports/buyers.csv`, `/reports/sales.csv`, `/reports/settlements.csv`, and
  `/reports/payout-exceptions.csv`

The core operational exports are `/reports/members.csv`,
`/reports/production.csv`, and `/reports/scores.csv`. They include unified
focus/kind/product/activity/quantity/unit columns while retaining useful legacy
crop columns.

### Authentication and cooperative roles

| UI | Method | Path |
|----|--------|------|
| Login | POST | `/auth/login` |
| Session hydrate (app load) | GET | `/auth/me` |
| Signup | POST | `/auth/signup` |
| Add cooperative user | POST | `/auth/register` |

`POST /auth/login` returns `{access_token, token_type, user, cooperative_name,
organization_type, password_change_required}`. `GET /auth/me` returns the same
`user` fields plus `cooperative_name`, `organization_type`, and
`password_change_required` for the token's user (401 without a valid token).

**Session hydration (#251).** The frontend never invents display strings. On
load it bootstraps from the stored user or, failing that, from JWT claims only
(`sub`, `user_id`, `role`, `cooperative_id`, `organization_id`,
`organization_type` — no name or cooperative), then replaces that with
`GET /auth/me`. A transport failure keeps the bootstrap session and the
dashboard shows its own error state; a reachable backend rejecting the token
clears the session.

When `AUTH_ENABLED=true`, every route except signup/login, health probes, and
the exact Moolre/USSDK callback paths requires `Authorization: Bearer <token>`.
Tokens contain `cooperative_id` and `role`; authenticated query/body scope is
always replaced by the token's cooperative.

`admin` can manage members, production, cooperative settings, finance, loans,
and communications. `finance_officer` can manage finance, loans, and
communications but receives `403` for admin-only resources.

Demo credentials (`admin@agroos.demo` / `demo1234`) exist only when the Golden
Path seed has run (see below). The backend refuses to start with
`AUTH_ENABLED=true` and the default `ADMIN_PASSWORD`, so they can never be live
in production.

## Error conventions

FastAPI returns `{ "detail": "message" }` for 4xx/5xx responses.

## Client data policy (no demo fallback)

The frontend has **no client-side demo data**. Every dashboard read helper in
`frontend/src/api/*.js` goes through `apiFetch` / `fetchJson` in
`frontend/src/api/config.js` and either returns live API data or throws:

- Transport failures (network errors, `FETCH_TIMEOUT_MS` timeouts) propagate as
  the original error; `formatTransportError` renders them as a retryable message.
- Non-OK responses from a reachable backend (`401`, `403`, `422`, 5xx) propagate
  as `ApiError` with the server's `detail`. A `401` also clears the stored token.

Nothing is substituted for a failed request, in any environment, so a screen
showing data is always showing what the API returned. Login likewise only
succeeds against `POST /auth/login`; there are no local demo accounts.

## Demo data in production

Demo machinery is gated server-side on `Settings.is_production`
(`APP_ENV` of `production`/`prod`, any casing):

| Surface | Behaviour outside production | Behaviour in production |
|---|---|---|
| Golden Path seed (`seed_golden_path`) | Runs on startup when `SEED_DEMO_DATA=true` | Never runs; `SEED_DEMO_DATA=true` fails startup validation |
| `GET /admin/demo-reset/preview`, `POST /admin/demo-reset/confirm` | Admin of the demo cooperative only, two-step confirmation | `404` |
| Settings "Reset demo data" panel | Shown to the demo cooperative admin | Hidden (backend returns `404`) |
| `backend/scripts/purge_demo_data.py` | Runs; `--dry-run` previews | Refuses (exit 2) unless `--allow-production`; `--dry-run` still allowed |
| Staff transaction status edits (`PATCH /transactions/{id}/status`) | Allowed outside production | `404` |
| Legacy staff-initiated loan create/repay fixtures | `APP_ENV=test` only | `403` (farmers act via USSD) |

## Golden Path seed data

When `SEED_DEMO_DATA=true` (development/staging only), `seed_golden_path()`
inserts on startup:

- Cooperative: **Kuapa Kokoo Demo Cooperative**
- Farmer: **Abena Mensah** (pending dues transaction for webhook demo)
- Supporting crop, animal, and mixed members plus production and attendance records

Seeding is also disabled automatically when running on Render.
