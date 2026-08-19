# Adding a New Provider Adapter

AgroOS uses the ports-and-adapters pattern for payment and SMS providers.

## Provider Ports

| Port | Location | Methods |
|------|----------|---------|
| PaymentProvider | backend/app/services/providers/base.py | initiate_payment, payment_status, initiate_transfer, transfer_status, create_account, internal_transfer, generate_payment_link, account_status, list_transactions |
| SmsProvider | backend/app/services/providers/base.py | send_sms, send_bulk_sms, diagnose_sms |

## Current Adapter

Moolre is the sole adapter: `backend/app/services/providers/moolre_adapter.py`

## Adding a New Provider

1. Create a new adapter class implementing `PaymentProvider` and/or `SmsProvider`
2. Implement all abstract methods
3. Normalize provider-specific responses to the standard dict format:
   - `initiate_payment`: `{outcome: "push_sent"|"verification_required"|"failed", external_ref: str, ...}`
   - `initiate_transfer`: `{success: bool, external_ref: str, ...}`
4. Register the adapter in `backend/app/services/providers/factory.py`
5. Add provider-specific configuration to `.env.example` and `config.py`
6. Add webhook verification for the new provider's signature scheme in the route handler

## Provider-Neutral Field Names

All database columns use provider-neutral names:

| Column | Table | Purpose |
|--------|-------|---------|
| `provider_payment_ref` | transactions, payment_webhook_events | Provider's payment transaction reference |
| `provider_transfer_ref` | transactions, loans | Provider's transfer/disbursement reference |
| `wallet_account_id` | cooperatives | Provider wallet/account identifier |
| `provider_ref` | communication_logs | Provider message/SMS reference |

New providers should use these neutral column names for their references.

## Directory Structure

Provider-specific code is confined to:

```
backend/app/services/providers/
├── base.py              # Port interfaces (PaymentProvider, SmsProvider)
├── factory.py           # Factory functions (get_payment_provider, get_sms_provider)
├── moolre_adapter.py    # Moolre concrete adapter

backend/app/adapters/
├── moolre_ussd.py       # Moolre USSD gateway adapter
├── ussdk_adapter.py     # USSDK gateway adapter
├── at_adapter.py        # Africa's Talking gateway adapter
```

Domain code (`routes/`, `services/`, `domain/`) must never import directly from provider-specific modules — always use the port interface via the factory.
