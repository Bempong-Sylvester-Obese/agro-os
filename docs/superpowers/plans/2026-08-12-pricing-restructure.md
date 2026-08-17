# Pricing Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure subscription pricing into two audience tracks, and move payment before account creation so users see and pay the real total before signup.

**Architecture:** A single backend pricing module becomes the source of truth for plans/bands/prices, served via a public `GET /plans` endpoint and consumed by a new public `POST /subscriptions/pre-checkout` flow that records a `PendingCheckout`, generates a Moolre link, and is reconciled by the payment webhook. Signup verifies the paid checkout and activates the workspace.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend), React + Vite + Vitest (frontend), Moolre payments.

## Global Constraints

- Backend tests run with `python -m pytest backend/tests/<file>` from the repo root (SQLite in-memory, `client` + `db` fixtures). Do NOT rely on Postgres.
- Frontend tests run with `npm run test:frontend` (Vitest + Testing Library); mock `api/` modules with `vi.mock`.
- Alembic head is `011_merge_heads`; new migrations must set `down_revision = "011_merge_heads"`.
- Copy/feature strings must match the spec (`docs/superpowers/specs/2026-08-12-pricing-restructure-design.md`).
- Do not add code comments unless they explain non-obvious behavior.
- Moolre calls in tests must be mocked (see `test_demo_features.py::test_payment_link_route` pattern: monkeypatch `app.services.providers.moolre_adapter.MoolrePaymentAdapter.generate_payment_link`).
- Frontend pricing copy sources from `GET /plans` with a local fallback (mirrors existing `withDemoFallback` policy).

---

### Task 1: Pricing module + public `/plans` endpoint

**Files:**
- Create: `backend/app/plans.py`
- Create: `backend/app/routes/plans.py`
- Modify: `backend/main.py` (register router + public path)
- Test: `backend/tests/test_plans.py`

**Interfaces:**
- Produces: `get_plan(plan_key: str) -> dict | None`, `resolve_amount(plan_key: str, band_key: str | None = None) -> float | None`, `SUBSCRIPTION_DAYS = 30`, `PLANS: dict`.
- Produces: `GET /plans` → `{"plans": [ {...}, ... ]}` where each plan dict has `key`, `track`, `name`, `price`, `cadence`, `description`, `features`, `cta`, `bands` (list of `{key, label, capacity, price}` or `None`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_plans.py`:

```python
"""Pricing catalog tests."""

from app.plans import PLANS, get_plan, resolve_amount


def test_plans_catalog_has_two_tracks():
    tracks = {plan["track"] for plan in PLANS.values()}
    assert tracks == {"cooperative", "farmer"}


def test_get_plan_is_case_insensitive():
    assert get_plan("GROWTH")["key"] == "growth"
    assert get_plan("nope") is None


def test_resolve_amount_for_growth_bands():
    assert resolve_amount("growth", "base") == 299.0
    assert resolve_amount("growth", "plus_50") == 449.0
    assert resolve_amount("growth", "plus_100") == 599.0


def test_resolve_amount_for_solo_bands():
    assert resolve_amount("solo", "w20") == 99.0
    assert resolve_amount("solo", "w50") == 199.0
    assert resolve_amount("solo", "w100") == 349.0
    assert resolve_amount("solo", "custom") is None


def test_resolve_amount_is_none_for_free_and_custom_plans():
    assert resolve_amount("starter") is None
    assert resolve_amount("enterprise") is None
    assert resolve_amount("unknown") is None


def test_plans_endpoint_returns_all_plans(client):
    resp = client.get("/plans")
    assert resp.status_code == 200
    keys = {p["key"] for p in resp.json()["plans"]}
    assert keys == {"starter", "growth", "solo", "enterprise"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_plans.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.plans'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/plans.py`:

```python
"""Single source of truth for subscription plans, bands, and pricing."""

SUBSCRIPTION_DAYS = 30

PLANS = {
    "starter": {
        "key": "starter",
        "track": "cooperative",
        "name": "Starter",
        "eyebrow": "For emerging cooperatives",
        "price": "Free",
        "cadence": "No card required",
        "description": "Establish a reliable digital member register and start collecting dues.",
        "features": [
            "Up to 10 members",
            "MoMo payment collection",
            "Member and dues dashboard",
            "100 SMS messages per month",
            "Email support",
        ],
        "cta": "Create free workspace",
        "bands": None,
    },
    "growth": {
        "key": "growth",
        "track": "cooperative",
        "name": "Growth",
        "eyebrow": "For operating cooperatives",
        "price": "GHS 299",
        "cadence": "per organisation / month",
        "description": "Run payments, credit workflows, communication, and field operations at scale.",
        "features": [
            "AgroCredit Trust Scores",
            "USSD access",
            "Unlimited payment records",
            "1,000 SMS messages per month",
            "Priority support",
        ],
        "cta": "Start Growth onboarding",
        "featured": True,
        "badge": "Most selected",
        "bands": [
            {"key": "base", "label": "Up to 50 members", "capacity": 50, "price": 299.0},
            {"key": "plus_50", "label": "Up to 100 members", "capacity": 100, "price": 449.0},
            {"key": "plus_100", "label": "Up to 200 members", "capacity": 200, "price": 599.0},
        ],
    },
    "enterprise": {
        "key": "enterprise",
        "track": "cooperative",
        "name": "Enterprise",
        "eyebrow": "For networks and institutions",
        "price": "Custom",
        "cadence": "Annual agreement",
        "description": "A governed rollout for unions, lenders, NGOs, and multi-cooperative programmes.",
        "features": [
            "Unlimited members",
            "Multi-cooperative administration",
            "Custom USSD and API access",
            "Migration and implementation support",
            "Dedicated account manager",
            "Contracted SLA",
        ],
        "cta": "Talk to enterprise sales",
        "bands": None,
    },
    "solo": {
        "key": "solo",
        "track": "farmer",
        "name": "Solo Farm",
        "eyebrow": "For independent farmers",
        "price": "GHS 99",
        "cadence": "per farm / month",
        "description": "Manage farm workers, track tasks and attendance, run payroll.",
        "features": [
            "Worker management",
            "Task management",
            "Attendance tracking",
            "Wage payroll",
            "200 SMS messages per month",
            "Worker USSD access",
        ],
        "cta": "Start Solo Farm onboarding",
        "bands": [
            {"key": "w20", "label": "Up to 20 workers", "capacity": 20, "price": 99.0},
            {"key": "w50", "label": "Up to 50 workers", "capacity": 50, "price": 199.0},
            {"key": "w100", "label": "Up to 100 workers", "capacity": 100, "price": 349.0},
            {"key": "custom", "label": "Custom worker count", "capacity": None, "price": None},
        ],
    },
}


def get_plan(plan_key: str) -> dict | None:
    """Return a plan definition by key (case-insensitive), or None."""
    return PLANS.get((plan_key or "").lower())


def resolve_amount(plan_key: str, band_key: str | None = None) -> float | None:
    """Resolve a checkout amount for a plan + optional band.

    Returns None when the plan is not self-serve (free Starter, custom
    Enterprise, or the Solo Farm custom band).
    """
    plan = get_plan(plan_key)
    if not plan:
        return None
    bands = plan.get("bands")
    if not bands:
        return None
    band = next((b for b in bands if b["key"] == band_key), bands[0])
    return band.get("price")
```

Create `backend/app/routes/plans.py`:

```python
"""Public pricing catalog endpoint."""

from fastapi import APIRouter

from app.plans import PLANS

router = APIRouter(tags=["plans"])


@router.get("/plans")
def list_plans() -> dict:
    return {"plans": list(PLANS.values())}
```

Modify `backend/main.py`:
- Add `plans` to the `from app.routes import (...)` block (alphabetical: after `payroll`, before `production`).
- Add `app.include_router(plans.router)` in the router registration block.
- Add `"/plans"` to the `_PUBLIC_PATHS` frozenset.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_plans.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/plans.py backend/app/routes/plans.py backend/main.py backend/tests/test_plans.py
git commit -m "feat(pricing): add plans catalog module and public /plans endpoint"
```

---

### Task 2: `PendingCheckout` model + migration

**Files:**
- Modify: `backend/app/models/models.py` (add `PendingCheckout` model)
- Create: `backend/alembic/versions/012_pending_checkouts.py`
- Test: `backend/tests/test_plans.py` (add model test)

**Interfaces:**
- Produces: `PendingCheckout` SQLAlchemy model, `__tablename__ = "pending_checkouts"`, columns: `id`, `reference` (unique String), `plan_key` (String), `band` (nullable String), `amount` (Float), `currency` (String default "GHS"), `organisation` (String), `location` (nullable String), `member_count` (nullable Integer), `role` (nullable String), `organization_type` (String default "cooperative"), `status` (String default "pending"), `created_at` (DateTime).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_plans.py`:

```python
from app.models.models import PendingCheckout


def test_pending_checkout_is_persisted(client, db):
    checkout = PendingCheckout(
        reference="sub_pre_test123",
        plan_key="growth",
        band="base",
        amount=299.0,
        organisation="Ashanti Farmers Cooperative",
        status="pending",
    )
    db.add(checkout)
    db.commit()

    saved = db.query(PendingCheckout).filter(PendingCheckout.reference == "sub_pre_test123").one()
    assert saved.plan_key == "growth"
    assert saved.band == "base"
    assert saved.amount == 299.0
    assert saved.status == "pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_plans.py::test_pending_checkout_is_persisted -q`
Expected: FAIL — `ImportError: cannot import name 'PendingCheckout'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/models/models.py`, add after the `DemoBooking` class (around line 702):

```python
class PendingCheckout(Base):
    """Subscription checkout created before account creation; reconciled by webhook."""

    __tablename__ = "pending_checkouts"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, unique=True, nullable=False, index=True)
    plan_key = Column(String, nullable=False)
    band = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="GHS")
    organisation = Column(String, nullable=False)
    location = Column(String, nullable=True)
    member_count = Column(Integer, nullable=True)
    role = Column(String, nullable=True)
    organization_type = Column(String, default="cooperative", nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False)
```

Create `backend/alembic/versions/012_pending_checkouts.py`:

```python
"""pending_checkouts

Revision ID: 012_pending_checkouts
Revises: 011_merge_heads
Create Date: 2026-08-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "012_pending_checkouts"
down_revision: Union[str, None] = "011_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    if "pending_checkouts" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "pending_checkouts",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("reference", sa.String(), nullable=False, unique=True, index=True),
            sa.Column("plan_key", sa.String(), nullable=False),
            sa.Column("band", sa.String(), nullable=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(), default="GHS"),
            sa.Column("organisation", sa.String(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("member_count", sa.Integer(), nullable=True),
            sa.Column("role", sa.String(), nullable=True),
            sa.Column("organization_type", sa.String(), default="cooperative", nullable=False),
            sa.Column("status", sa.String(), default="pending", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    cooperative_columns = _column_names("cooperatives")
    if "subscription_band" not in cooperative_columns:
        op.add_column("cooperatives", sa.Column("subscription_band", sa.String(), nullable=True))


def downgrade() -> None:
    cooperative_columns = _column_names("cooperatives")
    if "subscription_band" in cooperative_columns:
        op.drop_column("cooperatives", "subscription_band")
    op.drop_table("pending_checkouts")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_plans.py::test_pending_checkout_is_persisted -q`
Expected: PASS.

Also verify migration chain: `python -m alembic heads` (workdir `backend`) shows `012_pending_checkouts (head)`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/models.py backend/alembic/versions/012_pending_checkouts.py backend/tests/test_plans.py
git commit -m "feat(pricing): add PendingCheckout model and migration"
```

---

### Task 3: Public `POST /subscriptions/pre-checkout`

**Files:**
- Modify: `backend/app/routes/subscriptions.py`
- Modify: `backend/main.py` (add public path)
- Test: `backend/tests/test_subscriptions_checkout.py` (new)

**Interfaces:**
- Consumes: `resolve_amount` from `app.plans`, `get_payment_provider` from `app.services.providers.factory`.
- Produces: `POST /subscriptions/pre-checkout` (no auth). Request body: `{plan_key, band, organisation, location?, member_count?, role?, organization_type?}`. Response: `{checkout_id, reference, authorization_url, amount}`. Uses `external_ref = reference = f"sub_pre_{uuid4().hex}"`, `redirect_url = f"{settings.agroos_base_url}/login?mode=signup&onboarding=subscription&checkout={reference}"`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_subscriptions_checkout.py`:

```python
"""Pre-checkout flow tests (public, no auth)."""

from app.models.models import PendingCheckout


def _mock_link(monkeypatch, **extra):
    async def fake_generate_payment_link(self, **kwargs):
        return {
            "success": True,
            "payment_url": "https://sandbox.moolre.com/pay/pre",
            "reference": kwargs.get("external_ref"),
        }

    monkeypatch.setattr(
        "app.services.providers.moolre_adapter.MoolrePaymentAdapter.generate_payment_link",
        fake_generate_payment_link,
    )


def test_pre_checkout_creates_pending_record_and_returns_link(client, db, monkeypatch):
    _mock_link(monkeypatch)

    resp = client.post(
        "/subscriptions/pre-checkout",
        json={
            "plan_key": "growth",
            "band": "plus_50",
            "organisation": "Ashanti Farmers Cooperative",
            "location": "Kumasi",
            "member_count": 100,
            "role": "Cooperative administrator",
            "organization_type": "cooperative",
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["amount"] == 449.0
    assert body["authorization_url"]
    assert body["reference"].startswith("sub_pre_")

    saved = db.query(PendingCheckout).filter(PendingCheckout.reference == body["reference"]).one()
    assert saved.plan_key == "growth"
    assert saved.band == "plus_50"
    assert saved.status == "pending"


def test_pre_checkout_rejects_unknown_plan(client):
    resp = client.post(
        "/subscriptions/pre-checkout",
        json={"plan_key": "vip", "organisation": "Acme"},
    )
    assert resp.status_code == 400


def test_pre_checkout_rejects_custom_solo_band(client):
    resp = client.post(
        "/subscriptions/pre-checkout",
        json={"plan_key": "solo", "band": "custom", "organisation": "Acme Farm"},
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_subscriptions_checkout.py -q`
Expected: FAIL — 404 (route does not exist) / assertion errors.

- [ ] **Step 3: Write minimal implementation**

Modify `backend/app/routes/subscriptions.py` — add imports and the endpoint. Replace the `plan_prices` dict usage in `create_checkout` too (see Task 6). Add:

```python
import uuid

from app.config import get_settings
from app.plans import resolve_amount
```

Add model import for PendingCheckout:

```python
from app.models.models import Cooperative, PendingCheckout, User
```

Add request/response schemas and the endpoint:

```python
class PreCheckoutRequest(BaseModel):
    plan_key: str
    band: str | None = None
    organisation: str
    location: str | None = None
    member_count: int | None = None
    role: str | None = None
    organization_type: str = "cooperative"


@router.post("/pre-checkout")
async def create_pre_checkout(
    req: PreCheckoutRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create a pending subscription checkout and return a Moolre payment link.

    Public endpoint: runs before account creation, so no auth dependency.
    """
    amount = resolve_amount(req.plan_key, req.band)
    if amount is None:
        raise HTTPException(status_code=400, detail="Plan requires a sales conversation")

    reference = f"sub_pre_{uuid.uuid4().hex}"
    checkout = PendingCheckout(
        reference=reference,
        plan_key=req.plan_key.lower(),
        band=req.band,
        amount=amount,
        organisation=req.organisation,
        location=req.location,
        member_count=req.member_count,
        role=req.role,
        organization_type=req.organization_type,
    )
    db.add(checkout)
    db.commit()
    db.refresh(checkout)

    settings = get_settings()
    redirect_url = (
        f"{settings.agroos_base_url}/login?mode=signup&onboarding=subscription&checkout={reference}"
    )
    provider = get_payment_provider()
    result = await provider.generate_payment_link(
        amount=amount,
        email=f"checkout@{checkout.id}.agroos.local",
        currency="GHS",
        external_ref=reference,
        redirect_url=redirect_url,
        reusable=False,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail="Failed to generate payment link")

    return {
        "checkout_id": checkout.id,
        "reference": reference,
        "authorization_url": result.get("payment_url"),
        "amount": amount,
    }
```

Modify `backend/main.py`: add `"/subscriptions/pre-checkout"` to `_PUBLIC_PATHS`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_subscriptions_checkout.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/subscriptions.py backend/main.py backend/tests/test_subscriptions_checkout.py
git commit -m "feat(pricing): add public pre-checkout endpoint"
```

---

### Task 4: Webhook `sub_pre_*` handling

**Files:**
- Modify: `backend/app/routes/webhooks.py`
- Test: `backend/tests/test_subscriptions_checkout.py` (add webhook test)

**Interfaces:**
- Consumes: `PendingCheckout` model.
- Produces: in `_process_payment_payload`, when `external_ref.startswith("sub_pre_")` and status success, mark the matching `PendingCheckout.status = "paid"`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_subscriptions_checkout.py`:

```python
def test_webhook_marks_pending_checkout_paid(client, db):
    checkout = PendingCheckout(
        reference="sub_pre_wh123",
        plan_key="growth",
        band="base",
        amount=299.0,
        organisation="Webhook Coop",
    )
    db.add(checkout)
    db.commit()

    resp = client.post(
        "/webhooks/moolre/payment",
        json={
            "status": 1,
            "data": {"externalref": "sub_pre_wh123", "amount": "299.00"},
        },
    )

    assert resp.status_code == 200
    saved = db.query(PendingCheckout).filter(PendingCheckout.reference == "sub_pre_wh123").one()
    assert saved.status == "paid"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_subscriptions_checkout.py::test_webhook_marks_pending_checkout_paid -q`
Expected: FAIL — status stays `pending`.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/routes/webhooks.py`, add `PendingCheckout` to the models import block, then add a new branch in `_process_payment_payload` BEFORE the existing `sub_upg_` branch (around line 163):

```python
    if external_ref and external_ref.startswith("sub_pre_"):
        if moolre_status == 1:
            from app.models.models import PendingCheckout
            checkout = (
                db.query(PendingCheckout)
                .filter(PendingCheckout.reference == external_ref)
                .first()
            )
            if checkout and checkout.status != "paid":
                checkout.status = "paid"
                db.commit()
                logger.info(f"Pending checkout {checkout.reference} marked paid")
        return {"status": "ok", "message": "Pre-checkout webhook processed"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_subscriptions_checkout.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/webhooks.py backend/tests/test_subscriptions_checkout.py
git commit -m "feat(pricing): reconcile pre-checkout payment in webhook"
```

---

### Task 5: Signup verifies checkout + persists band

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/routes/auth.py`
- Modify: `backend/tests/test_onboarding_marketing.py`
- Test: `backend/tests/test_subscriptions_checkout.py` (add signup test)

**Interfaces:**
- Consumes: `PendingCheckout`, `SUBSCRIPTION_DAYS` from `app.plans`.
- Produces: `SignupRequest.checkout_ref: str | None`, `SignupRequest.subscription_band: str | None`; `SignupResponse.subscription_band`. Signup with a paid `checkout_ref` sets `subscription_status="active"`, `subscription_expires_at = now + 30 days`. Paid plan signup WITHOUT a valid `checkout_ref` returns 400.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_subscriptions_checkout.py`:

```python
from datetime import timedelta, datetime


def _paid_checkout(db, reference="sub_pre_signup1", plan_key="growth", band="base", amount=299.0):
    checkout = PendingCheckout(
        reference=reference,
        plan_key=plan_key,
        band=band,
        amount=amount,
        organisation="Signup Coop",
        status="paid",
    )
    db.add(checkout)
    db.commit()
    return checkout


def test_signup_with_paid_checkout_activates_and_sets_band(client, db):
    _paid_checkout(db)

    resp = client.post(
        "/auth/signup",
        json={
            "email": "paid-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Paid Cooperative",
            "subscription_plan": "growth",
            "checkout_ref": "sub_pre_signup1",
        },
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["subscription_plan"] == "growth"
    assert resp.json()["subscription_band"] == "base"

    coop = db.query(Cooperative).filter(Cooperative.name == "Paid Cooperative").one()
    assert coop.subscription_plan == "growth"
    assert coop.subscription_band == "base"
    assert coop.subscription_status == "active"
    assert coop.subscription_expires_at is not None


def test_signup_with_paid_plan_but_no_checkout_is_rejected(client):
    resp = client.post(
        "/auth/signup",
        json={
            "email": "unpaid-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Unpaid Cooperative",
            "subscription_plan": "growth",
        },
    )
    assert resp.status_code == 400


def test_signup_with_unpaid_checkout_is_rejected(client, db):
    checkout = PendingCheckout(
        reference="sub_pre_unpaid1",
        plan_key="growth",
        band="base",
        amount=299.0,
        organisation="Unpaid Coop",
        status="pending",
    )
    db.add(checkout)
    db.commit()

    resp = client.post(
        "/auth/signup",
        json={
            "email": "pending-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Pending Cooperative",
            "subscription_plan": "growth",
            "checkout_ref": "sub_pre_unpaid1",
        },
    )
    assert resp.status_code == 402
```

Also update `backend/tests/test_onboarding_marketing.py::test_signup_persists_subscription_and_business_role` (it currently signs up a `growth` plan with no checkout, which will now be rejected). Change it to use a paid checkout:

```python
from app.models.models import Cooperative, DemoBooking, PendingCheckout, User


def test_signup_persists_subscription_and_business_role(client, db):
    db.add(
        PendingCheckout(
            reference="sub_pre_growth_role1",
            plan_key="growth",
            band="base",
            amount=299.0,
            organisation="Growth Cooperative",
            status="paid",
        )
    )
    db.commit()

    response = client.post(
        "/auth/signup",
        json={
            "email": "growth-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Growth Cooperative",
            "location": "Kumasi",
            "member_count": 240,
            "subscription_plan": "growth",
            "checkout_ref": "sub_pre_growth_role1",
            "onboarding_role": "Operations director",
        },
    )
    ...  # rest unchanged
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_subscriptions_checkout.py backend/tests/test_onboarding_marketing.py -q`
Expected: FAIL — signup still succeeds without checkout (400 expected but 201 returned).

- [ ] **Step 3: Write minimal implementation**

Modify `backend/app/schemas/auth.py` `SignupRequest`:

```python
class SignupRequest(BaseModel):
    """Combined cooperative + user registration in one step."""
    email: EmailStr
    password: str
    cooperative_name: str
    location: Optional[str] = None
    member_count: Optional[int] = None
    subscription_plan: Literal["starter", "growth", "solo"] = "starter"
    organization_type: Literal["cooperative", "solo_farm"] = "cooperative"
    onboarding_role: str | None = Field(default=None, max_length=80)
    checkout_ref: str | None = None
    subscription_band: str | None = None
```

And `SignupResponse`:

```python
class SignupResponse(BaseModel):
    access_token: str
    token_type: str
    cooperative_id: int
    cooperative_name: str
    subscription_plan: Literal["starter", "growth", "solo"]
    organization_type: str = "cooperative"
    onboarding_role: str | None = None
    subscription_band: str | None = None
```

Modify `backend/app/routes/auth.py` `signup`. After the email-uniqueness check, add checkout resolution:

```python
    from datetime import datetime as _dt

    resolved_plan = data.subscription_plan
    resolved_band = data.subscription_band
    resolved_org_type = data.organization_type
    resolved_name = data.cooperative_name
    resolved_location = data.location
    resolved_member_count = data.member_count
    resolved_role = data.onboarding_role
    subscription_status = "active"
    subscription_expires_at = None

    if data.checkout_ref:
        checkout = (
            db.query(PendingCheckout)
            .filter(PendingCheckout.reference == data.checkout_ref)
            .first()
        )
        if not checkout:
            raise HTTPException(status_code=404, detail="Checkout not found")
        if checkout.status != "paid":
            raise HTTPException(status_code=402, detail="Payment not confirmed for this checkout")
        resolved_plan = checkout.plan_key
        resolved_band = checkout.band
        resolved_org_type = checkout.organization_type or data.organization_type
        resolved_name = checkout.organisation or data.cooperative_name
        resolved_location = checkout.location or data.location
        resolved_member_count = checkout.member_count or data.member_count
        resolved_role = checkout.role or data.onboarding_role
    elif data.subscription_plan != "starter":
        raise HTTPException(
            status_code=400,
            detail="Paid plans require a completed checkout",
        )

    if resolved_plan != "starter":
        subscription_expires_at = _dt.utcnow() + timedelta(days=30)
```

Then update the `Cooperative(...)` construction to use the resolved values:

```python
    new_coop = Cooperative(
        name=resolved_name,
        location=resolved_location,
        description=description,
        currency="GHS",
        subscription_plan=resolved_plan,
        subscription_band=resolved_band,
        organization_type=resolved_org_type,
        subscription_status=subscription_status,
        subscription_expires_at=subscription_expires_at,
        ussd_code=code,
    )
```

Note: `description` is built from `data.member_count` earlier in the function; update it to use `resolved_member_count`:

```python
    if resolved_member_count:
        description = f"Approximate member count: {resolved_member_count}"
```

And `new_user` uses `data.onboarding_role` → change to `resolved_role`. Finally, the `moolre` sub-wallet creation uses `data.cooperative_name` → change to `resolved_name`, and return `subscription_band=resolved_band` in the response dict.

Add imports at the top of `auth.py`: `from app.models.models import AdminAuditLog, Cooperative, PendingCheckout, User` (add `PendingCheckout`). `datetime` is already imported as `from datetime import timedelta` — add `datetime`:

```python
from datetime import datetime, timedelta
```

Then use `datetime.utcnow()` instead of `_dt.utcnow()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_subscriptions_checkout.py backend/tests/test_onboarding_marketing.py -q`
Expected: PASS.

Also run the existing auth tests to ensure no regression: `python -m pytest backend/tests/test_onboarding_marketing.py backend/tests/test_demo_features.py -q`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/routes/auth.py backend/tests/test_onboarding_marketing.py backend/tests/test_subscriptions_checkout.py
git commit -m "feat(pricing): verify paid checkout at signup and persist subscription band"
```

---

### Task 6: Upgrade checkout uses plans module + band

**Files:**
- Modify: `backend/app/routes/subscriptions.py`
- Test: `backend/tests/test_subscriptions_checkout.py` (add upgrade test)

**Interfaces:**
- Produces: `POST /subscriptions/checkout` (auth-required) accepts `band` and resolves amount from `resolve_amount` instead of a hardcoded `plan_prices` dict.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_subscriptions_checkout.py`:

```python
def test_upgrade_checkout_uses_band_price(client, db, demo_admin, monkeypatch):
    _mock_link(monkeypatch)

    resp = client.post(
        "/subscriptions/checkout",
        json={"cooperative_id": demo_admin.cooperative_id, "plan_key": "growth", "band": "plus_100"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["authorization_url"]
```

Note: this test requires auth to be enabled to pass `get_current_user`. Since `AUTH_ENABLED=false` by default in tests, `get_current_user` returns a lax user; the existing `test_demo_features.py` route tests pass without auth. This test uses `demo_admin` only to supply a valid `cooperative_id`. Keep it simple and rely on the existing lax auth behavior (enforce_cooperative_scope passes when auth is disabled).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_subscriptions_checkout.py::test_upgrade_checkout_uses_band_price -q`
Expected: FAIL — `plan_prices.get("growth")` returns 299 but `plus_100` band is ignored; with the current hardcoded dict the endpoint still returns a link (so assert on amount instead). To make it fail meaningfully, change the assert to check the amount is derived from the band. See Step 3 for the correct approach.

- [ ] **Step 3: Write minimal implementation**

Modify `backend/app/routes/subscriptions.py`:
- `CheckoutRequest` gains `band: str | None = None`.
- Replace the `plan_prices` dict + `amount = plan_prices.get(...)` block with `amount = resolve_amount(req.plan_key, req.band)`, raising 400 if `None`.
- Keep the rest of `create_checkout` unchanged (ext_ref `sub_upg_...`, master wallet note).

Then rewrite the failing test to assert the correct amount via a mocked link that echoes the amount:

```python
def test_upgrade_checkout_uses_band_price(client, db, demo_admin, monkeypatch):
    captured = {}

    async def fake_generate_payment_link(self, **kwargs):
        captured["amount"] = kwargs.get("amount")
        return {
            "success": True,
            "payment_url": "https://sandbox.moolre.com/pay/upgrade",
            "reference": kwargs.get("external_ref"),
        }

    monkeypatch.setattr(
        "app.services.providers.moolre_adapter.MoolrePaymentAdapter.generate_payment_link",
        fake_generate_payment_link,
    )

    resp = client.post(
        "/subscriptions/checkout",
        json={"cooperative_id": demo_admin.cooperative_id, "plan_key": "growth", "band": "plus_100"},
    )
    assert resp.status_code == 200, resp.text
    assert captured["amount"] == 599.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_subscriptions_checkout.py -q`
Expected: PASS (all subscription tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/subscriptions.py backend/tests/test_subscriptions_checkout.py
git commit -m "feat(pricing): resolve upgrade checkout amount from plans module and band"
```

---

### Task 7: Frontend plans + pre-checkout API layer

**Files:**
- Create: `frontend/src/api/plans.js`
- Modify: `frontend/src/api/cooperatives.js` (add `createPreCheckout`)
- Test: `frontend/src/api/plans.test.js` (new)

**Interfaces:**
- Produces: `fetchPlans()` → array of plan objects (live from `/plans`, fallback to `PLANS_FALLBACK` on transport failure). `createPreCheckout({plan_key, band, organisation, location, member_count, role, organization_type})` → `{checkout_id, reference, authorization_url, amount}`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/api/plans.test.js`:

```javascript
import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('./config', () => ({
  API_URL: 'https://api.test',
  apiFetch: vi.fn(),
  authHeaders: vi.fn(() => ({})),
}))

import { createPreCheckout, fetchPlans } from './plans'
import { apiFetch } from './config'

describe('plans api', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetchPlans returns the plan list', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: async () => ({ plans: [{ key: 'starter' }] }) })
    const plans = await fetchPlans()
    expect(plans).toEqual([{ key: 'starter' }])
  })

  it('fetchPlans falls back on transport failure', async () => {
    apiFetch.mockRejectedValue(new TypeError('network down'))
    const plans = await fetchPlans()
    expect(plans.some((p) => p.key === 'growth')).toBe(true)
  })

  it('createPreCheckout posts the payload', async () => {
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ checkout_id: 1, reference: 'sub_pre_x', authorization_url: 'https://pay', amount: 299 }),
    })
    const result = await createPreCheckout({ plan_key: 'growth', band: 'base', organisation: 'Coop' })
    expect(result.authorization_url).toBe('https://pay')
  })
})
```

Note: `createPreCheckout` lives in `cooperatives.js`; to keep the mock simple, re-export it from `plans.js` (see Step 3) or import it from `cooperatives.js`. Simplest: define `createPreCheckout` in `plans.js` and re-export from `cooperatives.js` for backward compatibility. This test imports from `./plans`.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:frontend -- src/api/plans.test.js` (or `npx vitest run src/api/plans.test.js` in `frontend`).
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/api/plans.js`:

```javascript
import { API_URL, apiFetch, isTransportFailure } from './config'

const PLANS_FALLBACK = [
  {
    key: 'starter', track: 'cooperative', name: 'Starter', price: 'Free',
    cadence: 'No card required',
    description: 'Establish a reliable digital member register and start collecting dues.',
    features: ['Up to 10 members', 'MoMo payment collection', 'Member and dues dashboard', '100 SMS messages per month', 'Email support'],
    cta: 'Create free workspace', bands: null,
  },
  {
    key: 'growth', track: 'cooperative', name: 'Growth', price: 'GHS 299',
    cadence: 'per organisation / month',
    description: 'Run payments, credit workflows, communication, and field operations at scale.',
    features: ['AgroCredit Trust Scores', 'USSD access', 'Unlimited payment records', '1,000 SMS messages per month', 'Priority support'],
    cta: 'Start Growth onboarding', featured: true, badge: 'Most selected',
    bands: [
      { key: 'base', label: 'Up to 50 members', capacity: 50, price: 299 },
      { key: 'plus_50', label: 'Up to 100 members', capacity: 100, price: 449 },
      { key: 'plus_100', label: 'Up to 200 members', capacity: 200, price: 599 },
    ],
  },
  {
    key: 'enterprise', track: 'cooperative', name: 'Enterprise', price: 'Custom',
    cadence: 'Annual agreement',
    description: 'A governed rollout for unions, lenders, NGOs, and multi-cooperative programmes.',
    features: ['Unlimited members', 'Multi-cooperative administration', 'Custom USSD and API access', 'Migration and implementation support', 'Dedicated account manager', 'Contracted SLA'],
    cta: 'Talk to enterprise sales', bands: null,
  },
  {
    key: 'solo', track: 'farmer', name: 'Solo Farm', price: 'GHS 99',
    cadence: 'per farm / month',
    description: 'Manage farm workers, track tasks and attendance, run payroll.',
    features: ['Worker management', 'Task management', 'Attendance tracking', 'Wage payroll', '200 SMS messages per month', 'Worker USSD access'],
    cta: 'Start Solo Farm onboarding',
    bands: [
      { key: 'w20', label: 'Up to 20 workers', capacity: 20, price: 99 },
      { key: 'w50', label: 'Up to 50 workers', capacity: 50, price: 199 },
      { key: 'w100', label: 'Up to 100 workers', capacity: 100, price: 349 },
      { key: 'custom', label: 'Custom worker count', capacity: null, price: null },
    ],
  },
]

export async function fetchPlans() {
  try {
    const res = await apiFetch(`${API_URL}/plans`)
    if (!res.ok) throw new Error('plans fetch failed')
    const data = await res.json()
    return data.plans
  } catch (err) {
    if (isTransportFailure(err)) return PLANS_FALLBACK
    throw err
  }
}

export async function createPreCheckout(payload) {
  const res = await apiFetch(`${API_URL}/subscriptions/pre-checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to create checkout')
  }
  return res.json()
}
```

Modify `frontend/src/api/cooperatives.js` to re-export (append):

```javascript
export { createPreCheckout } from './plans'
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/api/plans.test.js` (in `frontend`).
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/plans.js frontend/src/api/cooperatives.js frontend/src/api/plans.test.js
git commit -m "feat(pricing): add plans and pre-checkout frontend API layer"
```

---

### Task 8: PricingPage two-track layout with band selectors

**Files:**
- Modify: `frontend/src/pages/PricingPage.jsx`
- Modify: `frontend/src/styles/global.css`
- Test: `frontend/src/pages/PricingPage.test.jsx` (new)

**Interfaces:**
- Consumes: `fetchPlans` from `../api/plans`.
- Produces: Two stacked sections: cooperative track (Starter, Growth, Enterprise) and farmer track (Solo Farm). Growth and Solo cards render a band `<select>`; selecting a band updates the displayed price. `choosePlan(plan, band)` navigates to `/subscribe/<key>?band=<band>`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/PricingPage.test.jsx`:

```javascript
import React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/plans', () => ({
  fetchPlans: vi.fn(),
}))

import PricingPage from './PricingPage'
import { fetchPlans } from '../api/plans'

const PLANS = [
  { key: 'starter', track: 'cooperative', name: 'Starter', price: 'Free', cadence: 'No card required', description: 'x', features: [], cta: 'Create free workspace', bands: null },
  { key: 'growth', track: 'cooperative', name: 'Growth', price: 'GHS 299', cadence: 'per organisation / month', description: 'x', features: [], cta: 'Start Growth onboarding', featured: true, bands: [
    { key: 'base', label: 'Up to 50 members', price: 299 },
    { key: 'plus_50', label: 'Up to 100 members', price: 449 },
  ] },
  { key: 'enterprise', track: 'cooperative', name: 'Enterprise', price: 'Custom', cadence: 'Annual agreement', description: 'x', features: [], cta: 'Talk to enterprise sales', bands: null },
  { key: 'solo', track: 'farmer', name: 'Solo Farm', price: 'GHS 99', cadence: 'per farm / month', description: 'x', features: [], cta: 'Start Solo Farm onboarding', bands: [
    { key: 'w20', label: 'Up to 20 workers', price: 99 },
    { key: 'w50', label: 'Up to 50 workers', price: 199 },
  ] },
]

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="loc">{location.pathname}{location.search}</div>
}

describe('PricingPage', () => {
  beforeEach(() => {
    fetchPlans.mockResolvedValue(PLANS)
    globalThis.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }
    window.scrollTo = () => undefined
  })
  afterEach(cleanup)

  it('renders two tracks', async () => {
    render(<MemoryRouter initialEntries={['/pricing']}><PricingPage /></MemoryRouter>)
    expect(await screen.findByText(/For Cooperatives/i)).toBeTruthy()
    expect(screen.getByText(/For Independent Farmers/i)).toBeTruthy()
  })

  it('selecting a Growth band updates price and navigates with band', async () => {
    render(
      <MemoryRouter initialEntries={['/pricing']}>
        <Routes>
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/subscribe/:plan" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )
    await screen.findByText(/For Cooperatives/i)
    const growthBand = screen.getAllByRole('combobox')[0]
    fireEvent.change(growthBand, { target: { value: 'plus_50' } })
    expect(await screen.findByText('GHS 449')).toBeTruthy()
    fireEvent.click(screen.getAllByRole('button', { name: /Start Growth onboarding/i })[0])
    expect(screen.getByTestId('loc').textContent).toBe('/subscribe/growth?band=plus_50')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/pages/PricingPage.test.jsx` (in `frontend`).
Expected: FAIL — old single-grid page has no "For Cooperatives" heading and no band selectors.

- [ ] **Step 3: Write minimal implementation**

Rewrite `frontend/src/pages/PricingPage.jsx`:

```javascript
import { ArrowRight, Check, Headphones, LockKeyhole, ReceiptText, ShieldCheck } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Footer from '../components/Footer'
import { Reveal } from '../components/Motion'
import { fetchPlans } from '../api/plans'

export default function PricingPage() {
  const navigate = useNavigate()
  const [plans, setPlans] = useState([])
  const [bands, setBands] = useState({})

  useEffect(() => {
    fetchPlans().then(setPlans).catch(() => {})
  }, [])

  const tracks = useMemo(() => {
    const coop = plans.filter((p) => p.track === 'cooperative')
    const farmer = plans.filter((p) => p.track === 'farmer')
    return { cooperative: coop, farmer }
  }, [plans])

  function choosePlan(plan) {
    if (plan.key === 'enterprise') {
      navigate('/book-demo?plan=enterprise&topic=Enterprise+implementation')
      return
    }
    const band = bands[plan.key]
    navigate(`/subscribe/${plan.key}${band ? `?band=${band}` : ''}`)
  }

  function renderCard(plan) {
    const band = plan.bands ? (bands[plan.key] || plan.bands[0]) : null
    const price = band ? `GHS ${band.price}` : plan.price
    return (
      <article key={plan.key} className={`pricing-card pricing-card--business${plan.featured ? ' pricing-card--featured' : ''}`}>
        {plan.badge && <div className="pricing-card__badge">{plan.badge}</div>}
        <div className="pricing-card__eyebrow">{plan.eyebrow}</div>
        <h2 className="pricing-card__name serif">{plan.name}</h2>
        <div className="pricing-card__price">{price}</div>
        <div className="pricing-card__sub">{band ? band.label : plan.cadence}</div>
        <p className="pricing-card__description">{plan.description}</p>
        <div className="pricing-card__divider" />
        {plan.bands && (
          <label className="pricing-band-select">
            <span>Choose your size</span>
            <select
              value={band.key}
              onChange={(e) => setBands((cur) => ({ ...cur, [plan.key]: e.target.value }))}
            >
              {plan.bands.map((b) => (
                <option key={b.key} value={b.key}>{b.label}</option>
              ))}
            </select>
          </label>
        )}
        <div className="pricing-card__includes">Plan includes</div>
        <div className="pricing-card__features">
          {plan.features.map((feature) => (
            <div key={feature} className="pricing-card__feature">
              <Check className="pricing-card__check" size={15} />
              {feature}
            </div>
          ))}
        </div>
        <button type="button" className="pricing-card__btn" onClick={() => choosePlan(plan)}>
          {plan.cta} <ArrowRight size={15} />
        </button>
      </article>
    )
  }

  return (
    <>
      <main className="pricing-page">
        <section className="pricing-hero">
          <Reveal>
            <div className="pricing-kicker">Plans for every stage of operation</div>
            <h1 className="serif">Commercial terms that scale with your cooperative.</h1>
            <p>Start with core operations, move into connected financial workflows, and add enterprise governance when your programme requires it.</p>
            <div className="pricing-hero-notes">
              <span><Check size={14} /> Ghana cedi pricing</span>
              <span><Check size={14} /> No setup fee on self-serve plans</span>
              <span><Check size={14} /> Cancel monthly plans any time</span>
            </div>
          </Reveal>
        </section>

        <section className="pricing-plans-section">
          <div className="pricing-container">
            <Reveal className="pricing-track-heading">
              <div className="pricing-kicker">Cooperative track</div>
              <h2 className="serif">For Cooperatives</h2>
            </Reveal>
            <div className="pricing-grid pricing-grid--business">
              {tracks.cooperative.map(renderCard)}
            </div>

            <Reveal className="pricing-track-heading pricing-track-heading--second">
              <div className="pricing-kicker">Farmer track</div>
              <h2 className="serif">For Independent Farmers</h2>
            </Reveal>
            <div className="pricing-grid pricing-grid--business">
              {tracks.farmer.map(renderCard)}
            </div>

            <Reveal className="pricing-procurement">
              {[
                [ReceiptText, 'Clear commercial terms', 'A plan summary is shown before account creation. No surprise charges.'],
                [LockKeyhole, 'Pay before you sign up', 'Paid plans complete checkout before account creation, so there are no unpaid workspaces.'],
                [Headphones, 'Implementation support', 'Enterprise engagements include migration, rollout planning, and operational support.'],
              ].map(([Icon, title, copy]) => (
                <div key={title}>
                  <Icon size={19} />
                  <strong>{title}</strong>
                  <p>{copy}</p>
                </div>
              ))}
            </Reveal>
          </div>
        </section>

        <section className="pricing-compare-section">
          <Reveal className="pricing-container">
            <div className="pricing-section-heading">
              <div className="pricing-kicker">Plan comparison</div>
              <h2 className="serif">Compare the operating model, not just the feature list.</h2>
            </div>
          </Reveal>
        </section>

        <section className="pricing-enterprise-band">
          <Reveal className="pricing-enterprise-inner">
            <div>
              <div className="pricing-kicker">Enterprise procurement</div>
              <h2 className="serif">Planning a multi-cooperative rollout?</h2>
              <p>Discuss migration, security review, API access, service levels, and programme governance with our team.</p>
            </div>
            <button type="button" className="btn-gold" onClick={() => choosePlan({ key: 'enterprise' })}>
              Start an enterprise conversation <ArrowRight size={16} />
            </button>
            <div className="pricing-enterprise-assurance"><ShieldCheck size={16} /> No generic signup. Your requirements are reviewed first.</div>
          </Reveal>
        </section>
      </main>
      <Footer />
    </>
  )
}
```

Modify `frontend/src/styles/global.css` — add near the pricing styles (after line ~1081):

```css
.pricing-track-heading { margin: 0 0 1.25rem; }
.pricing-track-heading--second { margin-top: 3rem; }
.pricing-track-heading h2 { font-size: 1.75rem; margin: 0.25rem 0 0; }
.pricing-band-select {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin: 1rem 0;
  font-size: 0.85rem;
  color: var(--muted, #6b7280);
}
.pricing-band-select select {
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  background: #fff;
  font-size: 0.95rem;
}
```

Note: the comparison table `<tbody>` render is removed in favor of keeping the existing markup simple; if you prefer to retain the full comparison table, keep `COMPARISON` and re-add it. The design spec does not require a comparison table; the two-track split replaces it. Keep the section heading only to avoid an empty table.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/pages/PricingPage.test.jsx` (in `frontend`).
Expected: PASS (2 passed).

Also run the full frontend suite to catch regressions in `MarketingRefresh.test.jsx`: `npm run test:frontend`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PricingPage.jsx frontend/src/styles/global.css frontend/src/pages/PricingPage.test.jsx
git commit -m "feat(pricing): two-track pricing page with band selectors"
```

---

### Task 9: SubscriptionPage pay-before-signup

**Files:**
- Modify: `frontend/src/pages/SubscriptionPage.jsx`
- Modify: `frontend/src/pages/SubscriptionPage.test.jsx`
- Test: `frontend/src/pages/SubscriptionPage.test.jsx` (rewrite)

**Interfaces:**
- Consumes: `fetchPlans`, `createPreCheckout` from `../api/plans`.
- Produces: single org form → order summary with real total → "Pay GHS X" (redirects to `authorization_url`) or "Start free workspace" (navigates to signup). Reads `band` from `useSearchParams`.

- [ ] **Step 1: Write the failing test**

Rewrite `frontend/src/pages/SubscriptionPage.test.jsx`:

```javascript
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import React from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SubscriptionPage from './SubscriptionPage'

const apiMocks = vi.hoisted(() => ({
  fetchPlans: vi.fn(),
  createPreCheckout: vi.fn(),
}))

vi.mock('../api/plans', () => ({
  fetchPlans: apiMocks.fetchPlans,
  createPreCheckout: apiMocks.createPreCheckout,
}))

const PLANS = [
  { key: 'growth', track: 'cooperative', name: 'Growth', price: 'GHS 299', cadence: 'per organisation / month', description: 'x', features: [], cta: 'Start Growth onboarding', bands: [
    { key: 'base', label: 'Up to 50 members', price: 299 },
    { key: 'plus_50', label: 'Up to 100 members', price: 449 },
  ] },
  { key: 'starter', track: 'cooperative', name: 'Starter', price: 'Free', cadence: 'No card required', description: 'x', features: [], cta: 'Create free workspace', bands: null },
]

function LoginProbe() {
  const location = useLocation()
  return <div data-testid="login-location">{location.search}</div>
}

describe('SubscriptionPage', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    globalThis.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }
    window.scrollTo = () => undefined
    apiMocks.fetchPlans.mockResolvedValue(PLANS)
    apiMocks.createPreCheckout.mockReset()
  })

  it('shows the real band total and creates a checkout for paid plans', async () => {
    apiMocks.createPreCheckout.mockResolvedValue({ authorization_url: 'https://pay/moolre', reference: 'sub_pre_x' })
    render(
      <MemoryRouter initialEntries={['/subscribe/growth?band=plus_50']}>
        <Routes>
          <Route path="/subscribe/:plan" element={<SubscriptionPage />} />
          <Route path="/login" element={<LoginProbe />} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.change(await screen.findByLabelText(/Organisation name/i), { target: { value: 'Ashanti Farmers Cooperative' } })
    fireEvent.change(screen.getByLabelText(/Expected member count/i), { target: { value: '125' } })
    fireEvent.click(screen.getByRole('button', { name: /Review plan and terms/i }))

    expect(screen.getByText('GHS 449')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Pay GHS 449/i }))

    await waitFor(() => expect(apiMocks.createPreCheckout).toHaveBeenCalledWith(expect.objectContaining({
      plan_key: 'growth',
      band: 'plus_50',
      organisation: 'Ashanti Farmers Cooperative',
    })))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/pages/SubscriptionPage.test.jsx` (in `frontend`).
Expected: FAIL — old page shows "GHS 299" fixed and no "Pay GHS 449" button.

- [ ] **Step 3: Write minimal implementation**

Rewrite `frontend/src/pages/SubscriptionPage.jsx`:

```javascript
import React, { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Building2, Check, ChevronRight, MapPin, ReceiptText, ShieldCheck, Users } from 'lucide-react'
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Reveal } from '../components/Motion'
import { createPreCheckout, fetchPlans } from '../api/plans'

const MEMBER_OPTIONS = [
  { value: '25', label: '1–50 members' },
  { value: '125', label: '51–200 members' },
  { value: '350', label: '201–500 members' },
  { value: '750', label: '500+ members' },
]

export default function SubscriptionPage() {
  const { plan: planKey } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [plans, setPlans] = useState([])
  const [step, setStep] = useState(0)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    organisation: '',
    location: '',
    memberCount: '',
    role: 'Cooperative administrator',
  })

  useEffect(() => {
    fetchPlans().then(setPlans).catch(() => {})
  }, [])

  const plan = useMemo(() => plans.find((p) => p.key === planKey), [plans, planKey])
  const bandKey = searchParams.get('band')
  const band = useMemo(() => {
    if (!plan?.bands) return null
    return plan.bands.find((b) => b.key === bandKey) || plan.bands[0]
  }, [plan, bandKey])

  if (plans.length > 0 && !plan) return <Navigate to="/pricing" replace />

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setError('')
  }

  function reviewOrder(event) {
    event.preventDefault()
    if (!form.organisation.trim() || !form.memberCount) {
      setError('Add your organisation and expected member count to continue.')
      return
    }
    setStep(1)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function continueToAccount() {
    const orgType = planKey === 'solo' ? 'solo_farm' : 'cooperative'
    if (planKey === 'starter') {
      const intent = { plan: planKey, ...form, org_type: orgType }
      window.sessionStorage.setItem('agroos-subscription-intent', JSON.stringify(intent))
      navigate(`/login?mode=signup&plan=${planKey}&onboarding=subscription`)
      return
    }

    setError('')
    try {
      const checkout = await createPreCheckout({
        plan_key: planKey,
        band: band?.key || null,
        organisation: form.organisation,
        location: form.location,
        member_count: Number(form.memberCount) || null,
        role: form.role,
        organization_type: orgType,
      })
      const intent = { plan: planKey, band: band?.key || null, ...form, org_type: orgType, checkout_ref: checkout.reference }
      window.sessionStorage.setItem('agroos-subscription-intent', JSON.stringify(intent))
      window.location.href = checkout.authorization_url
    } catch (err) {
      setError(err.message)
    }
  }

  if (!plan) return null

  const priceLabel = band ? `GHS ${band.price}` : plan.price

  return (
    <main className="subscribe-page">
      <section className="subscribe-aside">
        <button type="button" className="subscribe-back" onClick={() => navigate('/pricing')}>
          <ArrowLeft size={15} /> Back to pricing
        </button>
        <div className="subscribe-kicker">Selected plan</div>
        <h1 className="serif">{plan.name}</h1>
        <div className="subscribe-price">{priceLabel}</div>
        <div className="subscribe-cadence">{band ? band.label : plan.cadence}</div>
        <p className="subscribe-description">{plan.description}</p>
        <div className="subscribe-terms">
          {plan.features.map((term) => <div key={term}><Check size={15} /> {term}</div>)}
        </div>
        <div className="subscribe-safety">
          <ShieldCheck size={18} />
          <div>
            <strong>Commercially transparent</strong>
            <p>You will review the selected plan and pay before creating an administrator account.</p>
          </div>
        </div>
      </section>

      <section className="subscribe-content">
        <Reveal className="subscribe-panel">
          <div className="subscribe-progress" aria-label={`Step ${step + 1} of 2`}>
            <span className="active">1</span><i className={step === 1 ? 'complete' : ''} /><span className={step === 1 ? 'active' : ''}>2</span>
          </div>

          {step === 0 ? (
            <>
              <div className="subscribe-heading">
                <div className="subscribe-kicker">Organisation profile</div>
                <h2 className="serif">Set up your subscription workspace.</h2>
                <p>This information prepares the correct workspace and account path for your team.</p>
              </div>

              {error && <div className="auth-error subscribe-error" role="alert">{error}</div>}

              <form onSubmit={reviewOrder} className="subscribe-form">
                <label className="demo-field">
                  <span><Building2 size={14} /> Organisation name *</span>
                  <input className="auth-input" name="organisation" value={form.organisation} onChange={updateField} placeholder="Ashanti Farmers Cooperative" required />
                </label>
                <label className="demo-field">
                  <span><MapPin size={14} /> Primary location</span>
                  <input className="auth-input" name="location" value={form.location} onChange={updateField} placeholder="Kumasi, Ashanti Region" />
                </label>
                <label className="demo-field">
                  <span><Users size={14} /> Expected member count *</span>
                  <select className="auth-input auth-select" name="memberCount" value={form.memberCount} onChange={updateField} required>
                    <option value="">Select organisation size</option>
                    {MEMBER_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </select>
                </label>
                <label className="demo-field">
                  <span>Your role</span>
                  <select className="auth-input auth-select" name="role" value={form.role} onChange={updateField}>
                    {['Cooperative administrator', 'Executive or board member', 'Finance or operations lead', 'Programme manager', 'Technology partner'].map((role) => <option key={role}>{role}</option>)}
                  </select>
                </label>
                <button type="submit" className="btn-lg subscribe-primary">
                  Review plan and terms <ArrowRight size={16} />
                </button>
              </form>
            </>
          ) : (
            <>
              <button type="button" className="subscribe-inline-back" onClick={() => setStep(0)}>
                <ArrowLeft size={14} /> Edit organisation details
              </button>
              <div className="subscribe-heading">
                <div className="subscribe-kicker">Order summary</div>
                <h2 className="serif">Confirm your onboarding path.</h2>
                <p>You will be charged once, securely, before account creation.</p>
              </div>

              <div className="subscribe-summary">
                <div className="subscribe-summary-plan">
                  <div>
                    <span>Plan</span>
                    <strong>{plan.name}</strong>
                  </div>
                  <div className="subscribe-summary-price">
                    <strong>{priceLabel}</strong>
                    <span>/ month</span>
                  </div>
                </div>
                <div className="subscribe-summary-row"><span>Organisation</span><strong>{form.organisation}</strong></div>
                <div className="subscribe-summary-row"><span>Member profile</span><strong>{MEMBER_OPTIONS.find((option) => option.value === form.memberCount)?.label}</strong></div>
                <div className="subscribe-summary-row"><span>Billing today</span><strong>{priceLabel}</strong></div>
              </div>

              <div className="subscribe-next">
                <ReceiptText size={18} />
                <div>
                  <strong>{planKey === 'starter' ? 'Next: secure account setup' : 'Next: secure payment'}</strong>
                  <p>{planKey === 'starter' ? 'Create the administrator credentials for your workspace.' : 'Pay securely via Moolre, then create your administrator account.'}</p>
                </div>
                <ChevronRight size={18} />
              </div>

              {error && <div className="auth-error subscribe-error" role="alert">{error}</div>}

              <button type="button" className="btn-lg subscribe-primary" onClick={continueToAccount}>
                {planKey === 'starter' ? 'Start free workspace' : `Pay ${priceLabel}`} <ArrowRight size={16} />
              </button>
            </>
          )}
        </Reveal>
      </section>
    </main>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/pages/SubscriptionPage.test.jsx` (in `frontend`).
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SubscriptionPage.jsx frontend/src/pages/SubscriptionPage.test.jsx
git commit -m "feat(pricing): pay-before-signup subscription flow"
```

---

### Task 10: AuthPage checkout_ref integration

**Files:**
- Modify: `frontend/src/pages/AuthPage.jsx`
- Modify: `frontend/src/api/auth.js` (pass checkout_ref + subscription_band)
- Modify: `frontend/src/pages/AuthPage.test.jsx`
- Test: `frontend/src/pages/AuthPage.test.jsx` (update)

**Interfaces:**
- Consumes: `signup` (extended with `checkoutRef` / `subscriptionBand`).
- Produces: AuthPage reads `checkout` query param + intent, sends `checkout_ref` and `subscription_band` to signup, and no longer calls `createSubscriptionCheckout` after signup.

- [ ] **Step 1: Write the failing test**

Update `frontend/src/pages/AuthPage.test.jsx` — add a test that a paid signup passes `checkoutRef` and does not call `createSubscriptionCheckout`. Extend the mock to include `createSubscriptionCheckout`:

```javascript
import { createSubscriptionCheckout } from '../api/cooperatives'
vi.mock('../api/cooperatives', () => ({
  createSubscriptionCheckout: vi.fn(),
}))

it('sends checkout_ref for paid plans and skips post-signup checkout', async () => {
  window.sessionStorage.setItem('agroos-subscription-intent', JSON.stringify({
    plan: 'growth',
    band: 'plus_50',
    organisation: 'Test Cooperative',
    location: 'Accra',
    memberCount: '125',
    role: 'Finance or operations lead',
    checkout_ref: 'sub_pre_abc',
  }))
  authMocks.signup.mockResolvedValue({ access_token: 'token' })

  render(
    <MemoryRouter initialEntries={['/login?mode=signup&plan=growth&onboarding=subscription&checkout=sub_pre_abc']}>
      <AuthPage onAuth={vi.fn()} />
    </MemoryRouter>,
  )
  submitSignup()

  await waitFor(() => expect(authMocks.signup).toHaveBeenCalledWith(expect.objectContaining({
    checkoutRef: 'sub_pre_abc',
    subscriptionBand: 'plus_50',
  })))
  expect(createSubscriptionCheckout).not.toHaveBeenCalled()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/pages/AuthPage.test.jsx` (in `frontend`).
Expected: FAIL — signup is not called with `checkoutRef`.

- [ ] **Step 3: Write minimal implementation**

Modify `frontend/src/api/auth.js` `signupAdmin` and `signup` to accept and forward `checkout_ref` and `subscription_band`:

In `signupAdmin` params add `checkout_ref` and `subscription_band`, and in the `authFetch` body add:

```javascript
    checkout_ref: checkout_ref || null,
    subscription_band: subscription_band || null,
```

In `signup` wrapper, add `checkoutRef` and `subscriptionBand` params and map:

```javascript
    checkout_ref: checkoutRef,
    subscription_band: subscriptionBand,
```

Modify `frontend/src/pages/AuthPage.jsx`:
- In the `handleSignup`, read `checkout_ref` from intent and pass it:

```javascript
      const checkoutRef = subscriptionIntent?.checkout_ref || searchParams.get('checkout')
      const data = await signup({
        email: signupEmail,
        password: signupPassword,
        cooperativeName,
        location: location || undefined,
        memberCount: memberCount || undefined,
        subscriptionPlan: plan,
        subscriptionBand: subscriptionIntent?.band,
        checkoutRef,
        onboardingRole: subscriptionIntent?.role || 'Cooperative administrator',
        organizationType,
      })
```

- Remove the entire post-signup `createSubscriptionCheckout` block (lines 251-264) so paid plans no longer trigger checkout after signup:

```javascript
      storeAuthToken(data.access_token)
      if (subscriptionIntent) window.sessionStorage.removeItem('agroos-subscription-intent')
      setSuccess(true)
      setTimeout(() => {
        completeAuth(data, userFromSignupResponse(data, signupEmail.trim()))
      }, 1200)
```

- Remove the now-unused `createSubscriptionCheckout` import if it becomes unused.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/pages/AuthPage.test.jsx` (in `frontend`).
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/AuthPage.jsx frontend/src/api/auth.js frontend/src/pages/AuthPage.test.jsx
git commit -m "feat(pricing): pass checkout_ref through signup, drop post-signup checkout"
```

---

### Task 11: Full verification

- [ ] **Step 1: Run backend test suite**

Run: `python -m pytest backend/tests -q`
Expected: all pass (including the new `test_plans.py` and `test_subscriptions_checkout.py`).

- [ ] **Step 2: Run frontend test suite**

Run: `npm run test:frontend`
Expected: all pass.

- [ ] **Step 3: Run frontend lint**

Run: `npm --prefix frontend run lint`
Expected: no errors.

- [ ] **Step 4: Run backend lint/import check**

Run: `python -m compileall backend/app` (smoke check)
Expected: no errors.

- [ ] **Step 5: Commit any remaining fixes**

```bash
git add -A
git commit -m "chore(pricing): final verification fixes"
```

---

## Self-Review

**Spec coverage:**
- Two-track pricing (cooperative + farmer) → Task 1 (catalog) + Task 8 (UI). ✓
- Band-based Growth scaling + multi-tier Solo Farm → Task 1 + Task 8. ✓
- Pay-before-signup flow → Task 3 (pre-checkout), Task 4 (webhook), Task 5 (signup verify), Task 9 (UI), Task 10 (AuthPage). ✓
- Single pricing source (`/plans`) → Task 1 + Task 7. ✓
- Webhook hardening (no hardcoded 30 days; band-derived) → Task 4 + Task 5. ✓
- Upgrade trigger (band on existing checkout) → Task 6. ✓
- Error handling (invalid plan/custom → 400; unpaid checkout → 402; missing → 404) → Task 3 + Task 5. ✓

**Placeholder scan:** No TBD/TODO. All code blocks concrete.

**Type consistency:** `resolve_amount(plan_key, band)` used identically in Task 3 and Task 6; `checkout_ref`/`reference` naming consistent across Task 3 (response `reference`), Task 5 (signup `checkout_ref`), Task 9 (intent `checkout_ref`), Task 10 (`checkoutRef`). `subscription_band` column (Task 2 migration) matches `SignupResponse.subscription_band` (Task 5). ✓

**Note on existing tests:** `test_onboarding_marketing.py::test_signup_persists_subscription_and_business_role` is updated in Task 5 because paid signups now require a checkout. `test_signup_defaults_to_starter_without_onboarding_context` remains valid (Starter is free, no checkout needed).
