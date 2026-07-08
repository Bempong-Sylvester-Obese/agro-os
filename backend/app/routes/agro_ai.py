"""Agro-AI credit scoring routes for the cooperative dashboard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agro_ai.db_bridge import get_assessment_from_db, list_assessments_from_db
from app.agro_ai.runtime import agro_ai, prediction_audit
from app.database.db import get_db

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


def _list_assessments(db: Session) -> list[dict[str, Any]]:
    db_assessments = list_assessments_from_db(db, agro_ai)
    if db_assessments is not None:
        return db_assessments
    return agro_ai.list_farmer_assessments()


@router.get("/api/farmers")
def list_farmer_assessments(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return _list_assessments(db)


@router.get("/api/farmers/{farmer_id}/credit-assessment")
def get_credit_assessment(farmer_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    assessment = get_assessment_from_db(farmer_id, db, agro_ai)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Farmer not found")
    prediction_audit.log_prediction(
        features=assessment["features"],
        prediction=agro_ai.predict(assessment["features"], assessment["requested_credit_amount"]),
        requested_credit_amount=assessment["requested_credit_amount"],
        context={"source": "farmer_assessment", "farmer_id": farmer_id},
        db=db,
    )
    return assessment


@router.get("/api/agro-ai/credit-summary")
def get_credit_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    assessments = _list_assessments(db)
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
        "data_source": "database" if list_assessments_from_db(db, agro_ai) is not None else "synthetic",
    }


@router.post("/api/agro-ai/predict")
def predict_creditworthiness(payload: PredictionRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
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
            "cooperative_id": payload.cooperative_id,
            "actor_id": payload.actor_id,
        },
        db=db,
    )
    return {
        "requested_credit_amount": payload.requested_credit_amount,
        "farmer_id": payload.farmer_id,
        "cooperative_id": payload.cooperative_id,
        "features": payload.features.model_dump(),
        **prediction.__dict__,
    }
