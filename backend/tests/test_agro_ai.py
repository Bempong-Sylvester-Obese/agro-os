from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.agro_ai.audit import PredictionAuditLogger
from app.agro_ai.evaluation import train_and_evaluate
from app.agro_ai.model import AgroAiCreditModel, save_model_artifact
from app.agro_ai.synthetic_data import DEMO_FARMERS
from app.agro_ai.runtime import create_agro_ai_model, prediction_audit
from app.agro_ai.train import DEFAULT_MODEL_PATH
from main import app


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


def test_prediction_never_approves_more_than_requested() -> None:
    model = AgroAiCreditModel()
    requested_credit_amount = 500
    prediction = model.predict(DEMO_FARMERS[0]["features"], requested_credit_amount)

    assert prediction.approved_credit_limit <= requested_credit_amount


def test_create_agro_ai_model_falls_back_to_default_artifact(tmp_path, monkeypatch) -> None:
    result = train_and_evaluate(row_count=200, test_size=0.25, random_state=42)
    default_artifact = tmp_path / "default-model.joblib"
    save_model_artifact(
        default_artifact,
        result.classifier,
        {"model_version": "default-artifact", "metrics": result.metrics},
    )

    monkeypatch.setenv("AGRO_AI_MODEL_PATH", str(tmp_path / "missing-model.joblib"))
    monkeypatch.setattr("app.agro_ai.runtime.DEFAULT_MODEL_PATH", default_artifact)

    model = create_agro_ai_model()

    assert model.model_version == "default-artifact"
    assert model.artifact_source == str(default_artifact)


def test_credit_summary_handles_empty_assessments(client, cooperative) -> None:
    response = client.get(f"/api/agro-ai/credit-summary?cooperative_id={cooperative['id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_farmers"] == 0
    assert payload["average_score"] == 0.0


def test_get_assessment_rejects_fuzzy_name_lookup(client, farmer, cooperative):
    resp = client.get(
        f"/api/farmers/{farmer['name']}/credit-assessment?cooperative_id={cooperative['id']}"
    )
    assert resp.status_code == 404


def test_health_includes_synthetic_model_metadata(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert "is_synthetic_fallback" in payload
    assert "artifact_source" in payload
    assert "model_ready" in payload


def test_synthetic_model_metadata_flag() -> None:
    synthetic = AgroAiCreditModel()
    assert synthetic.is_synthetic_fallback is True
    assert synthetic.metadata["is_synthetic_fallback"] is True


def test_predict_endpoint_returns_score_and_audits(tmp_path, client, cooperative) -> None:
    original_audit_path = prediction_audit.path
    audit_path = tmp_path / "api_predictions.jsonl"
    prediction_audit.path = audit_path
    try:
        response = client.post(
            "/api/agro-ai/predict",
            json={
                "requested_credit_amount": 3000,
                "farmer_id": DEMO_FARMERS[1]["farmer_id"],
                "cooperative_id": str(cooperative["id"]),
                "actor_id": "admin-demo",
                "features": DEMO_FARMERS[1]["features"],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert 0 <= payload["score"] <= 100
        assert payload["model_version"].startswith("agro-ai")
        assert payload["farmer_id"] == DEMO_FARMERS[1]["farmer_id"]
        assert payload["cooperative_id"] == str(cooperative["id"])

        saved = json.loads(audit_path.read_text(encoding="utf-8"))
        assert saved["context"]["source"] == "ad_hoc_prediction"
        assert saved["context"]["cooperative_id"] == str(cooperative["id"])
        assert saved["context"]["actor_id"] == "admin-demo"
        assert saved["requested_credit_amount"] == 3000
    finally:
        prediction_audit.path = original_audit_path
