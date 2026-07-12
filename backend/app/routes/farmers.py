"""Farmer Management Routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import (
    CooperativeAttendance,
    Cooperative,
    CooperativeMembership,
    Farmer,
    MembershipStatus,
    User,
)
from app.services.auth_service import enforce_cooperative_scope, get_current_user, require_roles
from app.schemas.schemas import (
    AttendanceCreate,
    AttendanceResponse,
    FarmerCreate,
    FarmerResponse,
    FarmerUpdate,
    TrustScoreResponse,
)
from app.services.trust_score_service import TrustScoreService
from app.utils.phone import normalize_ghana_phone

router = APIRouter(prefix="/farmers", tags=["farmers"])


def _get_farmer_or_404(
    farmer_id: int, db: Session, current_user: User | None = None
) -> CooperativeMembership:
    membership = (
        db.query(CooperativeMembership)
        .options(joinedload(CooperativeMembership.farmer))
        .filter(CooperativeMembership.id == farmer_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Farmer not found")
    enforce_cooperative_scope(current_user, membership.cooperative_id)
    return membership


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=FarmerResponse, status_code=201)
def create_farmer(
    farmer_in: FarmerCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Register a new farmer / cooperative member."""
    # Ensure cooperative exists
    cooperative_id = (
        current_user.cooperative_id if current_user is not None else farmer_in.cooperative_id
    )
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    normalized_phone = normalize_ghana_phone(farmer_in.phone)
    farmer = db.query(Farmer).filter(Farmer.phone == normalized_phone).first()
    existing_farmer = farmer is not None
    if farmer is None:
        farmer = Farmer(
            name=farmer_in.name,
            phone=normalized_phone,
            email=farmer_in.email,
            location=farmer_in.location,
        )
        db.add(farmer)
        db.flush()

    duplicate = (
        db.query(CooperativeMembership)
        .filter(
            CooperativeMembership.farmer_id == farmer.id,
            CooperativeMembership.cooperative_id == cooperative_id,
        )
        .first()
    )
    if duplicate:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This farmer is already a member of your cooperative",
        )

    membership = CooperativeMembership(
        farmer_id=farmer.id,
        cooperative_id=cooperative_id,
        crop_type=farmer_in.crop_type,
        acreage=farmer_in.acreage,
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This farmer is already a member of your cooperative",
        )
    db.refresh(membership)
    response = FarmerResponse.model_validate(membership).model_dump()
    response["existing_farmer"] = existing_farmer
    return response


@router.get("/", response_model=list[FarmerResponse])
def list_farmers(
    cooperative_id: int | None = None,
    membership_status: MembershipStatus | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """List farmers with optional cooperative and status filters."""
    query = db.query(CooperativeMembership).options(
        joinedload(CooperativeMembership.farmer)
    )
    if current_user and current_user.cooperative_id:
        query = query.filter(
            CooperativeMembership.cooperative_id == current_user.cooperative_id
        )
    elif cooperative_id is not None:
        query = query.filter(CooperativeMembership.cooperative_id == cooperative_id)
    else:
        settings = get_settings()
        if settings.auth_enabled:
            raise HTTPException(status_code=401, detail="Authentication required")
        raise HTTPException(status_code=400, detail="cooperative_id is required")
    if membership_status is not None:
        query = query.filter(
            CooperativeMembership.membership_status == membership_status
        )
    return (
        query.join(Farmer)
        .order_by(Farmer.name)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{farmer_id}", response_model=FarmerResponse)
def get_farmer(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get farmer profile."""
    return _get_farmer_or_404(farmer_id, db, current_user)


@router.put("/{farmer_id}", response_model=FarmerResponse)
def update_farmer(
    farmer_id: int,
    updates: FarmerUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Partial-update farmer profile."""
    membership = _get_farmer_or_404(farmer_id, db, current_user)

    if updates.phone:
        normalized_phone = normalize_ghana_phone(updates.phone)
        existing = (
            db.query(Farmer)
            .filter(
                Farmer.phone == normalized_phone,
                Farmer.id != membership.farmer_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Phone number already registered to another farmer")
        membership.farmer.phone = normalized_phone

    values = updates.model_dump(exclude_none=True, exclude={"phone", "cooperative_id"})
    for field in ("name", "email", "location"):
        if field in values:
            setattr(membership.farmer, field, values[field])
    for field in ("crop_type", "acreage", "membership_status"):
        if field in values:
            setattr(membership, field, values[field])

    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/{farmer_id}", status_code=204)
def deactivate_farmer(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Soft-deactivate a farmer (sets membership_status → inactive)."""
    farmer = _get_farmer_or_404(farmer_id, db, current_user)
    farmer.membership_status = MembershipStatus.inactive
    db.commit()


# ---------------------------------------------------------------------------
# Trust Score
# ---------------------------------------------------------------------------


@router.get("/{farmer_id}/trust-score", response_model=TrustScoreResponse)
def get_trust_score(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Return the most recent trust score breakdown for a farmer."""
    _get_farmer_or_404(farmer_id, db, current_user)
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
    farmer_id: int,
    limit: int = Query(default=10, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Return the last N trust score snapshots for trend display."""
    _get_farmer_or_404(farmer_id, db, current_user)
    return TrustScoreService.get_score_history(farmer_id, db, limit=limit)


@router.post("/{farmer_id}/recalculate-trust-score", response_model=TrustScoreResponse)
def recalculate_trust_score(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    """Trigger a manual trust score recalculation."""
    _get_farmer_or_404(farmer_id, db, current_user)
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
    current_user: User | None = Depends(require_roles("admin")),
):
    """Record whether a farmer attended a cooperative event."""
    _get_farmer_or_404(farmer_id, db, current_user)
    attendance_in.farmer_id = farmer_id  # ensure path param takes precedence
    record = CooperativeAttendance(**attendance_in.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{farmer_id}/attendance", response_model=list[AttendanceResponse])
def list_attendance(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """List all attendance records for a farmer."""
    _get_farmer_or_404(farmer_id, db, current_user)
    return (
        db.query(CooperativeAttendance)
        .filter(CooperativeAttendance.farmer_id == farmer_id)
        .order_by(CooperativeAttendance.event_date.desc())
        .all()
    )
