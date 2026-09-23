"""Organisation-type write guards (#254, #256).

Workers, tasks, and labor attendance are solo-farm modules. Cooperative
workspaces keep members, meeting attendance, dues, and commerce.
"""

from fastapi import HTTPException, status

from app.models.models import Cooperative

SOLO_FARM_ONLY = (
    "This action is only available on a solo farm. "
    "Cooperative members live under Members."
)
WORKER_SOLO_FARM_ONLY = (
    "Workers can only be managed on a solo farm. Cooperative members live under Members."
)


def require_solo_farm(
    coop: Cooperative | None,
    *,
    detail: str = SOLO_FARM_ONLY,
) -> Cooperative:
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    if (coop.organization_type or "cooperative") != "solo_farm":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return coop
