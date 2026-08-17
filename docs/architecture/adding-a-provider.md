# Adding a New Provider Adapter

AgroOS uses the ports-and-adapters pattern for payment and SMS providers.

## Provider Ports

| Port | Location | Methods |
|------|----------|---------|
| PaymentProvider | backend/app/services/providers/base.py | initiate_payment, payment_status, initiate_transfer, create_account, internal_transfer |
| SmsProvider | backend/app/services/providers/base.py | send_sms, send_bulk_sms |

## Current Adapter

Moolre is the sole adapter: backend/app/services/providers/moolre_adapter.py

## Adding a New Provider

1. Create a new adapter class implementing PaymentProvider and/or SmsProvider
2. Implement all abstract methods
3. Normalize provider-specific responses to the standard dict format:
   - initiate_payment: {outcome: "push_sent"|"verification_required"|"failed", external_ref: str, ...}
   - initiate_transfer: {success: bool, moolre_transfer_ref: str, ...}
4. Register the adapter in a factory/service resolver
5. Add provider-specific configuration to .env.example and config.py

## Provider-Neutral vs Provider-Specific Fields

- provider_reference: generic external reference (DB column)
- moolre_reference: Moolre-specific reference (DB column, legacy)
- New providers should use provider_reference for their references
