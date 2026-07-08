# Supabase

This directory contains the AgroOS database schema reference, migrations, and seed documentation aligned with the SQLAlchemy models in `backend/app/models/models.py`.

## Migration strategy (hackathon MVP)

| Approach | Status | Notes |
|----------|--------|-------|
| SQLAlchemy `create_all()` on FastAPI startup | **Active** | Creates/updates tables automatically |
| `supabase/migrations/*.sql` | **Reference** | Mirrors ORM for review and future Supabase CLI use |
| Alembic versioned migrations | Planned | Recommended before production |

Run local seed via backend startup (`APP_ENV=development`) or set `SEED_DEMO_DATA=true`. See [docs/api-contract.md](../docs/api-contract.md) for Golden Path characters.

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
