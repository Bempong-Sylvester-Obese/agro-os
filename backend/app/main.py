"""FastAPI entrypoint for AgroOS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agro_ai.audit import PredictionAuditLogger
from app.agro_ai.model import AgroAiCreditModel
from app.agro_ai.train import DEFAULT_MODEL_PATH

app = FastAPI(
    title="AgroOS API",
    description="Hackathon API for farmer cooperative operations and agro-ai credit scoring.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_agro_ai_model() -> AgroAiCreditModel:
    configured_model_path = os.getenv("AGRO_AI_MODEL_PATH")
    candidate_paths: list[Path] = []
    if configured_model_path:
        resolved_path = _resolve_path(configured_model_path)
        if resolved_path:
            candidate_paths.append(resolved_path)
    if DEFAULT_MODEL_PATH not in candidate_paths:
        candidate_paths.append(DEFAULT_MODEL_PATH)

    for candidate_path in candidate_paths:
        if candidate_path and candidate_path.exists():
            return AgroAiCreditModel.from_artifact(candidate_path)

    return AgroAiCreditModel()


def _resolve_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None

    path = Path(raw_path)
    if path.is_absolute():
        return path

    backend_root = Path(__file__).resolve().parents[1]
    repo_root = backend_root.parent
    if path.parts and path.parts[0] == "backend":
        return repo_root / path

    return backend_root / path


agro_ai = create_agro_ai_model()

prediction_audit = PredictionAuditLogger()


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", **agro_ai.metadata}


@app.get("/api/farmers")
def list_farmers() -> list[dict[str, Any]]:
    return agro_ai.list_farmer_assessments()


@app.get("/api/farmers/{farmer_id}/credit-assessment")
def get_credit_assessment(farmer_id: str) -> dict[str, Any]:
    assessment = agro_ai.get_farmer_assessment(farmer_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Farmer not found")
    prediction_audit.log_prediction(
        features=assessment["features"],
        prediction=agro_ai.predict(assessment["features"], assessment["requested_credit_amount"]),
        requested_credit_amount=assessment["requested_credit_amount"],
        context={"source": "farmer_assessment", "farmer_id": farmer_id},
    )
    return assessment


@app.get("/api/agro-ai/credit-summary")
def get_credit_summary() -> dict[str, Any]:
    assessments = agro_ai.list_farmer_assessments()
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


@app.post("/api/agro-ai/predict")
def predict_creditworthiness(payload: PredictionRequest) -> dict[str, Any]:
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
    )
    return {
        "requested_credit_amount": payload.requested_credit_amount,
        "farmer_id": payload.farmer_id,
        "cooperative_id": payload.cooperative_id,
        "features": payload.features.model_dump(),
        **prediction.__dict__,
    }
