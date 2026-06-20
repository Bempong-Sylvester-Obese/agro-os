# Backend

The AgroOS FastAPI backend exposes the AgroOS API, handles Moolre webhooks, calculates farmer Trust Scores, manages SMS communications, and processes loan lifecycles.

## Stack

- **Python 3.10+** (tested on 3.14)
- **FastAPI** — async REST API framework
- **SQLAlchemy 2.0** — ORM with lazy engine initialisation
- **Supabase PostgreSQL** — production database (SQLite for local dev)
- **Moolre** — payments, USSD, SMS, and bulk transfers
- **Ruff** — linting and formatting
- **pytest** — test suite (70 tests, 0 failures)

---

## API Endpoints

Interactive docs available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API root — version and environment info |
| GET | `/health` | Health check for deployment monitors |

### Cooperatives
| Method | Path | Description |
|--------|------|-------------|
| POST | `/cooperatives/` | Create a new cooperative |
| GET | `/cooperatives/` | List all cooperatives |
| GET | `/cooperatives/{id}` | Get cooperative by ID |
| PUT | `/cooperatives/{id}` | Update cooperative (partial) |
| DELETE | `/cooperatives/{id}` | Delete cooperative (only if no farmers) |

### Farmers
| Method | Path | Description |
|--------|------|-------------|
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
|--------|------|-------------|
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
|--------|------|-------------|
| POST | `/loans/` | Farmer requests an input/cash loan |
| GET | `/loans/` | List loans (filter by `farmer_id`, `status`) |
| GET | `/loans/{id}` | Get loan details |
| POST | `/loans/{id}/approve` | Approve a loan request |
| POST | `/loans/{id}/reject` | Reject a loan request |
| POST | `/loans/{id}/disburse` | Disburse approved loan via Moolre transfer |
| POST | `/loans/{id}/repay` | Record loan repayment + recalculate Trust Score |

### Production
| Method | Path | Description |
|--------|------|-------------|
| POST | `/production/` | Log a new crop/production cycle |
| GET | `/production/` | List production records (filter by `farmer_id`, `crop_type`) |
| GET | `/production/{id}` | Get a production record |
| PUT | `/production/{id}` | Update production record (log harvest data) |
| DELETE | `/production/{id}` | Delete a production record |
| GET | `/production/farmer/{farmer_id}` | All production records for a farmer |
| GET | `/production/farmer/{farmer_id}/summary` | Yield summary (total kg, completion rate) |

### Communications
| Method | Path | Description |
|--------|------|-------------|
| POST | `/communications/sms/broadcast` | Bulk SMS to all active cooperative members |
| POST | `/communications/sms/dues-reminder` | Send dues reminder SMS to all active members |
| GET | `/communications/logs` | List sent communication logs |

### Webhooks
| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhooks/moolre/payment` | Moolre payment confirmation webhook (HMAC verified) |
| POST | `/webhooks/moolre/ussd` | USSD session handler (5-option farmer menu) |

---

## Trust Score Formula

The AgroCredit Trust Score (0–100) is transparent and rules-based for the MVP:

| Factor | Weight | How it's measured |
|--------|--------|-------------------|
| Payment Compliance | 40% | % of dues transactions completed |
| Production History | 25% | Harvest completion rate + volume bonuses |
| Loan Repayment | 20% | % of disbursed loans repaid |
| Attendance | 15% | % of cooperative events attended (last 12 months) |

A webhook from Moolre automatically triggers a recalculation after every successful payment.

---

## Moolre Integration

The backend is the sole owner of all Moolre API calls — the frontend never calls Moolre directly.

| Capability | Moolre Endpoint | AgroOS Use |
|------------|-----------------|------------|
| USSD Payment Push | `POST /open/transact/payment` | Dues collection |
| Bulk Transfer | `POST /open/transact/transfer` | Loan disbursement & payouts |
| Payment/Transfer Status | `POST /open/transact/status` | Retry & support flows |
| List Transactions | `POST /open/account/status` (type=2) | Finance dashboard sync |
| Wallet Balance | `POST /open/account/status` (type=1) | Account overview |
| Send SMS | `POST /open/sms/send` | Dues reminders & confirmations |
| Payment Link | `POST /embed/link` | Hosted payment pages |
| Payment Webhook | `POST {callback_url}` | Real-time payment reconciliation |

Environments:
- **Sandbox**: `https://sandbox.moolre.com` — only `X-API-USER` required
- **Live**: `https://api.moolre.com` — full auth headers required

---

## Local Setup

### Prerequisites
- Python 3.10+
- PostgreSQL (Supabase) — or SQLite for local dev

### Installation

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL and MOOLRE_API_USER

# 4. Run the server
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000` with:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

> **Tip**: The default `.env.example` includes a SQLite URL (`sqlite:///./agro_os_dev.db`) so you can run locally without Supabase. Switch `DATABASE_URL` to your Supabase PostgreSQL connection string for production.

### Connecting to Supabase

In your `.env`:
```
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL or SQLite connection string |
| `MOOLRE_API_URL` | Moolre base URL (sandbox or live) |
| `MOOLRE_API_USER` | Your Moolre username |
| `MOOLRE_API_KEY` | Private API key (live only) |
| `MOOLRE_API_PUBKEY` | Public API key (live only) |
| `MOOLRE_API_VASKEY` | VAS key for SMS/WhatsApp |
| `MOOLRE_ACCOUNT_NUMBER` | Cooperative Moolre wallet number |
| `MOOLRE_MERCHANT_CODE` | USSD merchant code for dues payment |
| `MOOLRE_WEBHOOK_SECRET` | HMAC secret for webhook signature verification |
| `DEFAULT_CURRENCY` | Default currency (set to `GHS`) |
| `DEFAULT_SMS_SENDER_ID` | SMS sender ID (default: `AgroOS`) |

### Agro-AI (dashboard credit scoring)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/farmers` | List farmer credit assessments for the dashboard |
| GET | `/api/farmers/{farmer_id}/credit-assessment` | Get one farmer credit assessment |
| GET | `/api/agro-ai/credit-summary` | Aggregate credit summary for dashboard widgets |
| POST | `/api/agro-ai/predict` | Run an ad-hoc credit prediction from feature payload |

`POST /api/agro-ai/predict` accepts optional `farmer_id`, `cooperative_id`, and `actor_id` for audit logging.

---

## Local Setup

Create a Python virtual environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Direct backend dependencies live in `backend/requirements.in`; `backend/requirements.txt` is the hash-locked output generated with `pip-compile`.

Copy `backend/.env.example` to `backend/.env` for local development. SQLite is supported for local dev without Supabase.

Run the API locally:

```bash
npm run api
```

Or from `backend/`:

```bash
../.venv/bin/uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## Agro-AI Training And Evaluation

Train and evaluate the current synthetic-data model:

```bash
npm run train:ai -- --wandb-mode offline
```

This writes a local model artifact to `backend/model_artifacts/agro-ai-rf-v1.joblib` by default and logs W&B data in offline mode. Use online W&B after authenticating:

```bash
wandb login
npm run train:ai -- --wandb-mode online --wandb-project agro-os
```

The training command logs model parameters, dataset split metadata, classification metrics, credit-threshold metrics, confusion matrix, feature importances, and a model artifact. Synthetic evaluation validates the pipeline only; real credit performance requires repayment and default outcomes from Supabase/Moolre data.

---

## Development

```bash
# Lint
ruff check .

# Format
ruff format .

# Run all backend tests (domain routes + Agro-AI)
pytest tests/ -v
```

### Project Structure

```
backend/
├── app/
│   ├── routes/
│   │   ├── cooperatives.py   # Cooperative CRUD
│   │   ├── farmers.py        # Farmer CRUD + Trust Score + Attendance
│   │   ├── transactions.py   # Finance + Moolre dues collection
│   │   ├── loans.py          # Loan lifecycle (request→approve→disburse→repay)
│   │   ├── production.py     # Crop/harvest tracking
│   │   ├── communications.py # SMS broadcast & reminders
│   │   ├── webhooks.py       # Moolre payment webhook + USSD handler
│   │   └── agro_ai.py        # Dashboard Agro-AI credit scoring routes
│   ├── agro_ai/
│   │   ├── model.py          # Random Forest credit model
│   │   ├── runtime.py        # Model singleton + audit logger
│   │   ├── train.py          # Offline training + W&B logging CLI
│   │   └── evaluation.py     # Metrics and experiment helpers
│   ├── services/
│   │   ├── moolre_service.py          # All Moolre API calls
│   │   ├── trust_score_service.py     # AgroCredit scoring engine
│   │   └── communications_service.py  # SMS templates + logging
│   ├── models/
│   │   └── models.py         # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── schemas.py        # Pydantic request/response schemas
│   ├── database/
│   │   └── db.py             # Lazy engine + session management
│   └── config.py             # App settings (pydantic-settings)
├── tests/
│   ├── conftest.py            # In-memory SQLite fixtures
│   ├── test_cooperatives.py
│   ├── test_farmers.py
│   ├── test_transactions.py
│   ├── test_loans.py
│   ├── test_production.py
│   ├── test_webhooks.py
│   ├── test_trust_score.py
│   └── test_agro_ai.py
├── main.py                    # FastAPI app entry point
├── requirements.txt
├── pyproject.toml             # Ruff + pytest config
└── .env.example
```
