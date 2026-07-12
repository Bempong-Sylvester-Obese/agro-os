"""Cooperative Management Routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import Cooperative, User
from app.schemas.schemas import CooperativeCreate, CooperativeResponse, CooperativeUpdate
from app.services.auth_service import enforce_cooperative_scope, get_current_user, require_roles

router = APIRouter(prefix="/cooperatives", tags=["cooperatives"])


@router.post("/", response_model=CooperativeResponse, status_code=201)
def create_cooperative(
    cooperative: CooperativeCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Create a new farmer cooperative."""
    if current_user is not None:
        raise HTTPException(status_code=403, detail="Create cooperatives through signup")
    db_coop = Cooperative(**cooperative.model_dump())
    db.add(db_coop)
    db.commit()
    db.refresh(db_coop)
    return db_coop


@router.get("/", response_model=list[CooperativeResponse])
def list_cooperatives(
    skip: int = 0,
    limit: int = Query(default=100, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """List all cooperatives."""
    query = db.query(Cooperative)
    if current_user is not None:
        query = query.filter(Cooperative.id == current_user.cooperative_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{cooperative_id}", response_model=CooperativeResponse)
def get_cooperative(
    cooperative_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get a cooperative by ID."""
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    return coop


@router.put("/{cooperative_id}", response_model=CooperativeResponse)
def update_cooperative(
    cooperative_id: int,
    updates: CooperativeUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Update a cooperative (partial update)."""
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(coop, field, value)

    db.commit()
    db.refresh(coop)
    return coop


@router.delete("/{cooperative_id}", status_code=204)
def delete_cooperative(
    cooperative_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Delete a cooperative (only if it has no farmers)."""
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    if coop.farmers:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a cooperative with active farmers. Remove members first.",
        )
    db.delete(coop)
    db.commit()
