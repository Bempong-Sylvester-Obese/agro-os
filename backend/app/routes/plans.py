"""Public pricing catalog endpoint."""

from fastapi import APIRouter

from app.services.plans import PLANS

router = APIRouter(tags=["plans"])


@router.get("/plans")
def list_plans() -> dict:
    plans = [
        {
            **plan,
            "price": plan["display_price"],
        }
        for plan in PLANS.values()
    ]
    return {"plans": plans}
