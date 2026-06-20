"""Training and evaluation helpers for Agro-AI experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from app.agro_ai.model import build_classifier, vectorize_features
from app.agro_ai.synthetic_data import FEATURE_NAMES, generate_training_rows


@dataclass(frozen=True)
class EvaluationResult:
    classifier: Any
    metrics: dict[str, float]
    confusion_matrix: list[list[int]]
    feature_importances: dict[str, float]
    dataset: dict[str, int | float | str]


def train_and_evaluate(
    *,
    row_count: int = 720,
    test_size: float = 0.25,
    random_state: int = 42,
    model_overrides: dict[str, Any] | None = None,
) -> EvaluationResult:
    """Train on synthetic rows and evaluate on a deterministic holdout split."""

    rows = generate_training_rows(row_count)
    features = [vectorize_features(row["features"]) for row in rows]
    labels = [int(row["eligible"]) for row in rows]

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=test_size,
        random_state=random_state,
        stratify=labels,
    )

    classifier = build_classifier(**(model_overrides or {}))
    classifier.fit(x_train, y_train)
    probabilities = classifier.predict_proba(x_test)[:, 1]
    predictions = [int(probability >= 0.68) for probability in probabilities]

    metrics = {
        "accuracy": accuracy_score(y_test, predictions),
        "precision": precision_score(y_test, predictions, zero_division=0),
        "recall": recall_score(y_test, predictions, zero_division=0),
        "f1": f1_score(y_test, predictions, zero_division=0),
        "roc_auc": roc_auc_score(y_test, probabilities),
        "pr_auc": average_precision_score(y_test, probabilities),
        "brier_score": brier_score_loss(y_test, probabilities),
        "approval_rate": sum(predictions) / len(predictions),
        "manual_review_rate": _manual_review_rate(probabilities),
        **_threshold_metrics(y_test, probabilities),
    }

    return EvaluationResult(
        classifier=classifier,
        metrics={name: round(float(value), 4) for name, value in metrics.items()},
        confusion_matrix=confusion_matrix(y_test, predictions).astype(int).tolist(),
        feature_importances=_feature_importances(classifier),
        dataset={
            "source": "synthetic",
            "row_count": row_count,
            "train_rows": len(x_train),
            "test_rows": len(x_test),
            "test_size": test_size,
            "random_state": random_state,
            "positive_label_rate": round(sum(labels) / len(labels), 4),
        },
    )


def _manual_review_rate(probabilities: list[float]) -> float:
    scores = [probability * 100 for probability in probabilities]
    return sum(55 <= score < 68 for score in scores) / len(scores)


def _threshold_metrics(y_true: list[int], probabilities: list[float]) -> dict[str, float]:
    metrics: dict[str, float] = {}

    for threshold in (55, 68, 82):
        approved = [int(probability * 100 >= threshold) for probability in probabilities]
        false_approvals = sum(prediction == 1 and actual == 0 for prediction, actual in zip(approved, y_true))
        false_rejections = sum(prediction == 0 and actual == 1 for prediction, actual in zip(approved, y_true))
        actual_negatives = sum(actual == 0 for actual in y_true) or 1
        actual_positives = sum(actual == 1 for actual in y_true) or 1

        metrics[f"threshold_{threshold}_approval_rate"] = sum(approved) / len(approved)
        metrics[f"threshold_{threshold}_false_approval_rate"] = false_approvals / actual_negatives
        metrics[f"threshold_{threshold}_false_rejection_rate"] = false_rejections / actual_positives

    return metrics


def _feature_importances(classifier: Any) -> dict[str, float]:
    importances = getattr(classifier, "feature_importances_", [])
    return {
        feature_name: round(float(importance), 4)
        for feature_name, importance in zip(FEATURE_NAMES, importances)
    }
