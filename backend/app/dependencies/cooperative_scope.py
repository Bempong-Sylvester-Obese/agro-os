"""Resolve cooperative scope for list endpoints."""

from fastapi import HTTPException

from app.config import Settings
from app.models.models import User


def resolve_cooperative_scope(
    *,
    current_user: User | None,
    cooperative_id: int | None,
    settings: Settings,
) -> int:
    """Return the cooperative ID callers must be scoped to."""
    if current_user and current_user.cooperative_id:
        return current_user.cooperative_id
    if cooperative_id is not None:
        return cooperative_id
    if settings.auth_enabled:
        raise HTTPException(status_code=401, detail="Authentication required")
    raise HTTPException(status_code=400, detail="cooperative_id is required")
