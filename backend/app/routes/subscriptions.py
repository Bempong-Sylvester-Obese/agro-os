from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.models.models import AdminAuditLog, Cooperative, PendingCheckout, User
from app.services import subscription_lifecycle as lifecycle
from app.services.auth_service import enforce_cooperative_scope, get_current_user, require_roles
from app.services.plans import get_band, get_plan, resolve_amount
from app.services.providers.factory import get_payment_provider
from app.services.subscription_service import (
    SubscriptionIntentError,
    create_upgrade_intent,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class CheckoutRequest(BaseModel):
    cooperative_id: int
    plan_key: str
    band: str | None = None


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
    plan = get_plan(req.plan_key)
    band = get_band(req.plan_key, req.band)
    amount = resolve_amount(req.plan_key, req.band)
    if not plan or not band or amount is None:
        raise HTTPException(status_code=400, detail="Plan requires a sales conversation")
    capacity = band.get("capacity")
    if req.member_count is not None and req.member_count <= 0:
        raise HTTPException(status_code=400, detail="Organisation size must be positive")
    if capacity is not None and req.member_count is not None and req.member_count > capacity:
        raise HTTPException(
            status_code=400,
            detail=f"Selected band supports up to {capacity} members or workers",
        )

    plan_key = plan["key"]
    reference = f"sub_pre_{uuid.uuid4().hex}"
    checkout = PendingCheckout(
        reference=reference,
        kind=PendingCheckout.KIND_PRE_CHECKOUT,
        plan_key=plan_key,
        band=band["key"],
        amount=amount,
        organisation=req.organisation,
        location=req.location,
        member_count=req.member_count,
        role=req.role,
        organization_type="solo_farm" if plan["track"] == "farmer" else "cooperative",
    )
    db.add(checkout)
    db.flush()

    settings = get_settings()
    redirect_url = (
        f"{settings.agroos_base_url}/login?mode=signup&plan={plan_key}"
        f"&onboarding=subscription&checkout={reference}"
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
    payment_url = result.get("payment_url")
    if not result.get("success") or not payment_url:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to generate payment link")
    db.commit()

    return {
        "checkout_id": checkout.id,
        "reference": reference,
        "authorization_url": payment_url,
        "amount": amount,
    }


@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Record a single-use upgrade intent and return the provider payment link.

    The intent (plan, band, amount, cooperative) is what the payment webhook
    verifies against and activates from; the reference string carries no plan
    information. Links are non-reusable so one payment maps to one intent.
    """
    enforce_cooperative_scope(current_user, req.cooperative_id)

    coop = db.query(Cooperative).filter(Cooperative.id == req.cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    try:
        intent = create_upgrade_intent(
            db,
            cooperative=coop,
            plan_key=req.plan_key,
            band_key=req.band,
            created_by_user_id=current_user.id if current_user else None,
        )
    except SubscriptionIntentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user_email = (
        current_user.email
        if current_user
        else f"admin@{coop.name.replace(' ', '').lower()}.com"
    )

    provider = get_payment_provider()
    result = await provider.generate_payment_link(
        amount=intent.amount,
        email=user_email,
        currency=intent.currency or "GHS",
        external_ref=intent.reference,
        reusable=False,
    )

    payment_url = result.get("payment_url")
    if not result.get("success") or not payment_url:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to generate payment link")
    db.commit()

    return {
        "intent_id": intent.id,
        "authorization_url": payment_url,
        "reference": intent.reference,
        "plan_key": intent.plan_key,
        "band": intent.band,
        "amount": intent.amount,
    }


# ---------------------------------------------------------------------------
# Lifecycle: status, renewal, cancel, resume
# ---------------------------------------------------------------------------


class CancelRequest(BaseModel):
    cooperative_id: int
    immediately: bool = False


class LifecycleRequest(BaseModel):
    cooperative_id: int


def _scoped_cooperative(db: Session, current_user: User | None, cooperative_id: int) -> Cooperative:
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    return coop


@router.get("/status")
def subscription_status(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Current lifecycle state, with time-based transitions applied first."""
    scoped_id = current_user.cooperative_id if current_user and current_user.cooperative_id else cooperative_id
    if scoped_id is None:
        raise HTTPException(status_code=400, detail="cooperative_id is required")
    coop = _scoped_cooperative(db, current_user, scoped_id)
    lifecycle.reconcile_and_commit(db, coop)
    return lifecycle.describe(coop).as_dict()


@router.post("/renew")
async def renew_subscription(
    req: LifecycleRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
) -> dict[str, Any]:
    """Create a payment intent that renews the cooperative's current paid plan.

    Renewal is the same verified path as an upgrade: the webhook activates
    from the intent and extends the current period (or starts a fresh one if
    it has lapsed). Free-tier and trial cooperatives must pick a plan via
    ``/checkout`` instead.
    """
    coop = _scoped_cooperative(db, current_user, req.cooperative_id)
    lifecycle.reconcile_and_commit(db, coop)
    if lifecycle.is_free_plan(coop.subscription_plan) or coop.subscription_status == lifecycle.STATUS_TRIAL:
        raise HTTPException(status_code=400, detail="No paid plan to renew; choose a plan via checkout")

    try:
        intent = create_upgrade_intent(
            db,
            cooperative=coop,
            plan_key=coop.subscription_plan,
            band_key=coop.subscription_band,
            created_by_user_id=current_user.id if current_user else None,
        )
    except SubscriptionIntentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    provider = get_payment_provider()
    result = await provider.generate_payment_link(
        amount=intent.amount,
        email=current_user.email if current_user else f"admin@{coop.name.replace(' ', '').lower()}.com",
        currency=intent.currency or "GHS",
        external_ref=intent.reference,
        reusable=False,
    )
    payment_url = result.get("payment_url")
    if not result.get("success") or not payment_url:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to generate payment link")
    db.commit()
    return {
        "intent_id": intent.id,
        "authorization_url": payment_url,
        "reference": intent.reference,
        "plan_key": intent.plan_key,
        "band": intent.band,
        "amount": intent.amount,
    }


@router.post("/cancel")
def cancel_subscription(
    req: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
) -> dict[str, Any]:
    """Cancel the paid plan.

    By default access continues until the end of the paid period, after which
    the cooperative drops to the free tier. ``immediately=true`` drops now.
    """
    coop = _scoped_cooperative(db, current_user, req.cooperative_id)
    lifecycle.reconcile_and_commit(db, coop)
    try:
        lifecycle.cancel(coop, immediately=req.immediately)
    except lifecycle.SubscriptionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if current_user:
        db.add(
            AdminAuditLog(
                cooperative_id=coop.id,
                actor_id=str(current_user.id),
                action="subscription.cancelled",
                resource_type="cooperative",
                resource_id=str(coop.id),
                details=f"immediately={req.immediately}",
            )
        )
    db.commit()
    return lifecycle.describe(coop).as_dict()


@router.post("/resume")
def resume_subscription(
    req: LifecycleRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
) -> dict[str, Any]:
    """Undo a pending cancellation while the paid period is still running."""
    coop = _scoped_cooperative(db, current_user, req.cooperative_id)
    lifecycle.reconcile_and_commit(db, coop)
    try:
        lifecycle.resume(coop)
    except lifecycle.SubscriptionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if current_user:
        db.add(
            AdminAuditLog(
                cooperative_id=coop.id,
                actor_id=str(current_user.id),
                action="subscription.resumed",
                resource_type="cooperative",
                resource_id=str(coop.id),
                details=None,
            )
        )
    db.commit()
    return lifecycle.describe(coop).as_dict()
