# Supabase

This directory contains the AgroOS database schema reference, migrations, and seed documentation aligned with the SQLAlchemy models in `backend/app/models/models.py`.

## Migration strategy

| Approach | Status | Notes |
|----------|--------|-------|
| Alembic versioned migrations | **Active** | Authoritative schema; deploy with `alembic upgrade head` |
| SQLAlchemy `create_all()` | Tests/local bootstrap only | Does not replace versioned production migrations |
| `supabase/migrations/*.sql` | **Reference only** | Mirrors ORM/Alembic for review; do not apply directly |

Run local seed via backend startup (`APP_ENV=development`) or set `SEED_DEMO_DATA=true`. See [docs/api-contract.md](../docs/api-contract.md) for Golden Path characters.

## Access and RLS boundary

Browser clients must use the FastAPI API. AgroOS access tokens are custom
FastAPI JWTs and are not Supabase Auth JWTs, so direct SQL/API access using the
Supabase `authenticated` role is unsupported.

The M5 policies in `008_m5_rls_policies.sql` intentionally grant access only to
`service_role`; browser roles fail closed. These reference policies are not
installed by Alembic and do not protect an owner/superuser backend connection,
because PostgreSQL owners and superusers can bypass RLS. Current tenant
isolation is enforced by authenticated FastAPI cooperative-scope checks and
requires `AUTH_ENABLED=true` in production.

Enforcing database RLS in a future deployment requires a restricted
non-superuser runtime role and a transaction-scoped cooperative value (for
example, `SET LOCAL app.current_cooperative_id`) that policies can evaluate.

## Table mapping

| Planned / README name | Current ORM model | Status |
|-----------------------|-------------------|--------|
| `cooperatives` | `Cooperative` | Implemented |
| `farmers` | `Farmer` | Implemented |
| `farmer_profiles` | fields on `Farmer` | Merged into `Farmer` |
| `dues_payments` | `Transaction` (`transaction_type=dues`) | Merged |
| `transactions` | `Transaction` | Implemented |
| `loans` | `Loan` | Implemented |
| `loan_disbursements` | fields on `Loan` | Merged (`disbursed_at`, `moolre_transfer_ref`) |
| `disbursement_batches` | — | Not started |
| `harvests` | `Production` | Implemented as `productions` |
| `trust_scores` | `TrustScore` | Implemented (history snapshots) |
| `sms_messages` | `CommunicationLog` | Implemented |
| `announcements` | — | Not started |
| `ussd_sessions` | `UssdSession` | Implemented |
| `payment_webhook_events` | `PaymentWebhookEvent` | Implemented |
| `agro_ai_prediction_logs` | `AgroAiPredictionLog` | Implemented |
| `cooperative_attendances` | `CooperativeAttendance` | Implemented |

## Moolre metadata preserved

The `Transaction` model stores:

- `moolre_reference`, `moolre_transfer_ref`
- `payer_phone`, `payee_phone`, `channel`
- `amount`, `currency`, `status`

`PaymentWebhookEvent` stores raw webhook payloads for audit. `UssdSession` stores session id, phone, menu path, and response text.

## Files

- `migrations/001_initial.sql` — core tables aligned with SQLAlchemy
- `config.toml` — Supabase CLI scaffold

## Related issues

- Golden Path seed data: GitHub #12
- API contract: [docs/api-contract.md](../docs/api-contract.md)
