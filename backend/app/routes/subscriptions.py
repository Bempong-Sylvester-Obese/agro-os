from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import Cooperative, User
from app.services.auth_service import enforce_cooperative_scope, get_current_user
from app.services.moolre_service import MoolreService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class CheckoutRequest(BaseModel):
    cooperative_id: int
    plan_key: str


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

    moolre = MoolreService()
    ext_ref = f"sub_upg_{coop.id}_{int(datetime.utcnow().timestamp())}"
    
    user_email = current_user.email if current_user else f"admin@{coop.name.replace(' ', '').lower()}.com"

    # We want the subscription to be paid to the Master Wallet, not the sub-wallet!
    # generate_payment_link without account_number defaults to the Master account.
    result = await moolre.generate_payment_link(
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
