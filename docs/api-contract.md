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
  "crop_type": "Maize",
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
| Wallet balance | GET | `/transactions/moolre/wallet-balance` | Moolre wallet object |
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

### USSD & webhooks

| UI | Method | Path |
|----|--------|------|
| USSD log | GET | `/webhooks/ussd/logs` |
| USSD handler (Moolre) | POST | `/webhooks/moolre/ussd` |
| Payment webhook (Moolre) | POST | `/webhooks/moolre/payment` |
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

### Authentication and cooperative roles

| UI | Method | Path |
|----|--------|------|
| Login | POST | `/auth/login` |
| Signup | POST | `/auth/signup` |
| Add cooperative user | POST | `/auth/register` |

When `AUTH_ENABLED=true`, every route except signup/login, health probes, and
the exact Moolre/USSDK callback paths requires `Authorization: Bearer <token>`.
Tokens contain `cooperative_id` and `role`; authenticated query/body scope is
always replaced by the token's cooperative.

`admin` can manage members, production, cooperative settings, finance, loans,
and communications. `finance_officer` can manage finance, loans, and
communications but receives `403` for admin-only resources.

Default demo credentials: `admin@agroos.demo` / `demo1234`.

## Error conventions

FastAPI returns `{ "detail": "message" }` for 4xx/5xx responses.

## Demo fallback policy

The frontend **always prefers live API data** when the backend is reachable, but **never fails closed** on transport outages — including in production.

Dashboard read helpers (`frontend/src/api/*.js`, shared config in `frontend/src/api/config.js`) use a 10s timeout via `withDemoFallback`. **Only transport-level failures** (network errors, timeouts) return static demo data from `frontend/src/data/payments.js` and set `source: 'demo'`. HTTP responses from a reachable backend — including `401`, `403`, validation `422`, and other 4xx/5xx — are surfaced to callers as `ApiError` and are **not** replaced with demo data.

The dashboard topbar and per-tab badges show **Live API** vs **Demo data** so operators know which source is active.

Login is separate: the login page tries `POST /auth/login` first, then falls back to local demo accounts in `frontend/src/data/users.js` when auth is unavailable at the transport layer.

There is no `VITE_REQUIRE_API` or production-only strict mode — transport outages should degrade gracefully to demo data, not blank screens or blocking errors.

## Golden Path seed data

On backend startup in development, `seed_golden_path()` inserts:

- Cooperative: **Kuapa Kokoo Demo Cooperative**
- Farmer: **Abena Mensah** (pending dues transaction for webhook demo)
- Supporting farmers, loans, production, and attendance records

Set `SEED_DEMO_DATA=true` to force seeding in other environments.
