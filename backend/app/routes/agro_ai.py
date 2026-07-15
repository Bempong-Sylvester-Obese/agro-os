"""Agro-AI credit scoring routes for the cooperative dashboard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agro_ai.db_bridge import get_assessment_from_db, list_assessments_from_db
from app.agro_ai.runtime import agro_ai, prediction_audit
from app.config import get_settings
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import User
from app.services.auth_service import get_current_user

router = APIRouter(tags=["agro-ai"])


class FarmerFeatures(BaseModel):
    dues_payment_rate: float = Field(ge=0, le=1)
    on_time_payment_rate: float = Field(ge=0, le=1)
    yield_performance: float = Field(ge=0, le=1)
    attendance_rate: float = Field(ge=0, le=1)
    acreage: float = Field(ge=0)
    cooperative_tenure_months: int = Field(ge=0)
    prior_loans_repaid: int = Field(ge=0)
    outstanding_balance_ratio: float = Field(ge=0, le=1)
    savings_rate: float = Field(ge=0, le=1)


class PredictionRequest(BaseModel):
    features: FarmerFeatures
    requested_credit_amount: int = Field(default=3000, ge=0)
    farmer_id: str | None = None
    cooperative_id: str | None = None
    actor_id: str | None = None


@router.get("/api/farmers")
def list_farmer_assessments(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    scoped_id = resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=cooperative_id,
        settings=get_settings(),
    )
    return list_assessments_from_db(db, agro_ai, cooperative_id=scoped_id)


@router.get("/api/farmers/{farmer_id}/credit-assessment")
def get_credit_assessment(
    farmer_id: str,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    scoped_id = resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=cooperative_id,
        settings=get_settings(),
    )
    assessment = get_assessment_from_db(
        farmer_id,
        db,
        agro_ai,
        cooperative_id=scoped_id,
    )
    if assessment is None:
        raise HTTPException(status_code=404, detail="Farmer not found")
    prediction_audit.log_prediction(
        features=assessment["features"],
        prediction=agro_ai.predict(assessment["features"], assessment["requested_credit_amount"]),
        requested_credit_amount=assessment["requested_credit_amount"],
        context={
            "source": "farmer_assessment",
            "farmer_id": farmer_id,
            "cooperative_id": str(scoped_id),
            "actor_id": str(current_user.id) if current_user else None,
        },
        db=db,
    )
    return assessment


@router.get("/api/agro-ai/credit-summary")
def get_credit_summary(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    scoped_id = resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=cooperative_id,
        settings=get_settings(),
    )
    assessments = list_assessments_from_db(db, agro_ai, cooperative_id=scoped_id)
    eligible_count = sum(1 for item in assessments if item["eligible"])
    high_risk_count = sum(1 for item in assessments if item["risk_band"] == "High risk")
    review_count = sum(1 for item in assessments if item["risk_band"] == "Watchlist")
    average_score = (
        round(sum(item["score"] for item in assessments) / len(assessments), 1)
        if assessments
        else 0.0
    )

    return {
        "model_version": agro_ai.model_version,
        "feature_schema_version": agro_ai.metadata["feature_schema_version"],
        "total_farmers": len(assessments),
        "eligible_count": eligible_count,
        "manual_review_count": review_count,
        "high_risk_count": high_risk_count,
        "average_score": average_score,
    }


@router.post("/api/agro-ai/predict")
def predict_creditworthiness(
    payload: PredictionRequest,
    current_user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    requested_cooperative_id = None
    if payload.cooperative_id:
        try:
            requested_cooperative_id = int(payload.cooperative_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid cooperative_id") from exc
    scoped_id = resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=requested_cooperative_id,
        settings=get_settings(),
    )
    prediction = agro_ai.predict(
        payload.features.model_dump(),
        requested_credit_amount=payload.requested_credit_amount,
    )
    prediction_audit.log_prediction(
        features=payload.features.model_dump(),
        prediction=prediction,
        requested_credit_amount=payload.requested_credit_amount,
        context={
            "source": "ad_hoc_prediction",
            "farmer_id": payload.farmer_id,
            "cooperative_id": (
                str(scoped_id)
            ),
            "actor_id": str(current_user.id) if current_user is not None else payload.actor_id,
        },
        db=db,
    )
    return {
        "requested_credit_amount": payload.requested_credit_amount,
        "farmer_id": payload.farmer_id,
        "cooperative_id": (
            str(scoped_id)
        ),
        "features": payload.features.model_dump(),
        **prediction.__dict__,
    }
