"""Prediction audit logging for Agro-AI decisions."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.agro_ai.model import FEATURE_SCHEMA_VERSION, Prediction

DEFAULT_AUDIT_LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "agro_ai_predictions.jsonl"


class PredictionAuditLogger:
    """Append local JSONL audit records until Supabase persistence is available."""

    def __init__(self, path: str | Path | None = None) -> None:
        configured_path = path or os.getenv("AGRO_AI_AUDIT_LOG_PATH") or DEFAULT_AUDIT_LOG_PATH
        self.path = Path(configured_path)

    def log_prediction(
        self,
        *,
        features: dict[str, float],
        prediction: Prediction,
        requested_credit_amount: int,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "model_version": prediction.model_version,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "requested_credit_amount": requested_credit_amount,
            "features": features,
            "prediction": asdict(prediction),
            "context": context or {},
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(record, sort_keys=True) + "\n")

        return record
