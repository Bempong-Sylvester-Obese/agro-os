# Backend

The backend will expose the AgroOS API, handle Moolre webhooks, and calculate farmer Trust Scores.

## Planned Stack

- Python 3.10+
- FastAPI
- Supabase PostgreSQL
- Ruff for linting

## Initial Responsibilities

- Farmer/member management endpoints.
- Finance endpoints for dues, transactions, loans, and payouts.
- Production tracking endpoints for crop and harvest records.
- Moolre webhook endpoint for payment confirmation events.
- Trust Score service using a transparent rules-based formula for the MVP.

## Moolre API Responsibilities

The backend owns all server-side communication with Moolre. Frontend code should call AgroOS endpoints rather than calling Moolre directly.

Relevant Moolre capabilities for the MVP:

- Payment collection for cooperative dues.
- Payment webhook handling for real-time reconciliation.
- Payment status checks for retry and support flows.
- Transaction listing for finance dashboards.
- Transfer or bulk disbursement for approved input loans and payouts.
- SMS sending for dues reminders and payment confirmations.
- USSD integration for feature-phone farmer interactions.

Moolre environments:

- Live: `https://api.moolre.com`
- Sandbox: `https://sandbox.moolre.com`

Sandbox notes from the Moolre quickstart:

- Sandbox requests use `X-API-USER`.
- `X-API-KEY` and `X-API-PUBKEY` are not required in sandbox, but should still be represented in configuration for production readiness.
- SMS and WhatsApp endpoints require `X-API-VASKEY`.

Primary reference: [Moolre API Documentation](https://docs.moolre.com/#/quickstart).

## Local Setup

Create a Python virtual environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Direct backend dependencies live in `backend/requirements.in`; `backend/requirements.txt` is the hash-locked output generated with `pip-compile`.

Run the API locally:

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## Agro-AI Endpoints

The hackathon `agro-ai` service scores cooperative farmers with a scikit-learn Random Forest model. It can load a local `joblib` artifact through `AGRO_AI_MODEL_PATH`; if no artifact exists locally, it falls back to deterministic synthetic training so the demo still runs.

- `GET /health`
- `GET /api/farmers`
- `GET /api/farmers/{farmer_id}/credit-assessment`
- `GET /api/agro-ai/credit-summary`
- `POST /api/agro-ai/predict`

`POST /api/agro-ai/predict` accepts optional `farmer_id`, `cooperative_id`, and `actor_id` fields. They are not required for the hackathon demo, but they are included in prediction audit logs so the auth/session work can attach tenant context later.

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

Expected environment variables should come from the root `.env.example`.
