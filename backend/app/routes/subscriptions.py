from datetime import datetime
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.models.models import Cooperative, PendingCheckout, User
from app.services.auth_service import enforce_cooperative_scope, get_current_user
from app.services.plans import get_band, get_plan, resolve_amount
from app.services.providers.factory import get_payment_provider

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
    """Generate a Moolre payment link for subscription upgrade."""
    enforce_cooperative_scope(current_user, req.cooperative_id)

    coop = db.query(Cooperative).filter(Cooperative.id == req.cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    plan = get_plan(req.plan_key)
    band = get_band(req.plan_key, req.band)
    amount = resolve_amount(req.plan_key, req.band)
    if not plan or not band or amount is None:
        raise HTTPException(status_code=400, detail="Invalid paid plan selected")
    plan_key = plan["key"]

    provider = get_payment_provider()
    ext_ref = (
        f"sub_upg_{coop.id}_{plan['key']}_{int(datetime.utcnow().timestamp())}"
        f"_{band['key']}"
    )

    user_email = (
        current_user.email
        if current_user
        else f"admin@{coop.name.replace(' ', '').lower()}.com"
    )

    result = await provider.generate_payment_link(
        amount=amount,
        email=user_email,
        currency=coop.currency or "GHS",
        external_ref=ext_ref,
        reusable=True,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail="Failed to generate payment link")

    return {
        "authorization_url": result.get("payment_url"),
        "reference": result.get("reference"),
    }
