from datetime import datetime
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.models.models import Cooperative, PendingCheckout, User
from app.plans import resolve_amount
from app.services.auth_service import enforce_cooperative_scope, get_current_user
from app.services.providers.factory import get_payment_provider

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class CheckoutRequest(BaseModel):
    cooperative_id: int
    plan_key: str


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

    plan_prices = {
        "growth": 299.0,
    }

    amount = plan_prices.get(req.plan_key.lower())
    if not amount:
        raise HTTPException(status_code=400, detail="Invalid paid plan selected")

    provider = get_payment_provider()
    ext_ref = f"sub_upg_{coop.id}_{int(datetime.utcnow().timestamp())}"
    
    user_email = current_user.email if current_user else f"admin@{coop.name.replace(' ', '').lower()}.com"

    # We want the subscription to be paid to the Master Wallet, not the sub-wallet!
    # generate_payment_link without account_number defaults to the Master account.
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
