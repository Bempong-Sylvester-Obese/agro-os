"""Production Tracking Routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import (
    CooperativeMembership as Farmer,
)
from app.models.models import (
    Production,
    ProductionFocus,
    ProductionKind,
    User,
)
from app.schemas.schemas import (
    ProductionCreate,
    ProductionResponse,
    ProductionSummary,
    ProductionUpdate,
)
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/production", tags=["production"])


def _validate_member_kind(farmer: Farmer, kind: ProductionKind) -> None:
    focus = farmer.production_focus or ProductionFocus.crop
    if focus == ProductionFocus.mixed:
        return
    if focus.value != kind.value:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{kind.value} production is not allowed "
                f"for a {focus.value}-only member"
            ),
        )


def _get_production_or_404(
    production_id: int, db: Session, current_user: User | None = None
) -> Production:
    record = db.query(Production).filter(Production.id == production_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Production record not found")
    farmer = db.query(Farmer).filter(Farmer.id == record.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Production record not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)
    return record


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=ProductionResponse, status_code=201)
def create_production(
    production_in: ProductionCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Log a new crop / production cycle."""
    farmer = db.query(Farmer).filter(Farmer.id == production_in.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)
    _validate_member_kind(farmer, production_in.production_kind)

    record = Production(**production_in.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=list[ProductionResponse])
def list_productions(
    farmer_id: int | None = None,
    crop_type: str | None = None,
    production_kind: ProductionKind | None = None,
    product_name: str | None = None,
    cooperative_id: int | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """List production records with optional filters."""
    query = db.query(Production)
    if current_user and current_user.cooperative_id:
        query = query.join(Farmer, Production.farmer_id == Farmer.id).filter(
            Farmer.cooperative_id == current_user.cooperative_id
        )
    elif cooperative_id is not None:
        query = query.join(Farmer, Production.farmer_id == Farmer.id).filter(
            Farmer.cooperative_id == cooperative_id
        )
    else:
        settings = get_settings()
        if settings.auth_enabled:
            raise HTTPException(status_code=401, detail="Authentication required")
        raise HTTPException(status_code=400, detail="cooperative_id is required")
    if farmer_id is not None:
        query = query.filter(Production.farmer_id == farmer_id)
    if crop_type is not None:
        query = query.filter(Production.crop_type.ilike(f"%{crop_type}%"))
    if production_kind is not None:
        query = query.filter(Production.production_kind == production_kind)
    if product_name is not None:
        query = query.filter(Production.product_name.ilike(f"%{product_name}%"))
    return query.order_by(Production.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/farmer/{farmer_id}", response_model=list[ProductionResponse])
def get_farmer_productions(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get all production records for a specific farmer."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)
    return (
        db.query(Production)
        .filter(Production.farmer_id == farmer_id)
        .order_by(Production.created_at.desc())
        .all()
    )


@router.get("/farmer/{farmer_id}/summary", response_model=ProductionSummary)
def get_farmer_production_summary(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Yield summary for a farmer: total productions, kg harvested, completion rate."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)

    productions = db.query(Production).filter(Production.farmer_id == farmer_id).all()
    total = len(productions)
    completed = [
        p for p in productions if p.quantity is not None or p.harvest_date is not None
    ]
    harvested = [p for p in productions if p.harvest_date is not None]
    total_kg = sum(p.quantity_kg or 0 for p in harvested)
    completion_rate = (len(harvested) / total * 100) if total > 0 else 0.0
    production_completion_rate = (len(completed) / total * 100) if total > 0 else 0.0
    totals_by_unit: dict[str, float] = {}
    for production in completed:
        quantity = production.quantity
        if quantity is None:
            quantity = production.quantity_kg
        if quantity is None:
            continue
        unit = production.unit or "kg"
        totals_by_unit[unit] = totals_by_unit.get(unit, 0.0) + quantity

    return ProductionSummary(
        farmer_id=farmer_id,
        total_productions=total,
        completed_productions=len(completed),
        totals_by_unit={
            unit: round(quantity, 2) for unit, quantity in totals_by_unit.items()
        },
        production_completion_rate=round(production_completion_rate, 2),
        total_kg_harvested=round(total_kg, 2),
        harvest_completion_rate=round(completion_rate, 2),
    )


@router.get("/{production_id}", response_model=ProductionResponse)
def get_production(
    production_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get a single production record."""
    return _get_production_or_404(production_id, db, current_user)


@router.put("/{production_id}", response_model=ProductionResponse)
def update_production(
    production_id: int,
    updates: ProductionUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Update a production record (e.g. log harvest data)."""
    record = _get_production_or_404(production_id, db, current_user)
    farmer = db.query(Farmer).filter(Farmer.id == record.farmer_id).first()

    values = updates.model_dump(exclude_none=True)
    kind = values.get("production_kind", record.production_kind)
    _validate_member_kind(farmer, kind)
    unit = values.get("unit", record.unit or "kg")
    if kind == ProductionKind.crop:
        product_name = values.get("product_name") or values.get("crop_type")
        if product_name:
            values["product_name"] = product_name
            values["crop_type"] = product_name
    elif "crop_type" in values:
        raise HTTPException(
            status_code=422, detail="crop_type is only valid for crop production"
        )
    if "expected_kg" in values and "expected_quantity" not in values:
        values["expected_quantity"] = values["expected_kg"]
    if "quantity_kg" in values and "quantity" not in values:
        values["quantity"] = values["quantity_kg"]
    if str(unit).lower() == "kg":
        if "expected_quantity" in values and "expected_kg" not in values:
            values["expected_kg"] = values["expected_quantity"]
        if "quantity" in values and "quantity_kg" not in values:
            values["quantity_kg"] = values["quantity"]
    if "harvest_date" in values and "production_date" not in values:
        values["production_date"] = values["harvest_date"]

    for field, value in values.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{production_id}", status_code=204)
def delete_production(
    production_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Delete a production record."""
    record = _get_production_or_404(production_id, db, current_user)
    db.delete(record)
    db.commit()
