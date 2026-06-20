"""Farmer Management Routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import CooperativeAttendance, Cooperative, Farmer, MembershipStatus
from app.schemas.schemas import (
    AttendanceCreate,
    AttendanceResponse,
    FarmerCreate,
    FarmerResponse,
    FarmerUpdate,
    TrustScoreResponse,
)
from app.services.trust_score_service import TrustScoreService

router = APIRouter(prefix="/farmers", tags=["farmers"])


def _get_farmer_or_404(farmer_id: int, db: Session) -> Farmer:
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=FarmerResponse, status_code=201)
def create_farmer(farmer_in: FarmerCreate, db: Session = Depends(get_db)):
    """Register a new farmer / cooperative member."""
    # Ensure cooperative exists
    coop = db.query(Cooperative).filter(Cooperative.id == farmer_in.cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    # Duplicate phone check
    existing = db.query(Farmer).filter(Farmer.phone == farmer_in.phone).first()
    if existing:
        raise HTTPException(status_code=409, detail="A farmer with this phone number already exists")

    farmer = Farmer(**farmer_in.model_dump())
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


@router.get("/", response_model=list[FarmerResponse])
def list_farmers(
    cooperative_id: int | None = None,
    membership_status: MembershipStatus | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List farmers with optional cooperative and status filters."""
    query = db.query(Farmer)
    if cooperative_id is not None:
        query = query.filter(Farmer.cooperative_id == cooperative_id)
    if membership_status is not None:
        query = query.filter(Farmer.membership_status == membership_status)
    return query.order_by(Farmer.name).offset(skip).limit(limit).all()


@router.get("/{farmer_id}", response_model=FarmerResponse)
def get_farmer(farmer_id: int, db: Session = Depends(get_db)):
    """Get farmer profile."""
    return _get_farmer_or_404(farmer_id, db)


@router.put("/{farmer_id}", response_model=FarmerResponse)
def update_farmer(
    farmer_id: int,
    updates: FarmerUpdate,
    db: Session = Depends(get_db),
):
    """Partial-update farmer profile."""
    farmer = _get_farmer_or_404(farmer_id, db)

    # Phone uniqueness check (only if changing phone)
    if updates.phone and updates.phone != farmer.phone:
        existing = db.query(Farmer).filter(Farmer.phone == updates.phone).first()
        if existing:
            raise HTTPException(status_code=409, detail="Phone number already registered to another farmer")

    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(farmer, field, value)

    db.commit()
    db.refresh(farmer)
    return farmer


@router.delete("/{farmer_id}", status_code=204)
def deactivate_farmer(farmer_id: int, db: Session = Depends(get_db)):
    """Soft-deactivate a farmer (sets membership_status → inactive)."""
    farmer = _get_farmer_or_404(farmer_id, db)
    farmer.membership_status = MembershipStatus.inactive
    db.commit()


# ---------------------------------------------------------------------------
# Trust Score
# ---------------------------------------------------------------------------


@router.get("/{farmer_id}/trust-score", response_model=TrustScoreResponse)
def get_trust_score(farmer_id: int, db: Session = Depends(get_db)):
    """Return the most recent trust score breakdown for a farmer."""
    _get_farmer_or_404(farmer_id, db)
    from app.models.models import TrustScore

    snapshot = (
        db.query(TrustScore)
        .filter(TrustScore.farmer_id == farmer_id)
        .order_by(TrustScore.calculated_at.desc())
        .first()
    )
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail="No trust score calculated yet. POST to /recalculate-trust-score first.",
        )
    return snapshot


@router.get("/{farmer_id}/trust-score/history", response_model=list[TrustScoreResponse])
def get_trust_score_history(
    farmer_id: int, limit: int = 10, db: Session = Depends(get_db)
):
    """Return the last N trust score snapshots for trend display."""
    _get_farmer_or_404(farmer_id, db)
    return TrustScoreService.get_score_history(farmer_id, db, limit=limit)


@router.post("/{farmer_id}/recalculate-trust-score", response_model=TrustScoreResponse)
def recalculate_trust_score(farmer_id: int, db: Session = Depends(get_db)):
    """Trigger a manual trust score recalculation."""
    _get_farmer_or_404(farmer_id, db)
    try:
        return TrustScoreService.calculate_trust_score(farmer_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------


@router.post("/{farmer_id}/attendance", response_model=AttendanceResponse, status_code=201)
def record_attendance(
    farmer_id: int,
    attendance_in: AttendanceCreate,
    db: Session = Depends(get_db),
):
    """Record whether a farmer attended a cooperative event."""
    _get_farmer_or_404(farmer_id, db)
    attendance_in.farmer_id = farmer_id  # ensure path param takes precedence
    record = CooperativeAttendance(**attendance_in.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{farmer_id}/attendance", response_model=list[AttendanceResponse])
def list_attendance(farmer_id: int, db: Session = Depends(get_db)):
    """List all attendance records for a farmer."""
    _get_farmer_or_404(farmer_id, db)
    return (
        db.query(CooperativeAttendance)
        .filter(CooperativeAttendance.farmer_id == farmer_id)
        .order_by(CooperativeAttendance.event_date.desc())
        .all()
    )
