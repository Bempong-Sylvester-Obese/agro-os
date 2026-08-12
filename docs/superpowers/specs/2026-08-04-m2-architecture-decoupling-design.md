# M2 — Architecture Decoupling Design

**Date:** 2026-08-04
**Milestone:** M2

---

## Design Decisions

### #224 — PaymentProvider & SmsProvider Ports
Create `backend/app/services/providers/base.py` with abstract base classes:
- `PaymentProvider`: `initiate_payment()`, `payment_status()`, `initiate_transfer()`, `create_account()`, `internal_transfer()`
- `SmsProvider`: `send_sms()`, `send_bulk_sms()`

`MoolreService` implements both via adapter in `backend/app/services/providers/moolre_adapter.py` (thin wrapper, delegates to existing MoolreService).

### #225 — PaymentEvent Normalization
Create `backend/app/domain/payment_event.py` dataclass with: `provider`, `event_type`, `external_ref`, `amount`, `currency`, `status`, `metadata`. Webhook handler transforms Moolre payload → PaymentEvent → domain processing.

### #226 — Domain Services Extraction
- Move payment processing from `webhooks.py` into `backend/app/services/payment_service.py`
- Move loan processing into `backend/app/services/loan_service.py`
- Stop route-to-route imports (routes import from services, not from other routes)

### #227 — Unify USSD Gateways
Create `backend/app/services/ussd_service.py` with shared menu logic used by:
- `routes/ussd.py` (Africa's Talking format)
- `routes/webhooks.py` (Moolre USSD format)
- `routes/ussdk_hooks.py` (USSDK format)

### #228 — Config-Driven URLs
Replace hardcoded webhook URLs with `AGROOS_BASE_URL` env var. Read from config.

### #229 — Deduplicate Router
Check `main.py` for duplicate router includes and merge.

### #242 — Neutral DB Columns
Document provider-agnostic fields vs Moolre-specific fields. No rename (breaking), just documentation.

### #243 — Provider Adapter Docs
Write `docs/adding-a-provider.md` explaining how to add a new payment/SMS provider.
