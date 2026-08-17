from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import Cooperative, User
from app.services.auth_service import enforce_cooperative_scope, get_current_user
from app.services.plans import get_plan
from app.services.providers.factory import get_payment_provider

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

    plan_key = req.plan_key.lower()
    plan = get_plan(plan_key)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid paid plan selected")
    price = plan["price"]
    if price <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Plan '{plan_key}' requires custom pricing",
        )

    provider = get_payment_provider()
    ext_ref = f"sub_upg_{coop.id}_{plan_key}_{int(datetime.utcnow().timestamp())}"

    user_email = (
        current_user.email
        if current_user
        else f"admin@{coop.name.replace(' ', '').lower()}.com"
    )

    result = await provider.generate_payment_link(
        amount=price,
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
