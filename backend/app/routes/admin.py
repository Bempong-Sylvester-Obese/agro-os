"""Administrator-only operational controls."""

import json
import uuid
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.database.demo_constants import DEMO_COOPERATIVE_NAME
from app.database.purge_demo import reset_demo_workspace
from app.models.models import (
    AdminActionConfirmation,
    AdminAuditLog,
    Cooperative,
    User,
)
from app.services.auth_service import ALGORITHM, require_roles

router = APIRouter(prefix="/admin", tags=["admin"])
RESET_PHRASE = "RESET DEMO"


class DemoResetConfirm(BaseModel):
    confirmation_token: str
    confirmation_phrase: str


@router.get("/audit")
def list_admin_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    rows = (
        db.query(AdminAuditLog)
        .filter(AdminAuditLog.cooperative_id == current_user.cooperative_id)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )
    numeric_actor_ids = {
        int(row.actor_id) for row in rows if row.actor_id and row.actor_id.isdigit()
    }
    actor_emails = {
        user.id: user.email
        for user in db.query(User).filter(User.id.in_(numeric_actor_ids)).all()
    }
    return [
        {
            "id": row.id,
            "actor_id": row.actor_id,
            "actor_label": actor_emails.get(int(row.actor_id))
            if row.actor_id and row.actor_id.isdigit()
            else row.actor_id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "details": row.details,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/integration-health")
def integration_health(
    current_user: User | None = Depends(require_roles("admin")),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    settings = get_settings()
    return {
        "environment": settings.moolre_env,
        "moolre": {
            "api_credentials_configured": bool(
                settings.moolre_api_user and settings.moolre_api_key
            ),
            "merchant_configured": bool(
                settings.moolre_merchant_id and settings.moolre_merchant_code
            ),
            "platform_wallet_configured": bool(settings.moolre_account_number),
            "webhook_verification_configured": bool(settings.moolre_webhook_secret),
        },
        "policy": {
            "disbursements": "platform_wallet",
            "repayments": "cooperative_wallet",
        },
    }


def _demo_cooperative(current_user: User, db: Session) -> Cooperative:
    settings = get_settings()
    if settings.app_env.lower() in ("production", "prod"):
        raise HTTPException(status_code=404, detail="Not found")
    cooperative = (
        db.query(Cooperative)
        .filter(
            Cooperative.id == current_user.cooperative_id,
            Cooperative.name == DEMO_COOPERATIVE_NAME,
        )
        .first()
    )
    if not cooperative:
        raise HTTPException(status_code=403, detail="Demo reset is unavailable for this workspace")
    return cooperative


@router.get("/demo-reset/preview")
def preview_demo_reset(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    cooperative = _demo_cooperative(current_user, db)
    preview = reset_demo_workspace(
        db,
        dry_run=True,
        cooperative_id=cooperative.id,
    )
    now = datetime.utcnow()
    db.query(AdminActionConfirmation).filter(
        AdminActionConfirmation.cooperative_id == cooperative.id,
        AdminActionConfirmation.user_id == current_user.id,
        AdminActionConfirmation.action == "demo_reset",
        AdminActionConfirmation.used_at.is_(None),
    ).update({AdminActionConfirmation.used_at: now}, synchronize_session=False)
    token_id = str(uuid.uuid4())
    expires_at = now + timedelta(minutes=5)
    db.add(
        AdminActionConfirmation(
            token_id=token_id,
            cooperative_id=cooperative.id,
            user_id=current_user.id,
            action="demo_reset",
            expires_at=expires_at,
        )
    )
    db.commit()
    token = jwt.encode(
        {
            "type": "demo_reset",
            "sub": str(current_user.id),
            "cooperative_id": cooperative.id,
            "jti": token_id,
            "exp": expires_at,
        },
        get_settings().secret_key,
        algorithm=ALGORITHM,
    )
    return {
        **preview,
        "confirmation_phrase": RESET_PHRASE,
        "confirmation_token": token,
        "expires_in_seconds": 300,
    }


@router.post("/demo-reset/confirm")
def confirm_demo_reset(
    body: DemoResetConfirm,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    cooperative = _demo_cooperative(current_user, db)
    if body.confirmation_phrase.strip() != RESET_PHRASE:
        raise HTTPException(status_code=400, detail=f'Type "{RESET_PHRASE}" to confirm')
    try:
        payload = jwt.decode(
            body.confirmation_token,
            get_settings().secret_key,
            algorithms=[ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail="Reset confirmation expired or invalid") from exc
    if (
        payload.get("type") != "demo_reset"
        or payload.get("sub") != str(current_user.id)
        or payload.get("cooperative_id") != cooperative.id
    ):
        raise HTTPException(status_code=403, detail="Reset confirmation does not match this workspace")

    token_id = payload.get("jti")
    if not isinstance(token_id, str) or not token_id:
        raise HTTPException(status_code=400, detail="Reset confirmation expired or invalid")
    confirmation = (
        db.query(AdminActionConfirmation)
        .filter(AdminActionConfirmation.token_id == token_id)
        .with_for_update()
        .first()
    )
    if not confirmation:
        raise HTTPException(status_code=400, detail="Reset confirmation expired or invalid")
    if (
        confirmation.action != "demo_reset"
        or confirmation.user_id != current_user.id
        or confirmation.cooperative_id != cooperative.id
    ):
        raise HTTPException(status_code=403, detail="Reset confirmation does not match this workspace")
    if confirmation.used_at is not None:
        raise HTTPException(status_code=409, detail="Reset confirmation has already been used")
    if confirmation.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset confirmation expired or invalid")

    confirmation.used_at = datetime.utcnow()
    result = reset_demo_workspace(
        db,
        dry_run=False,
        commit=False,
        cooperative_id=cooperative.id,
    )
    db.add(
        AdminAuditLog(
            cooperative_id=cooperative.id,
            actor_id=str(current_user.id),
            action="demo_workspace.reset",
            resource_type="cooperative",
            resource_id=str(cooperative.id),
            details=json.dumps({key: value for key, value in result.items() if key != "reset"}),
        )
    )
    db.commit()
    return result
