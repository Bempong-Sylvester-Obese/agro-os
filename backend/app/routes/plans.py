"""Public pricing catalog endpoint."""

from fastapi import APIRouter

from app.plans import PLANS

router = APIRouter(tags=["plans"])


@router.get("/plans")
def list_plans() -> dict:
    return {"plans": list(PLANS.values())}
