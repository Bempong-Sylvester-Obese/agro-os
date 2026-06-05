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

## Local Setup Placeholder

Implementation-specific setup commands will be added when the FastAPI app is created.

Expected environment variables should come from the root `.env.example`.
