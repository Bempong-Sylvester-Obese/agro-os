# Backend

The AgroOS FastAPI backend exposes the AgroOS API, handles Moolre webhooks, calculates farmer Trust Scores, manages SMS communications, and processes loan lifecycles.

## Stack

- **Python 3.10+** (tested on 3.14)
- **FastAPI** — async REST API framework
- **SQLAlchemy 2.0** — ORM with lazy engine initialisation
- **Supabase PostgreSQL** — production and local database
- **Moolre** — payments, USSD, SMS, and bulk transfers
- **Ruff** — linting and formatting
- **pytest** — test suite (70 tests, 0 failures)

---

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for `npm run` scripts)
- A Supabase project **or** use the in-memory SQLite that the test suite spins up automatically

### Installation

```bash
# 1. From the repo root — install backend Python deps
npm run setup:backend

# 2. Copy the env file
cp backend/.env.example backend/.env
```

Then open `backend/.env` and fill in the required values. The minimum set to run the API locally:

```
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
MOOLRE_API_URL=https://sandbox.moolre.com
MOOLRE_API_USER=your_moolre_username
APP_ENV=development
DEBUG=true
```

See the [Environment Variables](#environment-variables) table below for all keys.

### Run the API

```bash
# From repo root:
npm run api

# Or from backend/ directly:
../.venv/bin/uvicorn main:app --reload
```

API available at `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

### Seed demo data

Populate the Golden Path demo characters (Kuapa Kokoo + Abena Mensah):

```bash
npm run seed:backend
```

See `supabase/README.md` for what gets seeded and how to run it against the demo deploy.

---

## Environment Variables

### App & Database

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | Supabase PostgreSQL connection string (see note below) |
| `APP_ENV` | ✅ | `development` or `production` |
| `DEBUG` | | `true` / `false` — enables uvicorn reload and verbose logging |
| `SECRET_KEY` | ✅ | Random secret for signing internal tokens |

> **DATABASE_URL** must be a PostgreSQL connection string for the running server.  
> The test suite (`npm run test:backend`) uses its own **in-memory SQLite** database spun up by `tests/conftest.py` — it does not read `DATABASE_URL` at all, so you can run tests without a Supabase project.

### Supabase

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | | Supabase project URL — used for client-side SDK calls if needed |
| `SUPABASE_SERVICE_ROLE_KEY` | | Service role key — full DB access, never expose to frontend |
| `SUPABASE_ANON_KEY` | | Anon/public key |

### Moolre

| Variable | Required | Description |
|---|---|---|
| `MOOLRE_ENV` | ✅ | `sandbox` or `live` |
| `MOOLRE_API_URL` | ✅ | `https://sandbox.moolre.com` or `https://api.moolre.com` |
| `MOOLRE_API_USER` | ✅ | Your Moolre username (`X-API-USER` header) |
| `MOOLRE_API_KEY` | Live only | Private API key (`X-API-KEY` header) — not required in sandbox |
| `MOOLRE_API_VASKEY` | Live only | VAS key for USSD and SMS services |
| `MOOLRE_ACCOUNT_NUMBER` | ✅ | Cooperative Moolre wallet number |
| `MOOLRE_MERCHANT_ID` | | Merchant ID for hosted payment links |
| `MOOLRE_MERCHANT_CODE` | | Short code farmers dial for USSD (e.g. `*713*1#`) |
| `MOOLRE_WEBHOOK_SECRET` | ✅ | HMAC secret for webhook signature verification |

For sandbox setup, local webhook tunnelling, and live credential promotion see [`docs/moolre-setup.md`](../docs/moolre-setup.md).

> **Security note:** `MOOLRE_WEBHOOK_SECRET` is required in production. If it is unset, the payment webhook logs a warning and skips signature verification (dev-only fallback). The USSD webhook has no signature verification at all today. See [`../SECURITY.md`](../SECURITY.md) for details.

### Cooperative Defaults

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_CURRENCY` | `GHS` | Currency used across transactions and loans |
| `DEFAULT_SMS_SENDER_ID` | `AgroOS` | Sender name shown on outgoing SMS |

### Agro-AI

| Variable | Default | Description |
|---|---|---|
| `AGRO_AI_MODEL_PATH` | `backend/model_artifacts/agro-ai-rf-v1.joblib` | Path to the trained Random Forest model artifact. If the file is absent, the runtime falls back to the rules-based Trust Score formula. |
| `AGRO_AI_AUDIT_LOG_PATH` | `backend/logs/agro_ai_audit.jsonl` | Append-only JSONL file that records every prediction request for audit. |
| `WANDB_PROJECT` | `agro-os` | Weights & Biases project name — used during training only |
| `WANDB_ENTITY` | | W&B team or username — leave blank to use personal workspace |
| `WANDB_MODE` | `offline` | `offline` writes runs locally; `online` streams to wandb.ai after `wandb login` |

---

## Running Tests

```bash
# From repo root (correct — uses pythonpath = backend):
npm run test:backend

# Do NOT run bare pytest from the repo root:
# pytest tests/   ← wrong, import paths will break
```

The `npm run test:backend` script sets `PYTHONPATH=backend` before invoking pytest, which is required for `from app.x import y` imports to resolve. The test suite uses an in-memory SQLite database created per-session in `tests/conftest.py` — no `DATABASE_URL` or Supabase connection needed.

---

## Agro-AI Training and Evaluation

Train and evaluate the Random Forest credit model:

```bash
# Offline (no W&B account needed):
npm run train:ai -- --wandb-mode offline

# Online (requires wandb login):
wandb login
npm run train:ai -- --wandb-mode online --wandb-project agro-os
```

This writes a model artifact to the path set in `AGRO_AI_MODEL_PATH` (default: `backend/model_artifacts/agro-ai-rf-v1.joblib`) and logs parameters, dataset split metadata, classification metrics, credit-threshold metrics, confusion matrix, feature importances, and a model artifact to W&B.

> Synthetic evaluation validates the pipeline only. Real credit performance requires repayment and default outcomes from live Supabase/Moolre data.

---

## Development

```bash
# Lint
ruff check .

# Format
ruff format .

# Tests
npm run test:backend
```

---

## Security

All routes below are currently **unauthenticated**. See
[`../SECURITY.md`](../SECURITY.md) for secrets handling, webhook signature
verification status (payment vs. USSD), dependency policy, and how to
report a vulnerability.

---

## API Endpoints

Interactive docs at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

### Health
| Method | Path | Description |
|---|---|---|
| GET | `/` | API root — version and environment info |
| GET | `/health` | Health check for deployment monitors |

### Cooperatives
| Method | Path | Description |
|---|---|---|
| POST | `/cooperatives/` | Create a new cooperative |
| GET | `/cooperatives/` | List all cooperatives |
| GET | `/cooperatives/{id}` | Get cooperative by ID |
| PUT | `/cooperatives/{id}` | Update cooperative (partial) |
| DELETE | `/cooperatives/{id}` | Delete cooperative (only if no farmers) |

### Farmers
| Method | Path | Description |
|---|---|---|
| POST | `/farmers/` | Register a new farmer |
| GET | `/farmers/` | List farmers (filter by `cooperative_id`, `membership_status`) |
| GET | `/farmers/{id}` | Get farmer profile |
| PUT | `/farmers/{id}` | Update farmer profile (partial) |
| DELETE | `/farmers/{id}` | Soft-deactivate a farmer |
| GET | `/farmers/{id}/trust-score` | Get latest trust score breakdown |
| GET | `/farmers/{id}/trust-score/history` | Get trust score history (trend) |
| POST | `/farmers/{id}/recalculate-trust-score` | Trigger manual trust score recalculation |
| POST | `/farmers/{id}/attendance` | Record cooperative event attendance |
| GET | `/farmers/{id}/attendance` | List farmer attendance records |

### Transactions
| Method | Path | Description |
|---|---|---|
| POST | `/transactions/` | Create a manual transaction record |
| GET | `/transactions/` | List transactions (filter by `farmer_id`, `status`, `transaction_type`) |
| GET | `/transactions/{id}` | Get transaction by ID |
| PATCH | `/transactions/{id}/status` | Update transaction status |
| GET | `/transactions/farmer/{farmer_id}` | Get all transactions for a farmer |
| POST | `/transactions/dues/collect` | Initiate dues collection via Moolre USSD push |
| GET | `/transactions/moolre/account-transactions` | Sync transactions from Moolre wallet |
| GET | `/transactions/moolre/wallet-balance` | Check cooperative Moolre wallet balance |

### Loans
| Method | Path | Description |
|---|---|---|
| POST | `/loans/` | Farmer requests an input/cash loan |
| GET | `/loans/` | List loans (filter by `farmer_id`, `status`) |
| GET | `/loans/{id}` | Get loan details |
| POST | `/loans/{id}/approve` | Approve a loan request |
| POST | `/loans/{id}/reject` | Reject a loan request |
| POST | `/loans/{id}/disburse` | Disburse approved loan via Moolre transfer |
| POST | `/loans/{id}/repay` | Record loan repayment + recalculate Trust Score |

### Production
| Method | Path | Description |
|---|---|---|
| POST | `/production/` | Log a new crop/production cycle |
| GET | `/production/` | List production records (filter by `farmer_id`, `crop_type`) |
| GET | `/production/{id}` | Get a production record |
| PUT | `/production/{id}` | Update production record (log harvest data) |
| DELETE | `/production/{id}` | Delete a production record |
| GET | `/production/farmer/{farmer_id}` | All production records for a farmer |
| GET | `/production/farmer/{farmer_id}/summary` | Yield summary (total kg, completion rate) |

### Communications
| Method | Path | Description |
|---|---|---|
| POST | `/communications/sms/broadcast` | Bulk SMS to all active cooperative members |
| POST | `/communications/sms/dues-reminder` | Send dues reminder SMS to all active members |
| GET | `/communications/logs` | List sent communication logs |

### Webhooks
| Method | Path | Description |
|---|---|---|
| POST | `/webhooks/moolre/payment` | Moolre payment confirmation webhook (HMAC verified) |
| POST | `/webhooks/moolre/ussd` | USSD session handler (5-option farmer menu) |

### Agro-AI
| Method | Path | Description |
|---|---|---|
| GET | `/api/farmers` | List farmer credit assessments for the dashboard |
| GET | `/api/farmers/{farmer_id}/credit-assessment` | Get one farmer credit assessment |
| GET | `/api/agro-ai/credit-summary` | Aggregate credit summary for dashboard widgets |
| POST | `/api/agro-ai/predict` | Run an ad-hoc credit prediction from feature payload |

`POST /api/agro-ai/predict` accepts optional `farmer_id`, `cooperative_id`, and `actor_id` for audit logging.

---

## Trust Score Formula

The AgroCredit Trust Score (0–100) is transparent and rules-based for the MVP:

| Factor | Weight | How it's measured |
|---|---|---|
| Payment Compliance | 40% | % of dues transactions completed |
| Production History | 25% | Harvest completion rate + volume bonuses |
| Loan Repayment | 20% | % of disbursed loans repaid |
| Attendance | 15% | % of cooperative events attended (last 12 months) |

A Moolre webhook automatically triggers a recalculation after every successful payment.

---

## Moolre Integration

The backend is the sole owner of all Moolre API calls — the frontend never calls Moolre directly.

Full setup reference: [`docs/moolre-setup.md`](../docs/moolre-setup.md)

| Capability | Moolre Endpoint | AgroOS Use |
|---|---|---|
| USSD Payment Push | `POST /open/transact/payment` | Dues collection |
| Bulk Transfer | `POST /open/transact/transfer` | Loan disbursement & payouts |
| Payment/Transfer Status | `POST /open/transact/status` | Retry & support flows |
| List Transactions | `POST /open/account/status` (type=2) | Finance dashboard sync |
| Wallet Balance | `POST /open/account/status` (type=1) | Account overview |
| Send SMS | `POST /open/sms/send` | Dues reminders & confirmations |
| Payment Link | `POST /embed/link` | Hosted payment pages |
| Payment Webhook | `POST {callback_url}` | Real-time payment reconciliation |

---

## Project Structure

```
backend/
├── app/
│   ├── routes/
│   │   ├── cooperatives.py
│   │   ├── farmers.py
│   │   ├── transactions.py
│   │   ├── loans.py
│   │   ├── production.py
│   │   ├── communications.py
│   │   ├── webhooks.py
│   │   └── agro_ai.py
│   ├── agro_ai/
│   │   ├── model.py
│   │   ├── runtime.py
│   │   ├── train.py
│   │   └── evaluation.py
│   ├── services/
│   │   ├── moolre_service.py
│   │   ├── trust_score_service.py
│   │   └── communications_service.py
│   ├── models/
│   │   └── models.py
│   ├── schemas/
│   │   └── schemas.py
│   ├── database/
│   │   └── db.py
│   └── config.py
├── tests/
│   ├── conftest.py
│   ├── test_cooperatives.py
│   ├── test_farmers.py
│   ├── test_transactions.py
│   ├── test_loans.py
│   ├── test_production.py
│   ├── test_webhooks.py
│   ├── test_trust_score.py
│   └── test_agro_ai.py
├── main.py
├── requirements.in
├── requirements.txt
├── pyproject.toml
└── .env.example
```
