"""Random forest model wrapper for Agro-AI credit assessments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
from sklearn.ensemble import RandomForestClassifier

from app.agro_ai.synthetic_data import DEMO_FARMERS, FEATURE_NAMES, generate_training_rows

MODEL_VERSION = "agro-ai-rf-v1"
FEATURE_SCHEMA_VERSION = "agro-ai-features-v1"
SYNTHETIC_ARTIFACT_SOURCE = "startup-trained-synthetic"
MODEL_PARAMS = {
    "n_estimators": 160,
    "max_depth": 7,
    "min_samples_leaf": 4,
    "random_state": 42,
    "class_weight": "balanced",
}


@dataclass(frozen=True)
class Prediction:
    score: int
    confidence: int
    eligible: bool
    risk_band: str
    recommendation: str
    approved_credit_limit: int
    top_reasons: list[str]
    model_version: str = MODEL_VERSION


def vectorize_features(features: dict[str, float]) -> list[float]:
    """Return features in the exact order expected by the trained model."""

    return [float(features[name]) for name in FEATURE_NAMES]


def build_classifier(**overrides: Any) -> RandomForestClassifier:
    """Create the default Agro-AI classifier with optional experiment overrides."""

    return RandomForestClassifier(**{**MODEL_PARAMS, **overrides})


def train_classifier(training_rows: list[dict[str, Any]] | None = None) -> RandomForestClassifier:
    """Train a classifier from rows that contain `features` and `eligible` labels."""

    rows = generate_training_rows() if training_rows is None else training_rows
    if not rows:
        raise ValueError("training_rows must contain at least one row")
    feature_matrix = [vectorize_features(row["features"]) for row in rows]
    labels = [row["eligible"] for row in rows]
    classifier = build_classifier()
    classifier.fit(feature_matrix, labels)
    return classifier


def save_model_artifact(path: str | Path, classifier: RandomForestClassifier, metadata: dict[str, Any]) -> Path:
    """Persist a model plus metadata for reproducible FastAPI startup."""

    artifact_path = Path(path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "classifier": classifier,
            "feature_names": FEATURE_NAMES,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "model_version": metadata.get("model_version", MODEL_VERSION),
            "metadata": metadata,
        },
        artifact_path,
    )
    return artifact_path


def load_model_artifact(path: str | Path) -> dict[str, Any]:
    """Load and validate a serialized Agro-AI model artifact."""

    artifact = joblib.load(Path(path))
    missing_keys = {"classifier", "feature_names", "model_version"} - set(artifact)
    if missing_keys:
        raise ValueError(f"Model artifact is missing required keys: {', '.join(sorted(missing_keys))}")

    if list(artifact["feature_names"]) != FEATURE_NAMES:
        raise ValueError("Model artifact feature order does not match the current feature schema")

    return artifact


class AgroAiCreditModel:
    """Credit scoring wrapper around a versioned RandomForestClassifier."""

    def __init__(
        self,
        classifier: RandomForestClassifier | None = None,
        *,
        model_version: str = MODEL_VERSION,
        artifact_source: str = SYNTHETIC_ARTIFACT_SOURCE,
    ) -> None:
        self.classifier = classifier or train_classifier()
        self.model_version = model_version
        self.artifact_source = artifact_source

    @classmethod
    def from_artifact(cls, path: str | Path) -> "AgroAiCreditModel":
        artifact = load_model_artifact(path)
        return cls(
            artifact["classifier"],
            model_version=artifact["model_version"],
            artifact_source=str(Path(path)),
        )

    @property
    def is_synthetic_fallback(self) -> bool:
        return self.artifact_source == SYNTHETIC_ARTIFACT_SOURCE

    @property
    def metadata(self) -> dict[str, str | bool]:
        return {
            "model_version": self.model_version,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "artifact_source": self.artifact_source,
            "is_synthetic_fallback": self.is_synthetic_fallback,
        }

    def list_farmer_assessments(self) -> list[dict[str, Any]]:
        return [self.assess_farmer(farmer) for farmer in DEMO_FARMERS]

    def get_farmer_assessment(self, farmer_id: str) -> dict[str, Any] | None:
        for farmer in DEMO_FARMERS:
            if farmer["farmer_id"] == farmer_id:
                return self.assess_farmer(farmer)
        return None

    def assess_farmer(self, farmer: dict[str, Any]) -> dict[str, Any]:
        prediction = self.predict(farmer["features"], farmer["requested_credit_amount"])
        return {
            "farmer_id": farmer["farmer_id"],
            "name": farmer["name"],
            "phone": farmer["phone"],
            "region": farmer["region"],
            "crop": farmer["crop"],
            "dues_status": farmer["dues_status"],
            "requested_credit_amount": farmer["requested_credit_amount"],
            "previous_score": farmer["previous_score"],
            "features": farmer["features"],
            **prediction.__dict__,
        }

    def predict(self, features: dict[str, float], requested_credit_amount: int = 3000) -> Prediction:
        probability = self.classifier.predict_proba([self._vector(features)])[0][1]
        score = int(round(probability * 100))
        confidence = int(round(abs(probability - 0.5) * 200))
        eligible = score >= 68
        risk_band = self._risk_band(score)
        recommendation = self._recommendation(score)
        credit_limit_factor = 0.45 + (score / 100)
        approved_credit_limit = int(round(requested_credit_amount * credit_limit_factor / 50) * 50)
        approved_credit_limit = min(approved_credit_limit, requested_credit_amount)

        if not eligible:
            approved_credit_limit = min(approved_credit_limit, int(requested_credit_amount * 0.55))

        return Prediction(
            score=score,
            confidence=confidence,
            eligible=eligible,
            risk_band=risk_band,
            recommendation=recommendation,
            approved_credit_limit=approved_credit_limit,
            top_reasons=self._explain(features),
            model_version=self.model_version,
        )

    def _vector(self, features: dict[str, float]) -> list[float]:
        return vectorize_features(features)

    def _risk_band(self, score: int) -> str:
        if score >= 82:
            return "Low risk"
        if score >= 68:
            return "Moderate risk"
        if score >= 55:
            return "Watchlist"
        return "High risk"

    def _recommendation(self, score: int) -> str:
        if score >= 82:
            return "Approve full input credit"
        if score >= 68:
            return "Approve with standard monitoring"
        if score >= 55:
            return "Review manually before approval"
        return "Defer credit and require dues recovery"

    def _explain(self, features: dict[str, float]) -> list[str]:
        reason_pool = [
            (
                features["dues_payment_rate"],
                "Strong dues consistency improves repayment confidence",
                "Weak dues consistency is the main repayment concern",
            ),
            (
                features["on_time_payment_rate"],
                "On-time payments show reliable cooperative behavior",
                "Late payments reduce the model confidence",
            ),
            (
                features["yield_performance"],
                "Harvest performance supports productive capacity",
                "Yield performance is below the cooperative benchmark",
            ),
            (
                features["attendance_rate"],
                "Regular attendance signals cooperative engagement",
                "Low attendance limits training and repayment visibility",
            ),
            (
                1 - features["outstanding_balance_ratio"],
                "Low outstanding balance leaves room for new credit",
                "Outstanding balance is high for a new facility",
            ),
            (
                features["savings_rate"],
                "Savings behavior adds a repayment buffer",
                "Savings history is still thin",
            ),
        ]

        ranked = sorted(reason_pool, key=lambda item: abs(item[0] - 0.62), reverse=True)
        reasons: list[str] = []
        for value, positive, negative in ranked:
            reasons.append(positive if value >= 0.62 else negative)
            if len(reasons) == 3:
                break

        return reasons
