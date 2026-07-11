"""Production Tracking Routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import Farmer, Production, User
from app.services.auth_service import get_current_user
from app.schemas.schemas import (
    ProductionCreate,
    ProductionResponse,
    ProductionSummary,
    ProductionUpdate,
)

router = APIRouter(prefix="/production", tags=["production"])


def _get_production_or_404(production_id: int, db: Session) -> Production:
    record = db.query(Production).filter(Production.id == production_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Production record not found")
    return record


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=ProductionResponse, status_code=201)
def create_production(production_in: ProductionCreate, db: Session = Depends(get_db)):
    """Log a new crop / production cycle."""
    farmer = db.query(Farmer).filter(Farmer.id == production_in.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    record = Production(**production_in.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=list[ProductionResponse])
def list_productions(
    farmer_id: int | None = None,
    crop_type: str | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """List production records with optional filters."""
    query = db.query(Production)
    if current_user and current_user.cooperative_id:
        query = query.join(Farmer, Production.farmer_id == Farmer.id).filter(Farmer.cooperative_id == current_user.cooperative_id)
    if farmer_id is not None:
        query = query.filter(Production.farmer_id == farmer_id)
    if crop_type is not None:
        query = query.filter(Production.crop_type.ilike(f"%{crop_type}%"))
    return query.order_by(Production.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/farmer/{farmer_id}", response_model=list[ProductionResponse])
def get_farmer_productions(farmer_id: int, db: Session = Depends(get_db)):
    """Get all production records for a specific farmer."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return (
        db.query(Production)
        .filter(Production.farmer_id == farmer_id)
        .order_by(Production.created_at.desc())
        .all()
    )


@router.get("/farmer/{farmer_id}/summary", response_model=ProductionSummary)
def get_farmer_production_summary(farmer_id: int, db: Session = Depends(get_db)):
    """Yield summary for a farmer: total productions, kg harvested, completion rate."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    productions = db.query(Production).filter(Production.farmer_id == farmer_id).all()
    total = len(productions)
    harvested = [p for p in productions if p.harvest_date is not None]
    total_kg = sum(p.quantity_kg or 0 for p in harvested)
    completion_rate = (len(harvested) / total * 100) if total > 0 else 0.0

    return ProductionSummary(
        farmer_id=farmer_id,
        total_productions=total,
        total_kg_harvested=round(total_kg, 2),
        harvest_completion_rate=round(completion_rate, 2),
    )


@router.get("/{production_id}", response_model=ProductionResponse)
def get_production(production_id: int, db: Session = Depends(get_db)):
    """Get a single production record."""
    return _get_production_or_404(production_id, db)


@router.put("/{production_id}", response_model=ProductionResponse)
def update_production(
    production_id: int,
    updates: ProductionUpdate,
    db: Session = Depends(get_db),
):
    """Update a production record (e.g. log harvest data)."""
    record = _get_production_or_404(production_id, db)

    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{production_id}", status_code=204)
def delete_production(production_id: int, db: Session = Depends(get_db)):
    """Delete a production record."""
    record = _get_production_or_404(production_id, db)
    db.delete(record)
    db.commit()
