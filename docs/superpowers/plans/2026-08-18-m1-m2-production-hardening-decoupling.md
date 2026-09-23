# M1 Production Hardening + M2 Architecture Decoupling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all open issues in M1 (Production Hardening) and M2 (Architecture Decoupling) milestones.

**Architecture:** M1 locks down production safety (demo gating, API-only tenancy docs, docs rewrite). M2 decouples the backend from Moolre-specific coupling via column renames, PaymentEvent wiring, domain service extraction, and USSD gateway unification. Strict dependency order for M2: #229 → #228 → #242 → #225 → #226 → #227 → #243.

**Tech Stack:** Python/FastAPI, SQLAlchemy/Alembic, React/Vite, PostgreSQL

## Global Constraints

- All changes on branch `feat/m1-m2-close-milestones` (branched from `dev`)
- Run `npm run test:backend` after each task to verify nothing breaks
- No new external dependencies unless absolutely necessary
- Follow existing code style (no comments unless asked)
- Commit after each task with descriptive message

---

## Task 1: M2 #229 — Deduplicate subscriptions router + remove patch file

**Files:**
- Modify: `backend/main.py` (line 213)
- Delete: `ussdk-payment-flow.patch`

**Interfaces:**
- Produces: single `include_router(subscriptions.router)` in main.py

- [ ] **Step 1: Check for duplicate router registration**

Run: `rg "include_router(subscriptions" backend/main.py`
Expected: Should find exactly 1 occurrence. If 2, one is duplicate.

- [ ] **Step 2: Verify app boots with current code**

Run: `cd backend; python -c "from main import app; print('OK')"`
Expected: OK

- [ ] **Step 3: Delete the orphan patch file**

Run: `rm ussdk-payment-flow.patch` (if it exists at repo root)

- [ ] **Step 4: Verify app still boots**

Run: `cd backend; python -c "from main import app; print('OK')"`
Expected: OK

- [ ] **Step 5: Run backend tests**

Run: `npm run test:backend`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: deduplicate subscriptions router and remove orphan patch file (#229)"
```

---

## Task 2: M2 #228 — Remove hardcoded webhook URL + Moolre-named paths

**Files:**
- Modify: `backend/app/config.py` (add `webhook_callback_path`)
- Modify: `backend/app/services/moolre_service.py` (~line 670)
- Modify: `backend/app/middleware/rate_limit.py` (~line 64)
- Modify: `backend/main.py` (~line 143, app description)

**Interfaces:**
- Consumes: `settings.webhook_callback_path` (new config field)
- Produces: configurable webhook URL, provider-neutral rate limit paths

- [ ] **Step 1: Add `webhook_callback_path` to config**

In `backend/app/config.py`, add after `agroos_base_url` (line 50):

```python
    webhook_callback_path: str = "/webhooks/payment"
```

- [ ] **Step 2: Update moolre_service.py to use configurable path**

In `backend/app/services/moolre_service.py`, find the `create_account` method where the callback URL is built (around line 670). Replace the hardcoded path:

```python
# BEFORE:
callback_url = f"{settings.agroos_base_url}/webhooks/moolre/payment"

# AFTER:
callback_url = f"{settings.agroos_base_url}{settings.webhook_callback_path}"
```

- [ ] **Step 3: Update rate_limit.py to use config constants**

In `backend/app/middleware/rate_limit.py`, replace the hardcoded webhook paths (line 64):

```python
# BEFORE:
if path in {"/webhooks/moolre/payment", "/webhooks/moolre/ussd"} or path.startswith(
    "/ussdk/"
):

# AFTER:
 webhook_paths = {settings.webhook_callback_path, "/webhooks/moolre/payment", "/webhooks/moolre/ussd"}
    if path in webhook_paths or path.startswith("/ussdk/"):
```

- [ ] **Step 4: Update app description in main.py**

In `backend/main.py`, find `app.description` (around line 143) and remove "Powered by Moolre" if present. Replace with a provider-neutral description.

- [ ] **Step 5: Add webhook_callback_path to .env.example**

In `backend/.env.example`, add:

```
WEBHOOK_CALLBACK_PATH=/webhooks/payment
```

- [ ] **Step 6: Verify app boots**

Run: `cd backend; python -c "from main import app; print('OK')"`

- [ ] **Step 7: Run backend tests**

Run: `npm run test:backend`

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py backend/app/services/moolre_service.py backend/app/middleware/rate_limit.py backend/main.py backend/.env.example
git commit -m "chore: remove hardcoded webhook URL and use configurable callback path (#228)"
```

---

## Task 3: M2 #242 — Rename moolre_* columns to provider-neutral names (Alembic migration)

**Files:**
- Create: `backend/alembic/versions/<auto_generated>_rename_moolre_columns.py`
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/schemas/schemas.py`

**Interfaces:**
- Produces: renamed columns (`provider_payment_ref`, `provider_transfer_ref`, `wallet_account_id`, `provider_ref`)
- All subsequent tasks depend on these new names

- [ ] **Step 1: Generate Alembic migration**

Run: `cd backend; alembic revision --autogenerate -m "rename moolre columns to provider-neutral"`
Expected: Creates a new migration file in `alembic/versions/`

- [ ] **Step 2: Edit the generated migration**

Open the generated migration file. Replace the auto-generated content with explicit renames:

```python
"""rename moolre columns to provider-neutral

Revision ID: <auto>
Revises: <auto>
Create Date: <auto>
"""
from alembic import op
import sqlalchemy as sa

revision = "<auto>"
down_revision = "<auto>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # cooperatives: moolre_account_number -> wallet_account_id
    op.alter_column("cooperatives", "moolre_account_number", new_column_name="wallet_account_id")

    # transactions: moolre_reference -> provider_payment_ref
    op.alter_column("transactions", "moolre_reference", new_column_name="provider_payment_ref")

    # transactions: moolre_transfer_ref -> provider_transfer_ref
    op.alter_column("transactions", "moolre_transfer_ref", new_column_name="provider_transfer_ref")

    # loans: moolre_transfer_ref -> provider_transfer_ref
    op.alter_column("loans", "moolre_transfer_ref", new_column_name="provider_transfer_ref")

    # communication_logs: moolre_ref -> provider_ref
    op.alter_column("communication_logs", "moolre_ref", new_column_name="provider_ref")

    # payment_webhook_events: moolre_reference -> provider_payment_ref
    op.alter_column("payment_webhook_events", "moolre_reference", new_column_name="provider_payment_ref")


def downgrade() -> None:
    op.alter_column("payment_webhook_events", "provider_payment_ref", new_column_name="moolre_reference")
    op.alter_column("communication_logs", "provider_ref", new_column_name="moolre_ref")
    op.alter_column("loans", "provider_transfer_ref", new_column_name="moolre_transfer_ref")
    op.alter_column("transactions", "provider_transfer_ref", new_column_name="moolre_transfer_ref")
    op.alter_column("transactions", "provider_payment_ref", new_column_name="moolre_reference")
    op.alter_column("cooperatives", "wallet_account_id", new_column_name="moolre_account_number")
```

- [ ] **Step 3: Update models.py column names**

In `backend/app/models/models.py`, rename the 6 columns:

```python
# In Cooperative model:
wallet_account_id = Column(String, nullable=True)  # was moolre_account_number

# In Transaction model:
provider_payment_ref = Column(String, unique=True, nullable=True)  # was moolre_reference
provider_transfer_ref = Column(String, unique=True, nullable=True)  # was moolre_transfer_ref

# In Loan model:
provider_transfer_ref = Column(String, nullable=True)  # was moolre_transfer_ref

# In CommunicationLog model:
provider_ref = Column(String, nullable=True)  # was moolre_ref

# In PaymentWebhookEvent model:
provider_payment_ref = Column(String, nullable=True)  # was moolre_reference
```

- [ ] **Step 4: Update schemas.py field names**

In `backend/app/schemas/schemas.py`, rename all moolre_* fields:

```python
# CooperativeBase / CooperativeUpdate:
wallet_account_id: Optional[str] = None  # was moolre_account_number

# TransactionResponse:
provider_payment_ref: Optional[str] = None  # was moolre_reference
provider_transfer_ref: Optional[str] = None  # was moolre_transfer_ref

# LoanResponse:
provider_transfer_ref: Optional[str] = None  # was moolre_transfer_ref

# CommunicationLogResponse:
provider_ref: Optional[str] = None  # was moolre_ref

# PaymentWebhookEventResponse:
provider_payment_ref: Optional[str] = None  # was moolre_reference

# DuesCollectResponse:
provider_payment_ref: Optional[str] = None  # was moolre_reference
provider_code: Optional[str] = None  # was moolre_code

# PaymentInitiateResponse:
provider_payment_ref: Optional[str] = None  # was moolre_reference

# TransferInitiateResponse:
provider_transfer_ref: Optional[str] = None  # was moolre_transfer_ref
```

- [ ] **Step 5: Grep for remaining moolre_reference/moolre_transfer_ref in backend**

Run: `rg "moolre_reference|moolre_transfer_ref|moolre_account_number|moolre_ref[^e]" backend/app/ --include "*.py" -l`
Expected: Should return NO matches in models/schemas. May still appear in `moolre_service.py` (that's internal Moolre API, not our DB).

- [ ] **Step 6: Update all remaining backend references**

For each file found in Step 5 (excluding `moolre_service.py` and `providers/moolre_adapter.py`), update the column references to the new names. Key files likely include:
- `backend/app/routes/webhooks.py` — `Transaction.moolre_reference` → `Transaction.provider_payment_ref`
- `backend/app/routes/transactions.py`
- `backend/app/routes/loans.py`
- `backend/app/services/payment_service.py` — `Transaction.moolre_reference` → `Transaction.provider_payment_ref`
- `backend/app/routes/admin.py` — if it references moolre columns

- [ ] **Step 7: Verify app boots**

Run: `cd backend; python -c "from main import app; print('OK')"`

- [ ] **Step 8: Run backend tests**

Run: `npm run test:backend`
Expected: All tests pass. If any fail, update the test fixtures to use new column names.

- [ ] **Step 9: Commit**

```bash
git add backend/alembic/versions/ backend/app/models/ backend/app/schemas/ backend/app/routes/ backend/app/services/
git commit -m "refactor: rename moolre_* columns to provider-neutral names (#242)"
```

---

## Task 4: M2 #242 (frontend) — Rename moolre_* in frontend code + CSS

**Files:**
- Modify: `frontend/src/components/dashboard/Settings.jsx`
- Modify: `frontend/src/components/dashboard/Loans.jsx`
- Modify: `frontend/src/components/dashboard/Payments.jsx`
- Modify: `frontend/src/components/dashboard/Payroll.jsx`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/pages/HomePage.jsx`
- Modify: `frontend/src/components/Footer.jsx`

**Interfaces:**
- Consumes: new API response field names from Task 3

- [ ] **Step 1: Update Settings.jsx**

Find `moolre_account_number` references and rename to `wallet_account_id`. Update the label from "Moolre Account Number" to "Wallet Account ID".

- [ ] **Step 2: Update Loans.jsx**

Find `loan.moolre_transfer_ref` and rename to `loan.provider_transfer_ref`. Find `request_channel === 'moolre_ussd'` and rename to `'farmer_ussd'`.

- [ ] **Step 3: Update Payments.jsx**

Find `request_channel` mapping of `'moolre_ussd'` → `'Farmer USSD'` and update the value to `'farmer_ussd'`.

- [ ] **Step 4: Update Payroll.jsx**

Find `p.moolre_reference` and rename to `p.provider_payment_ref`.

- [ ] **Step 5: Rename CSS classes in global.css**

Find all `.moolre-*` CSS classes and rename to `.integration-*`:
- `.moolre-band` → `.integration-band`
- `.moolre-inner` → `.integration-inner`
- `.moolre-tag` → `.integration-tag`
- `.moolre-h2` → `.integration-h2`
- `.moolre-desc` → `.integration-desc`
- `.moolre-cards-wrap` → `.integration-cards-wrap`
- `.moolre-cards-heading` → `.integration-cards-heading`
- `.moolre-cards-sub` → `.integration-cards-sub`
- `.moolre-cards` → `.integration-cards`
- `.moolre-card` → `.integration-card`
- `.moolre-card-icon` → `.integration-card-icon`
- `.moolre-card-title` → `.integration-card-title`
- `.moolre-card-desc` → `.integration-card-desc`
- `.moolre-card-link` → `.integration-card-link`

Also update all responsive `@media` rules that reference these class names.

- [ ] **Step 6: Update HomePage.jsx**

Find `className="moolre-band"` and rename to `className="integration-band"`. Update marketing copy: "Built on Moolre. Native from day one." → "Built for cooperatives. Native from day one." Update the section title "Moolre integration" → "Platform integration". Update anchor ID `#moolre-integration` → `#platform-integration`.

- [ ] **Step 7: Update Footer.jsx**

Find links pointing to `/#moolre-integration` and update to `/#platform-integration`.

- [ ] **Step 8: Verify frontend builds**

Run: `cd frontend; npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 9: Run frontend tests**

Run: `cd frontend; npm test`
Expected: All tests pass. Update any test fixtures referencing moolre_* field names.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/
git commit -m "refactor: rename moolre references in frontend to provider-neutral names (#242)"
```

---

## Task 5: M2 #225 — Wire PaymentEvent normalization into webhook flow

**Files:**
- Modify: `backend/app/routes/webhooks.py` (lines 84-429)
- Modify: `backend/app/services/payment_service.py`

**Interfaces:**
- Consumes: `PaymentEvent` from `app.domain.payment_event`, new column names from Task 3
- Produces: `_process_payment_payload` delegates to `process_payment_event()` for regular transactions

- [ ] **Step 1: Update _normalize_payload to use new column names**

In `backend/app/routes/webhooks.py`, update `_normalize_payload` (line 84). The function already creates a `PaymentEvent` — no structural change needed, just verify it works with the Moolre payload shape.

- [ ] **Step 2: Refactor _process_payment_payload for regular transactions**

Replace the inline transaction processing (lines 305-429) with a call to `process_payment_event()`. Keep the subscription handling (lines 174-303) inline for now — it's subscription-specific, not generic payment processing.

The key change: after looking up the transaction by `provider_payment_ref` (new column name), instead of inline status updates, create a `PaymentEvent` and delegate to `process_payment_event()`.

```python
# In _process_payment_payload, replace lines 305-429 with:
from app.services.payment_service import process_payment_event

# ... (existing transaction lookup by provider_payment_ref) ...

event = PaymentEvent(
    provider="moolre",
    event_type=f"payment.{'success' if moolre_status == 1 else 'failed'}",
    external_ref=external_ref or str(transaction_id),
    amount=amount,
    currency="GHS",
    status="success" if moolre_status == 1 else "failed",
    payer_phone=None,
    metadata={"payload": payload, "signature_valid": signature_valid},
)
result = process_payment_event(event, db)

# Still record the webhook event and run background tasks
if result["status"] == "processed":
    _record_webhook_event(db, payload=payload, signature_valid=signature_valid,
                          transaction=tx, processed=True, message="Payment confirmed")
    background_tasks.add_task(_post_payment_tasks, farmer_id=tx.farmer_id,
                              amount=amount, reference=external_ref or str(transaction_id))
```

- [ ] **Step 3: Update payment_service.py to use new column names**

In `backend/app/services/payment_service.py`, line 36, change:

```python
# BEFORE:
.filter(Transaction.moolre_reference == event.external_ref)

# AFTER:
.filter(Transaction.provider_payment_ref == event.external_ref)
```

- [ ] **Step 4: Verify _record_webhook_event uses new column names**

In `webhooks.py` line 142, ensure `PaymentWebhookEvent` uses `provider_payment_ref` instead of `moolre_reference`.

- [ ] **Step 5: Verify app boots**

Run: `cd backend; python -c "from main import app; print('OK')"`

- [ ] **Step 6: Run backend tests**

Run: `npm run test:backend`

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/webhooks.py backend/app/services/payment_service.py
git commit -m "refactor: wire PaymentEvent normalization into webhook payment flow (#225)"
```

---

## Task 6: M2 #226 — Extract domain services from route modules

**Files:**
- Modify: `backend/app/services/dues_service.py` (expand)
- Modify: `backend/app/services/loan_workflow.py` (expand)
- Create: `backend/app/services/subscription_service.py`
- Modify: `backend/app/routes/webhooks.py` (remove extracted logic)
- Modify: `backend/app/routes/ussdk_hooks.py` (use services instead of inline logic)

**Interfaces:**
- Consumes: PaymentEvent, new column names
- Produces: callable domain services for dues, loans, subscriptions

- [ ] **Step 1: Create subscription_service.py**

Create `backend/app/services/subscription_service.py` with the pre-checkout and upgrade logic currently inline in `webhooks.py` (lines 174-303):

```python
"""Subscription domain service — handles pre-checkout and upgrade activation."""
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import Cooperative, PaymentWebhookEvent, PendingCheckout
from app.services.plans import PLANS, activate_subscription, get_plan, resolve_amount

logger = logging.getLogger(__name__)


def process_pre_checkout(db: Session, *, external_ref: str, amount: float, status_code: int) -> dict:
    """Handle pre-checkout payment confirmation."""
    if status_code != 1:
        return {"status": "ok", "message": "Pre-checkout webhook processed"}
    checkout = (
        db.query(PendingCheckout)
        .filter(PendingCheckout.reference == external_ref)
        .with_for_update()
        .first()
    )
    if checkout and abs(float(checkout.amount) - amount) >= 0.01:
        logger.warning("Pre-checkout amount mismatch for %s", checkout.reference)
        return {"status": "ok", "message": "amount mismatch — acknowledged"}
    if checkout and checkout.status == "pending":
        checkout.status = "paid"
        db.commit()
        logger.info("Pending checkout %s marked paid", checkout.reference)
    return {"status": "ok", "message": "Pre-checkout webhook processed"}


def process_subscription_upgrade(
    db: Session, *, external_ref: str, amount: float, status_code: int, signature_valid: bool, payload: dict
) -> dict:
    """Handle subscription upgrade payment confirmation."""
    if status_code != 1:
        return {"status": "ok", "message": "Subscription webhook processed"}
    try:
        # ... (parse external_ref, validate amount, activate subscription)
        # Moved from webhooks.py lines 197-303
        pass  # TODO: paste the actual logic here
    except (TypeError, ValueError, IndexError) as exc:
        db.rollback()
        logger.warning("Rejected subscription webhook: %s", exc)
        return {"status": "ok", "message": "Invalid subscription reference"}
    except Exception as exc:
        db.rollback()
        logger.error("Failed to process subscription webhook: %s", exc)
    return {"status": "ok", "message": "Subscription webhook processed"}
```

- [ ] **Step 2: Update webhooks.py to use subscription_service**

Replace the inline subscription logic (lines 174-303) with calls to `subscription_service.process_pre_checkout()` and `subscription_service.process_subscription_upgrade()`.

- [ ] **Step 3: Verify dues_service.py and loan_workflow.py are usable from USSD**

Check that `backend/app/services/dues_service.py::run_dues_collect` and `backend/app/services/loan_workflow.py` have clean interfaces that don't require route-specific imports. If they import from route modules, refactor the imports.

- [ ] **Step 4: Verify no route-to-route imports exist**

Run: `rg "from app.routes" backend/app/routes/ --include "*.py" -l`
Expected: No matches. If any exist, refactor the imported function into a service.

- [ ] **Step 5: Verify app boots**

Run: `cd backend; python -c "from main import app; print('OK')"`

- [ ] **Step 6: Run backend tests**

Run: `npm run test:backend`

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/ backend/app/routes/
git commit -m "refactor: extract subscription/dues/loan domain services from routes (#226)"
```

---

## Task 7: M2 #227 — Unify three USSD gateways behind one application service

**Files:**
- Create: `backend/app/services/ussd_application.py`
- Create: `backend/app/adapters/__init__.py`
- Create: `backend/app/adapters/moolre_ussd.py`
- Create: `backend/app/adapters/ussdk_adapter.py`
- Create: `backend/app/adapters/at_adapter.py`
- Modify: `backend/app/routes/webhooks.py` (extract 700-line USSD block)
- Modify: `backend/app/routes/ussdk_hooks.py` (thin adapter)
- Modify: `backend/app/routes/ussd.py` (thin adapter)

**Interfaces:**
- Consumes: domain services from Task 6
- Produces: `UssdApplicationService` with provider-neutral request/response

- [ ] **Step 1: Create USSD domain models**

Create `backend/app/services/ussd_application.py` with:

```python
"""USSD application service — provider-neutral menu state machine."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UssdRequest:
    session_id: str
    phone_number: str
    input_text: str
    is_new_session: bool
    cooperative_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UssdResponse:
    text: str
    continue_session: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class UssdApplicationService:
    """Provider-neutral USSD menu state machine + finance orchestration."""

    def handle(self, request: UssdRequest, db) -> UssdResponse:
        """Main entry point — routes to menu handlers based on session state."""
        # TODO: Move the state machine from webhooks.py lines 541-1244 here
        # The menu logic is shared across all gateways
        pass
```

- [ ] **Step 2: Move USSD state machine from webhooks.py**

Extract the entire USSD handler block from `webhooks.py` (lines 541-1244) into `UssdApplicationService.handle()`. This is the largest single refactor — the 700-line state machine moves from being a route handler to being a service method.

Key changes:
- Replace `request.json()` parsing with `UssdRequest` fields
- Replace `JSONResponse(...)` returns with `UssdResponse` objects
- Replace direct DB session access with `db` parameter
- Keep all menu logic (pay dues, request loan, repay loan, check balance, announcements, OTP handling) intact

- [ ] **Step 3: Create Moolre USSD adapter**

Create `backend/app/adapters/moolre_ussd.py`:

```python
"""Moolre USSD gateway adapter — translates Moolre JSON to UssdRequest/UssdResponse."""
from fastapi import Request, JSONResponse
from app.services.ussd_application import UssdApplicationService, UssdRequest, UssdResponse

ussd_app = UssdApplicationService()


async def handle_moolre_ussd(request: Request, db) -> JSONResponse:
    body = await request.json()
    req = UssdRequest(
        session_id=body.get("sessionId", ""),
        phone_number=body.get("msisdn", ""),
        input_text=body.get("text", ""),
        is_new_session=body.get("new", False),
        metadata={"gateway": "moolre"},
    )
    response = ussd_app.handle(req, db)
    return JSONResponse({
        "sessionId": req.session_id,
        "response": response.text,
    })
```

- [ ] **Step 4: Create USSDK adapter**

Create `backend/app/adapters/ussdk_adapter.py` with the same pattern, translating USSDK's hook format.

- [ ] **Step 5: Create Africa's Talking adapter**

Create `backend/app/adapters/at_adapter.py` with the same pattern, translating AT's form-encoded format.

- [ ] **Step 6: Slim down webhooks.py**

Replace the 700-line USSD block in `webhooks.py` with a call to the Moolre adapter:

```python
from app.adapters.moolre_ussd import handle_moolre_ussd

@router.post("/moolre/ussd")
async def moolre_ussd_webhook(request: Request, db: Session = Depends(get_db)):
    return await handle_moolre_ussd(request, db)
```

The route file should drop from ~1244 lines to ~500 lines.

- [ ] **Step 7: Slim down ussdk_hooks.py**

Replace the duplicated menu logic in `ussdk_hooks.py` with calls to the USSDK adapter. Each endpoint becomes ~10 lines.

- [ ] **Step 8: Slim down ussd.py**

Replace the duplicated menu logic in `ussd.py` with calls to the AT adapter.

- [ ] **Step 9: Verify all three gateways still work**

Run: `cd backend; python -c "from main import app; print('OK')"`

- [ ] **Step 10: Run backend tests**

Run: `npm run test:backend`

- [ ] **Step 11: Commit**

```bash
git add backend/app/services/ussd_application.py backend/app/adapters/ backend/app/routes/webhooks.py backend/app/routes/ussdk_hooks.py backend/app/routes/ussd.py
git commit -m "refactor: unify three USSD gateways behind UssdApplicationService (#227)"
```

---

## Task 8: M1 #223 — Gate demo seed/reset in production (frontend)

**Files:**
- Modify: `frontend/src/components/dashboard/Settings.jsx`
- Modify: `frontend/src/api/config.js`
- Modify: `frontend/src/api/plans.js`

**Interfaces:**
- Consumes: `import.meta.env.PROD`

- [ ] **Step 1: Hide demo reset section in production in Settings.jsx**

Wrap the "Demo data danger zone" section with a production check:

```jsx
{!import.meta.env.PROD && (
  <div className="danger-zone">
    {/* existing demo reset UI */}
  </div>
)}
```

- [ ] **Step 2: Remove dead withDemoFallback from config.js**

In `frontend/src/api/config.js`, remove the `withDemoFallback` function export and the `LIVE_API_ONLY` constant if they are unused. Keep `isTransportFailure` as it's used by `plans.js`.

- [ ] **Step 3: Remove PLANS_FALLBACK from plans.js**

In `frontend/src/api/plans.js`, remove the `PLANS_FALLBACK` array and the fallback logic. If the API call fails, let the error propagate (the UI already handles errors).

- [ ] **Step 4: Verify frontend builds**

Run: `cd frontend; npm run build`

- [ ] **Step 5: Run frontend tests**

Run: `cd frontend; npm test`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "chore: gate demo seed/reset in production and remove dead fallback code (#223)"
```

---

## Task 9: M1 #240 — API-only tenancy lockdown

**Files:**
- Modify: `backend/app/dependencies/cooperative_scope.py`
- Modify: `SECURITY.md`
- Modify: `COMPLIANCE.md`

**Interfaces:**
- Produces: `require_cooperative_scope()` fail-closed helper

- [ ] **Step 1: Add require_cooperative_scope to cooperative_scope.py**

Add a new function that raises 403 if no cooperative can be resolved:

```python
def require_cooperative_scope(
    *,
    current_user: User | None,
    cooperative_id: int | None,
    settings: Settings,
) -> int:
    """Return cooperative ID or raise 403 — fail-closed variant."""
    if current_user and current_user.cooperative_id:
        return current_user.cooperative_id
    if cooperative_id is not None:
        return cooperative_id
    raise HTTPException(status_code=403, detail="Cooperative scope required")
```

- [ ] **Step 2: Update SECURITY.md tenancy section**

Add/更新 the tenancy section in SECURITY.md to document:
- API-layer isolation is the primary defense
- JWT contains `cooperative_id`, validated on every request
- Route handlers must filter queries by cooperative scope
- DB connection uses service-role (bypasses RLS) — defense-in-depth only
- Threat model: "If a route handler omits cooperative filtering, cross-tenant data could leak"
- RLS reference SQL retained in `supabase/migrations/009_tenant_rls_policies.sql` for future enforcement

- [ ] **Step 3: Update COMPLIANCE.md tenancy section**

Remove hackathon-scope caveats. Document that API-only tenancy is the enforced model.

- [ ] **Step 4: Verify app boots**

Run: `cd backend; python -c "from main import app; print('OK')"`

- [ ] **Step 5: Run backend tests**

Run: `npm run test:backend`

- [ ] **Step 6: Commit**

```bash
git add backend/app/dependencies/cooperative_scope.py SECURITY.md COMPLIANCE.md
git commit -m "docs: lock down API-only tenancy model and add fail-closed scope helper (#240)"
```

---

## Task 10: M1 #241 + M2 #243 — Rewrite docs and document architecture

**Files:**
- Modify: `README.md`
- Modify: `SECURITY.md` (additional updates beyond Task 9)
- Modify: `COMPLIANCE.md` (additional updates beyond Task 9)
- Modify: `CONTRIBUTING.md`
- Create: `docs/architecture.md`

**Interfaces:**
- Consumes: all refactoring from Tasks 1-9

- [ ] **Step 1: Rewrite README.md**

Remove hackathon MVP framing. Rewrite as:
- B2B cooperative platform for Ghanaian agricultural cooperatives
- Solo-farm tier pointer (M5)
- Production setup instructions (env vars, database, migrations)
- Architecture overview linking to `docs/architecture.md`
- Development setup (local, with demo mode)

- [ ] **Step 2: Finalize SECURITY.md**

Ensure all sections reflect current state after Tasks 8-9:
- Auth model (JWT, optional)
- Webhook verification (Moolre HMAC, USSDK, AT)
- Rate limiting (config-driven paths)
- Tenancy model (API-only, documented)
- Demo gating (production-blocked)
- Open gaps with issue links

- [ ] **Step 3: Finalize COMPLIANCE.md**

Remove all draft/hackathon caveats. Align with:
- Current auth model
- API-only tenancy
- Provider-neutral architecture
- Data protection (Act 843), payment services (Act 987), AML (Act 1044)

- [ ] **Step 4: Create docs/architecture.md**

Document:
- **Ports & Adapters pattern**: `PaymentProvider`, `SmsProvider` abstract ports, Moolre adapters
- **Provider coupling boundaries**: Where Moolre-specific code lives vs domain code
- **Webhook normalization**: Raw payload → PaymentEvent → domain service
- **USSD architecture**: UssdApplicationService + thin gateway adapters
- **Forbidden patterns**: "Do not import `moolre_*` in domain code", "New providers implement the port interface"
- **Adding a new provider**: Step-by-step guide

- [ ] **Step 5: Update CONTRIBUTING.md**

Add architecture constraints section:
- "Do not import moolre_* in domain code"
- "New providers implement the PaymentProvider/SmsProvider port interface"
- "Route handlers must not import from other route modules"
- Link to `docs/architecture.md`

- [ ] **Step 6: Final verification — grep for remaining moolre references in non-provider code**

Run: `rg "moolre" backend/app/routes/ backend/app/services/ --include "*.py" -l | grep -v moolre_service | grep -v providers/moolre`
Expected: No matches (or only comments referencing the migration)

- [ ] **Step 7: Verify app boots**

Run: `cd backend; python -c "from main import app; print('OK')"`

- [ ] **Step 8: Run full test suite**

Run: `npm run test:backend`
Run: `cd frontend; npm test`

- [ ] **Step 9: Commit**

```bash
git add README.md SECURITY.md COMPLIANCE.md CONTRIBUTING.md docs/architecture.md
git commit -m "docs: rewrite README/SECURITY/COMPLIANCE and document architecture boundaries (#241, #243)"
```

---

## Final Verification

- [ ] **Step 1: Run full backend test suite**
Run: `npm run test:backend`

- [ ] **Step 2: Run full frontend test suite**
Run: `cd frontend; npm test`

- [ ] **Step 3: Verify frontend builds**
Run: `cd frontend; npm run build`

- [ ] **Step 4: Verify no moolre references in domain code**
Run: `rg "moolre_reference|moolre_transfer_ref|moolre_account_number" backend/app/routes/ backend/app/services/ backend/app/models/ backend/app/schemas/ --include "*.py" -l | grep -v moolre_service | grep -v providers/moolre`
Expected: No matches

- [ ] **Step 5: Verify app boots**
Run: `cd backend; python -c "from main import app; print('OK')"`
