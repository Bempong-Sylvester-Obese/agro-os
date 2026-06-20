"""CLI for training Agro-AI models and logging W&B experiments."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from app.agro_ai.evaluation import EvaluationResult, train_and_evaluate
from app.agro_ai.model import FEATURE_SCHEMA_VERSION, MODEL_PARAMS, MODEL_VERSION, save_model_artifact

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
DEFAULT_MODEL_PATH = BACKEND_ROOT / "model_artifacts" / f"{MODEL_VERSION}.joblib"


def main() -> None:
    args = parse_args()
    result = train_and_evaluate(
        row_count=args.rows,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    metadata = {
        "model_version": MODEL_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "model_params": MODEL_PARAMS,
        "dataset": result.dataset,
        "metrics": result.metrics,
        "confusion_matrix": result.confusion_matrix,
        "feature_importances": result.feature_importances,
    }
    artifact_path = save_model_artifact(args.model_output, result.classifier, metadata)
    wandb_status = log_to_wandb(
        result,
        artifact_path=artifact_path,
        project=args.wandb_project,
        entity=args.wandb_entity,
        mode=args.wandb_mode,
        disabled=args.disable_wandb,
    )

    print(f"Saved model artifact: {artifact_path}")
    print(f"Metrics: {result.metrics}")
    print(f"W&B: {wandb_status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and evaluate the Agro-AI credit model.")
    parser.add_argument("--rows", type=int, default=720, help="Synthetic rows to generate for this run.")
    parser.add_argument("--test-size", type=float, default=0.25, help="Holdout share used for evaluation.")
    parser.add_argument("--random-state", type=int, default=42, help="Deterministic split seed.")
    parser.add_argument(
        "--model-output",
        type=Path,
        default=default_model_output(),
        help="Where to write the serialized model artifact.",
    )
    parser.add_argument(
        "--wandb-project",
        default=os.getenv("WANDB_PROJECT", "agro-os"),
        help="W&B project name.",
    )
    parser.add_argument("--wandb-entity", default=os.getenv("WANDB_ENTITY"), help="Optional W&B entity/team.")
    parser.add_argument(
        "--wandb-mode",
        default=os.getenv("WANDB_MODE", "offline"),
        choices=("online", "offline", "disabled"),
        help="Use `online` after `wandb login`; offline works without credentials.",
    )
    parser.add_argument("--disable-wandb", action="store_true", help="Skip W&B logging entirely.")
    return parser.parse_args()


def default_model_output() -> Path:
    configured_path = os.getenv("AGRO_AI_MODEL_PATH")
    if not configured_path:
        return DEFAULT_MODEL_PATH

    path = Path(configured_path)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "backend":
        return REPO_ROOT / path
    return BACKEND_ROOT / path


def log_to_wandb(
    result: EvaluationResult,
    *,
    artifact_path: Path,
    project: str,
    entity: str | None,
    mode: str,
    disabled: bool,
) -> str:
    """Log a run to W&B, returning a status string that is safe for CLI output."""

    if disabled or mode == "disabled":
        return "disabled"

    try:
        import wandb
    except ImportError:
        return "wandb package is not installed"

    try:
        run = wandb.init(
            project=project,
            entity=entity,
            mode=mode,
            config={
                "model_version": MODEL_VERSION,
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "model_params": MODEL_PARAMS,
                "dataset": result.dataset,
            },
        )
        run.log(
            {
                **result.metrics,
                "confusion_matrix": result.confusion_matrix,
                "feature_importances": result.feature_importances,
            }
        )

        artifact = wandb.Artifact(
            name=MODEL_VERSION,
            type="model",
            metadata={
                "metrics": result.metrics,
                "dataset": result.dataset,
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
            },
        )
        artifact.add_file(str(artifact_path))
        run.log_artifact(artifact)
        run.finish()
        return "logged" if mode == "online" else "logged offline"
    except Exception as exc:  # W&B should not make local training fail.
        return f"skipped after W&B error: {exc}"


if __name__ == "__main__":
    main()
