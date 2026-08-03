from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.farm_production import FarmProduction
from app.models.models import Cooperative, User
from app.schemas.farm_production import (
    FarmProductionCreate,
    FarmProductionResponse,
    FarmProductionUpdate,
)
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/production/farm", tags=["farm_production"])


@router.get("/", response_model=list[FarmProductionResponse])
def list_farm_productions(
    cooperative_id: int = Query(...),
    crop_type: str | None = None,
    season: str | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    query = db.query(FarmProduction).filter(FarmProduction.cooperative_id == cooperative_id)
    if crop_type:
        query = query.filter(FarmProduction.crop_type.ilike(f"%{crop_type}%"))
    if season:
        query = query.filter(FarmProduction.season == season)
    return query.order_by(FarmProduction.planted_date.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=FarmProductionResponse, status_code=201)
def create_farm_production(
    data: FarmProductionCreate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    record = FarmProduction(
        cooperative_id=cooperative_id,
        crop_type=data.crop_type,
        season=data.season,
        location=data.location,
        planted_date=data.planted_date,
        expected_harvest_date=data.expected_harvest_date,
        actual_harvest_date=data.actual_harvest_date,
        expected_quantity_kg=data.expected_quantity_kg,
        actual_quantity_kg=data.actual_quantity_kg,
        quality_grade=data.quality_grade,
        notes=data.notes,
        logged_by=current_user.id if current_user else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{record_id}", response_model=FarmProductionResponse)
def update_farm_production(
    record_id: int,
    data: FarmProductionUpdate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    record = db.query(FarmProduction).filter(
        FarmProduction.id == record_id,
        FarmProduction.cooperative_id == cooperative_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Farm production record not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record
