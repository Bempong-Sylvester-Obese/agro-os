# AgroOS Architecture

> Provider-neutral cooperative management platform for Ghanaian agricultural cooperatives.

---

## High-Level Overview

AgroOS is a monorepo containing three main subsystems:

| Subsystem | Path | Stack |
|---|---|---|
| Frontend | `frontend/` | Vite + React |
| Backend API | `backend/` | Python / FastAPI |
| Database | `supabase/` | PostgreSQL (Supabase) |

```
┌─────────────────────────────────────────────────┐
│               Frontend (Vite + React)            │
│         Cooperative admin dashboard              │
└────────────────────┬────────────────────────────┘
                     │ REST API (JSON)
┌────────────────────▼────────────────────────────┐
│              FastAPI Backend                     │
│                                                 │
│  Routes ──► Services ──► Domain ──► Provider    │
│                                  Port Interfaces │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │         Provider Adapter Layer           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │   │
│  │  │ Payment  │ │   SMS    │ │   USSD   │ │   │
│  │  │ Adapter  │ │ Adapter  │ │ Adapters │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ │   │
│  └──────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│          PostgreSQL (Supabase)                   │
│  Alembic migrations + reference RLS policies    │
└─────────────────────────────────────────────────┘
```

---

## Backend Structure

```
backend/
├── main.py                      # FastAPI app, lifespan, CORS, router mounts
├── app/
│   ├── config.py                # Pydantic Settings (env-driven)
│   ├── constants.py
│   ├── adapters/                # Gateway adapters (USSD translation)
│   │   ├── moolre_ussd.py       # Moolre USSD gateway → UssdRequest
│   │   ├── ussdk_adapter.py     # USSDK gateway → UssdRequest
│   │   └── at_adapter.py        # Africa's Talking gateway → UssdRequest
│   ├── domain/                  # Domain objects (provider-agnostic)
│   │   └── payment_event.py     # PaymentEvent dataclass
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── routes/                  # FastAPI route modules
│   │   ├── webhooks.py          # Payment & USSD webhooks
│   │   ├── ussdk_hooks.py       # USSDK-specific hooks
│   │   ├── ussd.py              # Africa's Talking USSD
│   │   └── ...                  # Domain routes (farmers, loans, etc.)
│   ├── services/                # Business logic
│   │   ├── providers/           # Payment/SMS provider ports & adapters
│   │   │   ├── base.py          # PaymentProvider, SmsProvider ABCs
│   │   │   ├── factory.py       # get_payment_provider(), get_sms_provider()
│   │   │   └── moolre_adapter.py # Moolre concrete adapter
│   │   ├── moolre_service.py    # Moolre-specific HTTP client (provider internal)
│   │   ├── payment_service.py   # Domain payment logic
│   │   ├── payment_normalization.py
│   │   ├── ussd_application.py  # Provider-neutral USSD state machine
│   │   ├── subscription_service.py
│   │   ├── dues_service.py
│   │   ├── loan_workflow.py
│   │   └── ...                  # Other domain services
│   ├── dependencies/            # FastAPI dependency injection
│   │   └── cooperative_scope.py # Tenant isolation helpers
│   ├── middleware/
│   │   └── rate_limit.py        # Config-driven rate limiting
│   └── agro_ai/                 # Scikit-learn Trust Score model
├── alembic/                     # Database migrations
├── tests/                       # Backend test suite
└── scripts/                     # Utility scripts
```

---

## Ports & Adapters Pattern

AgroOS uses the **Hexagonal (Ports & Adapters)** architecture for external provider integrations. Domain code depends only on abstract ports; concrete adapters handle provider-specific translation.

### Provider Ports

Defined in `backend/app/services/providers/base.py`:

| Port | Interface | Purpose |
|---|---|---|
| `PaymentProvider` | `initiate_payment`, `initiate_transfer`, `payment_status`, `transfer_status`, `create_account`, `internal_transfer`, `generate_payment_link`, `account_status`, `list_transactions` | All payment operations |
| `SmsProvider` | `send_sms`, `send_bulk_sms`, `diagnose_sms` | SMS delivery |

### Provider Factory

Defined in `backend/app/services/providers/factory.py`:

```python
def get_payment_provider() -> PaymentProvider:
    """Returns the configured PaymentProvider singleton."""

def get_sms_provider() -> SmsProvider:
    """Returns the configured SmsProvider singleton."""
```

All consumers depend on the factory, never on concrete adapter classes. To swap providers, change only the factory return values.

### Current Adapter

Moolre is the sole concrete adapter:
- `backend/app/services/providers/moolre_adapter.py` — implements `PaymentProvider` and `SmsProvider`
- `backend/app/services/moolre_service.py` — HTTP client for Moolre API (provider-internal, not domain code)

See `docs/architecture/adding-a-provider.md` for the step-by-step guide to adding a new provider adapter.

---

## Payment Webhook Flow

Payment webhooks arrive as provider-specific JSON payloads and are normalized into domain objects before business logic runs.

```
Provider HTTP POST
       │
       ▼
webhooks.py (route handler)
       │
       ├─ Validate signature (provider-specific header)
       ├─ Parse provider-specific payload
       │
       ▼
PaymentEvent (domain object)
  .provider = "moolre"
  .event_type = "payment.success" | "payment.failed"
  .external_ref = provider transaction reference
  .amount, .currency, .status
       │
       ▼
payment_service.process_payment_event()
       │
       ├─ Look up Transaction by provider_payment_ref
       ├─ Update transaction status
       ├─ Trigger Trust Score recalculation
       └─ Run background tasks (SMS, notifications)
```

### PaymentEvent Domain Object

Defined in `backend/app/domain/payment_event.py`:

```python
@dataclass
class PaymentEvent:
    provider: str        # "moolre"
    event_type: str      # "payment.success", "payment.failed"
    external_ref: str    # provider's transaction reference
    amount: float | None
    currency: str        # "GHS"
    status: str          # "success", "failed", "pending"
    payer_phone: str | None
    metadata: dict[str, Any]
```

---

## USSD Architecture

AgroOS supports three USSD gateways, all unified behind a single application service.

```
Moolre USSD ──► moolre_ussd.py ──┐
USSDK        ──► ussdk_adapter.py ─┼──► UssdApplicationService.handle()
AT (AT USSD) ──► at_adapter.py ──┘          │
                                            ▼
                                   Domain Services
                                   (dues, loans, subscriptions, etc.)
```

### Components

| Component | Path | Role |
|---|---|---|
| `UssdRequest` / `UssdResponse` | `backend/app/services/ussd_application.py` | Provider-neutral request/response dataclasses |
| `UssdApplicationService` | `backend/app/services/ussd_application.py` | Menu state machine — shared across all gateways |
| `moolre_ussd.py` | `backend/app/adapters/moolre_ussd.py` | Translates Moolre JSON → UssdRequest |
| `ussdk_adapter.py` | `backend/app/adapters/ussdk_adapter.py` | Translates USSDK format → UssdRequest |
| `at_adapter.py` | `backend/app/adapters/at_adapter.py` | Translates AT form-encoded → UssdRequest |

Each adapter is a thin translation layer (~30 lines). The `UssdApplicationService` holds the entire menu state machine (pay dues, request loan, repay loan, check balance, announcements, OTP handling). Adding a new gateway requires only a new adapter — the application service is unchanged.

---

## Database Schema Overview

Key tables (PostgreSQL via Supabase):

| Table | Purpose |
|---|---|
| `cooperatives` | Cooperative entities; `wallet_account_id` = provider wallet reference |
| `farmers` | Member records linked to cooperatives |
| `transactions` | Payment records; `provider_payment_ref` = provider transaction ID |
| `loans` | Loan records; `provider_transfer_ref` = disbursement reference |
| `productions` | Production tracking (crop/animal/mixed) |
| `trust_scores` | AgroCredit AI scoring results |
| `communication_logs` | SMS delivery records; `provider_ref` = provider message ID |
| `payment_webhook_events` | Raw webhook event log; `provider_payment_ref` |
| `pending_checkouts` | Pre-checkout payment sessions |
| `subscriptions` | Cooperative subscription/plan records |

### Provider-Neutral Column Names

After the column rename migration (#242), all provider-specific database columns use neutral names:

| Old Name | New Name | Table |
|---|---|---|
| `moolre_account_number` | `wallet_account_id` | `cooperatives` |
| `moolre_reference` | `provider_payment_ref` | `transactions`, `payment_webhook_events` |
| `moolre_transfer_ref` | `provider_transfer_ref` | `transactions`, `loans` |
| `moolre_ref` | `provider_ref` | `communication_logs` |

---

## Tenant Isolation Model

AgroOS enforces tenant isolation at the API layer:

1. JWT contains `cooperative_id` — validated on every request
2. Route handlers filter all queries by cooperative scope
3. `require_cooperative_scope()` fails closed (403) if scope cannot be resolved
4. DB connection uses service-role (bypasses RLS) — defense-in-depth only

Reference RLS policies exist in `supabase/migrations/009_tenant_rls_policies.sql` for future enforcement.

---

## Forbidden Patterns

The following patterns are not allowed in domain code (`backend/app/routes/`, `backend/app/services/`, `backend/app/domain/`):

| Pattern | Why |
|---|---|
| `from app.services.moolre_service import ...` | Moolre-specific HTTP client belongs in the adapter layer |
| `from app.services.providers.moolre_adapter import ...` | Domain code must use the port interface via the factory |
| `from app.routes import <other_route>` | Route-to-route imports create circular dependencies |
| `moolre_reference`, `moolre_transfer_ref`, `moolre_account_number` | Use provider-neutral column names |

Provider-specific code is confined to:
- `backend/app/services/providers/moolre_adapter.py`
- `backend/app/services/moolre_service.py`
- `backend/app/adapters/moolre_ussd.py`

---

## Adding a New Provider

See [`docs/architecture/adding-a-provider.md`](architecture/adding-a-provider.md) for the detailed step-by-step guide. Summary:

1. Create adapter class implementing `PaymentProvider` and/or `SmsProvider`
2. Implement all abstract methods, normalizing responses to the standard dict format
3. Register the adapter in `backend/app/services/providers/factory.py`
4. Add provider-specific configuration to `.env.example` and `config.py`
5. Add webhook verification for the new provider's signature scheme
