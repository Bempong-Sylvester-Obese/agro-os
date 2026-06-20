from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.agro_ai.audit import PredictionAuditLogger
from app.agro_ai.evaluation import train_and_evaluate
from app.agro_ai.model import AgroAiCreditModel, save_model_artifact
from app.agro_ai.synthetic_data import DEMO_FARMERS
from app.main import app, prediction_audit


def test_train_and_evaluate_returns_enterprise_metrics() -> None:
    result = train_and_evaluate(row_count=200, test_size=0.25, random_state=42)

    for metric_name in ("roc_auc", "pr_auc", "brier_score", "threshold_68_false_approval_rate"):
        assert metric_name in result.metrics

    assert result.dataset["source"] == "synthetic"
    assert result.dataset["train_rows"] == 150
    assert result.dataset["test_rows"] == 50
    assert len(result.confusion_matrix) == 2
    assert set(result.feature_importances) >= {"dues_payment_rate", "yield_performance", "savings_rate"}


def test_model_artifact_round_trip(tmp_path) -> None:
    result = train_and_evaluate(row_count=200, test_size=0.25, random_state=42)
    artifact_path = tmp_path / "agro-ai.joblib"

    save_model_artifact(
        artifact_path,
        result.classifier,
        {"model_version": "test-model", "metrics": result.metrics},
    )

    model = AgroAiCreditModel.from_artifact(artifact_path)
    prediction = model.predict(DEMO_FARMERS[0]["features"], DEMO_FARMERS[0]["requested_credit_amount"])

    assert model.model_version == "test-model"
    assert model.artifact_source == str(artifact_path)
    assert prediction.model_version == "test-model"
    assert 0 <= prediction.score <= 100


def test_prediction_audit_logger_writes_jsonl(tmp_path) -> None:
    logger = PredictionAuditLogger(tmp_path / "predictions.jsonl")
    model = AgroAiCreditModel()
    prediction = model.predict(DEMO_FARMERS[0]["features"], DEMO_FARMERS[0]["requested_credit_amount"])

    record = logger.log_prediction(
        features=DEMO_FARMERS[0]["features"],
        prediction=prediction,
        requested_credit_amount=DEMO_FARMERS[0]["requested_credit_amount"],
        context={"source": "unit_test", "farmer_id": DEMO_FARMERS[0]["farmer_id"]},
    )

    saved = json.loads((tmp_path / "predictions.jsonl").read_text(encoding="utf-8"))
    assert saved["event_id"] == record["event_id"]
    assert saved["context"]["farmer_id"] == DEMO_FARMERS[0]["farmer_id"]
    assert saved["prediction"]["model_version"] == prediction.model_version


def test_predict_endpoint_returns_score_and_audits(tmp_path) -> None:
    prediction_audit.path = tmp_path / "api_predictions.jsonl"
    client = TestClient(app)

    response = client.post(
        "/api/agro-ai/predict",
        json={
            "requested_credit_amount": 3000,
            "farmer_id": DEMO_FARMERS[1]["farmer_id"],
            "cooperative_id": "coop-demo",
            "actor_id": "admin-demo",
            "features": DEMO_FARMERS[1]["features"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert 0 <= payload["score"] <= 100
    assert payload["model_version"].startswith("agro-ai")
    assert payload["farmer_id"] == DEMO_FARMERS[1]["farmer_id"]
    assert payload["cooperative_id"] == "coop-demo"

    saved = json.loads((tmp_path / "api_predictions.jsonl").read_text(encoding="utf-8"))
    assert saved["context"]["source"] == "ad_hoc_prediction"
    assert saved["context"]["cooperative_id"] == "coop-demo"
    assert saved["context"]["actor_id"] == "admin-demo"
    assert saved["requested_credit_amount"] == 3000
