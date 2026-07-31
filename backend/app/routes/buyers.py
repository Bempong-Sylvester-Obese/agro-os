"""Cooperative buyer directory."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import AdminAuditLog, Buyer, User
from app.schemas.market import BuyerCreate, BuyerResponse, BuyerUpdate
from app.services.auth_service import get_current_user, require_roles

router = APIRouter(prefix="/buyers", tags=["buyers"])


def _scope(user: User | None, cooperative_id: int | None) -> int:
    return resolve_cooperative_scope(
        current_user=user,
        cooperative_id=cooperative_id,
        settings=get_settings(),
    )


def _actor(user: User | None) -> str:
    return str(user.id) if user else "system"


@router.post("/", response_model=BuyerResponse, status_code=201)
def create_buyer(
    payload: BuyerCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer", "sales_officer")
    ),
):
    cooperative_id = _scope(current_user, payload.cooperative_id)
    buyer = Buyer(
        cooperative_id=cooperative_id,
        name=payload.name.strip(),
        phone=payload.phone,
        email=payload.email,
        address=payload.address,
        created_by=_actor(current_user),
    )
    db.add(buyer)
    db.flush()
    db.add(
        AdminAuditLog(
            cooperative_id=cooperative_id,
            actor_id=_actor(current_user),
            action="buyer.created",
            resource_type="buyer",
            resource_id=str(buyer.id),
        )
    )
    db.commit()
    db.refresh(buyer)
    return buyer


@router.get("/", response_model=list[BuyerResponse])
def list_buyers(
    cooperative_id: int | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    scoped_id = _scope(current_user, cooperative_id)
    query = db.query(Buyer).filter(Buyer.cooperative_id == scoped_id)
    if active_only:
        query = query.filter(Buyer.is_active.is_(True))
    return query.order_by(Buyer.name).all()


@router.patch("/{buyer_id}", response_model=BuyerResponse)
def update_buyer(
    buyer_id: int,
    payload: BuyerUpdate,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer", "sales_officer")
    ),
):
    scoped_id = _scope(current_user, cooperative_id)
    buyer = (
        db.query(Buyer)
        .filter(Buyer.id == buyer_id, Buyer.cooperative_id == scoped_id)
        .with_for_update()
        .first()
    )
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(buyer, key, value.strip() if isinstance(value, str) else value)
    db.add(
        AdminAuditLog(
            cooperative_id=scoped_id,
            actor_id=_actor(current_user),
            action="buyer.updated",
            resource_type="buyer",
            resource_id=str(buyer.id),
        )
    )
    db.commit()
    db.refresh(buyer)
    return buyer
