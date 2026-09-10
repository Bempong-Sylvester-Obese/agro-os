"""Resolve cooperative scope for list endpoints."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException

from app.config import Settings, get_settings
from app.models.models import User
from app.services.auth_service import get_current_user


@dataclass(frozen=True)
class CooperativeScope:
    cooperative_id: int


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


def require_cooperative_scope(
    current_user: User | None = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> CooperativeScope | None:
    """Fail-closed dependency that enforces cooperative scoping at the API layer.

    Extracts the cooperative_id from the authenticated user's JWT.
    Raises HTTP 403 if the user has no cooperative assignment.
    Returns None when auth is disabled (local-dev/test mode).
    """
    if not settings.auth_enabled:
        return None
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not current_user.cooperative_id:
        raise HTTPException(
            status_code=403,
            detail="User is not assigned to a cooperative",
        )
    return CooperativeScope(cooperative_id=current_user.cooperative_id)
