"""Enterprise organizations: many cooperatives under one account (#237).

Scope rules (see docs/architecture/tenancy-decision.md, "Organizations"):

* Tenancy remains cooperative-scoped. Every operational endpoint is scoped to
  the caller's *active* cooperative (``users.cooperative_id``) exactly as
  before; nothing here widens a data query across cooperatives.
* An organization administrator is a user with ``users.organization_id`` set.
  They may: read the organization, list its cooperatives with a billing and
  usage summary, create new cooperatives inside it, and *switch* their active
  cooperative to any member cooperative. Switching re-issues the JWT so the
  client and the server agree on the active scope.
* Cooperative admins who are not organization administrators cannot see or
  affect the organization (404, never 403, to avoid leaking existence).
* The Enterprise contract itself (plan activation, expiry) is sales-led and
  set by an operator (``backend/scripts/activate_enterprise.py``), never by
  an API caller — the same rule as cooperative plans (#235).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import AdminAuditLog, Cooperative, Organization, PendingCheckout, User
from app.schemas.auth import Token, UserResponse
from app.services import entitlements, subscription_lifecycle as lifecycle
from app.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    billing_email: EmailStr | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    billing_email: EmailStr | None = None


class OrganizationCooperativeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    location: str | None = None
    currency: str = "GHS"
    organization_type: str = "cooperative"


class SwitchRequest(BaseModel):
    cooperative_id: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _org_admin(current_user: User | None) -> User:
    """The caller must be an organization administrator."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not current_user.organization_id:
        raise HTTPException(status_code=404, detail="Resource not found")
    return current_user


def _scoped_org(db: Session, current_user: User, organization_id: int) -> Organization:
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Resource not found")
    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return org


def _org_row(org: Organization) -> dict[str, Any]:
    return {
        "id": org.id,
        "name": org.name,
        "description": org.description,
        "billing_email": org.billing_email,
        "subscription_plan": org.subscription_plan,
        "subscription_status": org.subscription_status,
        "subscription_expires_at": org.subscription_expires_at.isoformat() if org.subscription_expires_at else None,
        "subscription_live": org.subscription_is_live(),
        "contract_reference": org.contract_reference,
        "cooperative_count": len(org.cooperatives),
        "created_at": org.created_at.isoformat() if org.created_at else None,
    }


def _coop_row(db: Session, coop: Cooperative, active_id: int | None) -> dict[str, Any]:
    usage = entitlements.usage_summary(db, coop)
    state = lifecycle.describe(coop)
    return {
        "id": coop.id,
        "name": coop.name,
        "location": coop.location,
        "organization_type": coop.organization_type,
        "is_active_scope": coop.id == active_id,
        "subscription_plan": coop.subscription_plan,
        "subscription_status": state.status,
        "effective_plan_key": usage["effective_plan_key"],
        "effective_plan_name": usage["effective_plan_name"],
        "inherits_organization_plan": lifecycle.organization_plan_key(coop) is not None,
        "expires_at": state.expires_at.isoformat() if state.expires_at else None,
        "members": usage["limits"]["members"],
        "workers": usage["limits"]["workers"],
        "sms": usage["limits"]["sms"],
    }


def _issue_token(user: User) -> dict[str, Any]:
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "cooperative_id": user.cooperative_id,
            "organization_id": user.organization_id,
            "role": user.role,
            "organization_type": user.cooperative.organization_type if user.cooperative else None,
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
        "organization_type": user.cooperative.organization_type if user.cooperative else None,
        "password_change_required": user.must_change_password,
    }


def _audit(db: Session, *, user: User, cooperative_id: int, action: str, resource_id: str, details: str | None) -> None:
    db.add(
        AdminAuditLog(
            cooperative_id=cooperative_id,
            actor_id=str(user.id),
            action=action,
            resource_type="organization",
            resource_id=resource_id,
            details=details,
        )
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
def create_organization(
    body: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
) -> dict[str, Any]:
    """Create an organization from the caller's cooperative.

    The caller's cooperative becomes the first member and the caller becomes
    an organization administrator. The organization starts with a *pending*
    Enterprise subscription; member cooperatives keep their own plans until
    the contract is activated by an operator.
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if current_user.organization_id:
        raise HTTPException(status_code=409, detail="You already administer an organization")
    if not current_user.cooperative_id:
        raise HTTPException(status_code=400, detail="An active cooperative is required")
    coop = db.get(Cooperative, current_user.cooperative_id)
    if coop is None:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    if coop.organization_id:
        raise HTTPException(status_code=409, detail="This cooperative already belongs to an organization")

    org = Organization(
        name=body.name.strip(),
        description=body.description,
        billing_email=body.billing_email,
        subscription_plan="enterprise",
        subscription_status=Organization.STATUS_PENDING,
    )
    db.add(org)
    db.flush()
    coop.organization_id = org.id
    current_user.organization_id = org.id
    _audit(db, user=current_user, cooperative_id=coop.id, action="organization.created",
           resource_id=str(org.id), details=f"name={org.name}")
    db.commit()
    db.refresh(org)
    return _org_row(org)


@router.get("/me")
def my_organization(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """The caller's organization with its cooperatives, or 404 when none."""
    user = _org_admin(current_user)
    org = _scoped_org(db, user, user.organization_id)
    return {
        **_org_row(org),
        "cooperatives": [_coop_row(db, c, user.cooperative_id) for c in sorted(org.cooperatives, key=lambda c: c.name.lower())],
    }


@router.patch("/{organization_id}")
def update_organization(
    organization_id: int,
    body: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
) -> dict[str, Any]:
    """Edit profile fields. Subscription fields are operator-only."""
    user = _org_admin(current_user)
    org = _scoped_org(db, user, organization_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(org, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(org)
    return _org_row(org)


@router.get("/{organization_id}/cooperatives")
def list_organization_cooperatives(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    user = _org_admin(current_user)
    org = _scoped_org(db, user, organization_id)
    return [_coop_row(db, c, user.cooperative_id) for c in sorted(org.cooperatives, key=lambda c: c.name.lower())]


@router.post("/{organization_id}/cooperatives", status_code=201)
def create_organization_cooperative(
    organization_id: int,
    body: OrganizationCooperativeCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
) -> dict[str, Any]:
    """Create a new cooperative inside the organization.

    The cooperative starts on the free tier like any other; while the
    organization's contract is live it inherits the Enterprise plan.
    """
    user = _org_admin(current_user)
    org = _scoped_org(db, user, organization_id)
    if body.organization_type not in ("cooperative", "solo_farm"):
        raise HTTPException(status_code=400, detail="organization_type must be cooperative or solo_farm")
    coop = Cooperative(
        name=body.name.strip(),
        description=body.description,
        location=body.location,
        currency=body.currency or "GHS",
        organization_type=body.organization_type,
        subscription_plan=lifecycle.FREE_PLAN,
        subscription_status=lifecycle.STATUS_ACTIVE,
        organization_id=org.id,
    )
    db.add(coop)
    db.flush()
    _audit(db, user=user, cooperative_id=coop.id, action="organization.cooperative_created",
           resource_id=str(org.id), details=f"cooperative_id={coop.id} name={coop.name}")
    db.commit()
    db.refresh(coop)
    return _coop_row(db, coop, user.cooperative_id)


@router.post("/{organization_id}/switch", response_model=Token)
def switch_active_cooperative(
    organization_id: int,
    body: SwitchRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Make another member cooperative the caller's active scope.

    Persists ``users.cooperative_id`` and returns a fresh token carrying the
    new scope. All cooperative-scoped endpoints then apply to that cooperative.
    """
    user = _org_admin(current_user)
    org = _scoped_org(db, user, organization_id)
    target = db.get(Cooperative, body.cooperative_id)
    if target is None or target.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Resource not found")
    previous = user.cooperative_id
    user.cooperative_id = target.id
    _audit(db, user=user, cooperative_id=target.id, action="organization.scope_switched",
           resource_id=str(org.id), details=f"from={previous} to={target.id}")
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.get("/{organization_id}/billing")
def organization_billing(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
) -> dict[str, Any]:
    """Consolidated billing across member cooperatives.

    Combines the organization's contract, each cooperative's plan/usage, and
    every subscription intent recorded against member cooperatives.
    """
    user = _org_admin(current_user)
    org = _scoped_org(db, user, organization_id)
    coops = sorted(org.cooperatives, key=lambda c: c.name.lower())
    coop_ids = [c.id for c in coops]
    intents = (
        db.query(PendingCheckout)
        .filter(PendingCheckout.cooperative_id.in_(coop_ids))
        .order_by(PendingCheckout.created_at.desc(), PendingCheckout.id.desc())
        .limit(200)
        .all()
        if coop_ids
        else []
    )
    names = {c.id: c.name for c in coops}
    history = []
    for intent in intents:
        paid = intent.status != PendingCheckout.STATUS_PENDING
        history.append(
            {
                "id": intent.id,
                "cooperative_id": intent.cooperative_id,
                "cooperative_name": names.get(intent.cooperative_id),
                "reference": intent.reference,
                "kind": intent.kind,
                "plan_key": intent.plan_key,
                "band": intent.band,
                "amount": intent.amount,
                "currency": intent.currency or "GHS",
                "outcome": "paid" if paid else "pending",
                "provider_transaction_id": intent.provider_transaction_id,
                "created_at": intent.created_at.isoformat() if intent.created_at else None,
                "paid_at": intent.paid_at.isoformat() if intent.paid_at else None,
            }
        )
    rows = [_coop_row(db, c, user.cooperative_id) for c in coops]
    return {
        "organization": _org_row(org),
        "cooperatives": rows,
        "totals": {
            "cooperatives": len(rows),
            "members": sum(r["members"]["used"] for r in rows),
            "workers": sum(r["workers"]["used"] for r in rows),
            "sms_this_month": sum(r["sms"]["used"] for r in rows),
            "paid": round(sum(h["amount"] for h in history if h["outcome"] == "paid"), 2),
            "currency": "GHS",
        },
        "history": history,
        "generated_at": datetime.utcnow().isoformat(),
    }
