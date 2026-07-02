"""Agro-AI runtime singletons used by API routes and tests."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from app.agro_ai.audit import PredictionAuditLogger
from app.agro_ai.model import AgroAiCreditModel, SYNTHETIC_ARTIFACT_SOURCE
from app.agro_ai.train import DEFAULT_MODEL_PATH
from app.config import get_settings

logger = logging.getLogger(__name__)


def _resolve_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None

    path = Path(raw_path)
    if path.is_absolute():
        return path

    backend_root = Path(__file__).resolve().parents[2]
    repo_root = backend_root.parent
    if path.parts and path.parts[0] == "backend":
        return repo_root / path

    return backend_root / path


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

    settings = get_settings()
    if settings.app_env not in {"development", "test"}:
        logger.warning(
            "Agro-AI model artifact not found; using in-memory synthetic fallback "
            "(artifact_source=%s, app_env=%s)",
            SYNTHETIC_ARTIFACT_SOURCE,
            settings.app_env,
        )

    return AgroAiCreditModel()


agro_ai = create_agro_ai_model()
prediction_audit = PredictionAuditLogger()
