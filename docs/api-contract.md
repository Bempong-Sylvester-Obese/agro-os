# Frontend–Backend API Contract

Base URL: `VITE_API_URL` (default `http://localhost:8000`). CORS allows all origins in development and the Vercel frontend URL in production.

Interactive OpenAPI docs: `{VITE_API_URL}/docs`

## ID schemes

| Surface | ID format | Example |
|---------|-----------|---------|
| CRM farmers (`/farmers/*`) | Integer DB primary key | `1` |
| Agro-AI assessments (`/api/farmers`) | Member code string | `GH-0001` |
| Frontend display | Padded member code | `GH-0001` |

When the database is seeded, Agro-AI assessments are built from DB farmer records and use `GH-{db_id}` codes. When the DB is empty, Agro-AI falls back to synthetic demo farmers (`GH-0103`, etc.).

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
| Payment link | POST | `/transactions/payment-link` | `PaymentLinkResponse` |
| Collect dues | POST | `/transactions/dues/collect` | `DuesCollectResponse` |

**TransactionResponse** statuses: `pending`, `completed`, `failed`. Channel `13` = MoMo.

### Loans, Production, SMS

| UI | Method | Path |
|----|--------|------|
| Loans tab | GET/POST | `/loans/` |
| Production tab | GET | `/production/` |
| SMS tab | GET/POST | `/communications/logs`, `/communications/sms/broadcast` |

### USSD & webhooks

| UI | Method | Path |
|----|--------|------|
| USSD log | GET | `/webhooks/ussd/logs` |
| USSD handler (Moolre) | POST | `/webhooks/moolre/ussd` |
| Payment webhook (Moolre) | POST | `/webhooks/moolre/payment` |
| Demo simulate payment | POST | `/webhooks/moolre/payment/simulate` |

Simulate endpoint is disabled when `APP_ENV=production`.

### Cooperative profile

| UI | Method | Path |
|----|--------|------|
| Settings sidebar | GET | `/cooperatives/` or `/cooperatives/{id}` |

Optional env: `VITE_COOPERATIVE_ID`.

### Authentication (optional)

| UI | Method | Path |
|----|--------|------|
| Login | POST | `/auth/login` |

When `AUTH_ENABLED=true`, mutating routes require `Authorization: Bearer <token>`. Webhooks and login remain public.

Default demo credentials: `admin@agroos.demo` / `demo1234`.

## Error conventions

FastAPI returns `{ "detail": "message" }` for 4xx/5xx responses.

## Demo fallback policy

Frontend API helpers (`frontend/src/api/*.js`) use a 10s timeout. On network failure or non-2xx responses they return static demo data from `frontend/src/data/payments.js` and set `source: 'demo'`. The dashboard topbar shows **Live API** vs **Demo data** based on aggregated fetch results.

Payments and Overview tabs show an inline banner when demo fallback is active.

## Golden Path seed data

On backend startup in development, `seed_golden_path()` inserts:

- Cooperative: **Kuapa Kokoo Demo Cooperative**
- Farmer: **Abena Mensah** (pending dues transaction for webhook demo)
- Supporting farmers, loans, production, and attendance records

Set `SEED_DEMO_DATA=true` to force seeding in other environments.
