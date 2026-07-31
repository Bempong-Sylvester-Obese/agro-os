"""Cooperative Management Routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import AdminAuditLog, Cooperative, User
from app.schemas.schemas import (
    CooperativeCreate,
    CooperativeResponse,
    CooperativeUpdate,
)
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)
from app.services.moolre_service import MoolreService

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

    if current_user:
        db.add(
            AdminAuditLog(
                cooperative_id=coop.id,
                actor_id=str(current_user.id),
                action="settings.updated",
                resource_type="cooperative",
                resource_id=str(coop.id),
                details="fields=" + ",".join(sorted(updates.model_dump(exclude_none=True))),
            )
        )
    db.commit()
    db.refresh(coop)
    return coop


@router.post("/{cooperative_id}/wallet/provision", response_model=CooperativeResponse)
async def provision_wallet(
    cooperative_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Provision a Moolre sub-wallet for the cooperative."""
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
        
    if coop.moolre_account_number:
        raise HTTPException(status_code=400, detail="Wallet already provisioned")
        
    moolre = MoolreService()
    result = await moolre.create_account(
        account_name=coop.name,
        currency=coop.currency or "GHS",
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to provision wallet: {result.get('raw', {}).get('message', 'Unknown error')}"
        )
        
    coop.moolre_account_number = result.get("account_number")
    
    if current_user:
        db.add(
            AdminAuditLog(
                cooperative_id=coop.id,
                actor_id=str(current_user.id),
                action="wallet.provisioned",
                resource_type="cooperative",
                resource_id=str(coop.id),
                details=f"account_number={coop.moolre_account_number}",
            )
        )
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
    if get_settings().app_env.lower() in ("production", "prod"):
        raise HTTPException(status_code=404, detail="Not found")
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    if coop.memberships:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a cooperative with active farmers. Remove members first.",
        )
    db.delete(coop)
    db.commit()
