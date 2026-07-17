"""Cooperative-scoped produce intake operations."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import (
    AdminAuditLog,
    CooperativeMembership,
    IntakeStatus,
    ProduceIntake,
    ProductionFocus,
    User,
)
from app.schemas.market import IntakeCreate, IntakeResponse, IntakeReview
from app.services.auth_service import get_current_user, require_roles

router = APIRouter(prefix="/intakes", tags=["produce-intake"])


def _scope(current_user: User | None, cooperative_id: int | None) -> int:
    return resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=cooperative_id,
        settings=get_settings(),
    )


def _actor(current_user: User | None) -> str:
    return str(current_user.id) if current_user else "system"


@router.post("/", response_model=IntakeResponse, status_code=201)
def create_intake(
    payload: IntakeCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "field_officer", "operations_officer")
    ),
):
    cooperative_id = _scope(current_user, payload.cooperative_id)
    membership = (
        db.query(CooperativeMembership)
        .filter(
            CooperativeMembership.id == payload.membership_id,
            CooperativeMembership.cooperative_id == cooperative_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    if membership.production_focus == ProductionFocus.animal:
        raise HTTPException(
            status_code=409,
            detail="Produce intake is crop-only and unavailable to animal-only members",
        )
    intake = ProduceIntake(
        cooperative_id=cooperative_id,
        membership_id=payload.membership_id,
        crop_type=payload.crop_type.strip(),
        quantity_kg=payload.quantity_kg,
        quality_grade=payload.quality_grade,
        collection_point=payload.collection_point,
        received_at=payload.received_at or datetime.utcnow(),
        notes=payload.notes,
        created_by=_actor(current_user),
    )
    db.add(intake)
    db.flush()
    db.add(
        AdminAuditLog(
            cooperative_id=cooperative_id,
            actor_id=_actor(current_user),
            action="produce_intake.created",
            resource_type="produce_intake",
            resource_id=str(intake.id),
            details=f"membership_id={intake.membership_id};quantity_kg={intake.quantity_kg}",
        )
    )
    db.commit()
    db.refresh(intake)
    return intake


@router.get("/", response_model=list[IntakeResponse])
def list_intakes(
    cooperative_id: int | None = None,
    membership_id: int | None = None,
    status: IntakeStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    scoped_id = _scope(current_user, cooperative_id)
    query = db.query(ProduceIntake).filter(
        ProduceIntake.cooperative_id == scoped_id
    )
    if membership_id is not None:
        query = query.filter(ProduceIntake.membership_id == membership_id)
    if status is not None:
        query = query.filter(ProduceIntake.status == status)
    return query.order_by(ProduceIntake.received_at.desc()).all()


def _review_intake(
    *,
    intake_id: int,
    payload: IntakeReview,
    accept: bool,
    cooperative_id: int,
    db: Session,
    current_user: User | None,
) -> ProduceIntake:
    intake = (
        db.query(ProduceIntake)
        .filter(
            ProduceIntake.id == intake_id,
            ProduceIntake.cooperative_id == cooperative_id,
        )
        .with_for_update()
        .first()
    )
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")
    if intake.status != IntakeStatus.received:
        raise HTTPException(status_code=409, detail="Only received intake can be reviewed")
    if accept:
        net_quantity = payload.net_quantity_kg or intake.quantity_kg
        if net_quantity > intake.quantity_kg:
            raise HTTPException(
                status_code=422,
                detail="Accepted net weight cannot exceed received gross weight",
            )
        intake.net_quantity_kg = net_quantity
        intake.quality_grade = payload.quality_grade or intake.quality_grade
        intake.status = IntakeStatus.accepted
        action = "produce_intake.accepted"
    else:
        if not payload.reason or len(payload.reason.strip()) < 3:
            raise HTTPException(status_code=422, detail="Rejection reason is required")
        intake.rejection_reason = payload.reason.strip()
        intake.status = IntakeStatus.rejected
        action = "produce_intake.rejected"
    intake.reviewed_by = _actor(current_user)
    intake.reviewed_at = datetime.utcnow()
    db.add(
        AdminAuditLog(
            cooperative_id=cooperative_id,
            actor_id=_actor(current_user),
            action=action,
            resource_type="produce_intake",
            resource_id=str(intake.id),
            details=(
                f"net_quantity_kg={intake.net_quantity_kg}"
                if accept
                else f"reason={intake.rejection_reason}"
            ),
        )
    )
    db.commit()
    db.refresh(intake)
    return intake


@router.post("/{intake_id}/accept", response_model=IntakeResponse)
def accept_intake(
    intake_id: int,
    payload: IntakeReview,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "field_officer", "operations_officer")
    ),
):
    return _review_intake(
        intake_id=intake_id,
        payload=payload,
        accept=True,
        cooperative_id=_scope(current_user, cooperative_id),
        db=db,
        current_user=current_user,
    )


@router.post("/{intake_id}/reject", response_model=IntakeResponse)
def reject_intake(
    intake_id: int,
    payload: IntakeReview,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "field_officer", "operations_officer")
    ),
):
    return _review_intake(
        intake_id=intake_id,
        payload=payload,
        accept=False,
        cooperative_id=_scope(current_user, cooperative_id),
        db=db,
        current_user=current_user,
    )


@router.post("/{intake_id}/cancel", response_model=IntakeResponse)
def cancel_intake(
    intake_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "field_officer", "operations_officer")
    ),
):
    scoped_id = _scope(current_user, cooperative_id)
    intake = (
        db.query(ProduceIntake)
        .filter(
            ProduceIntake.id == intake_id,
            ProduceIntake.cooperative_id == scoped_id,
        )
        .with_for_update()
        .first()
    )
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")
    if intake.status != IntakeStatus.received:
        raise HTTPException(
            status_code=409,
            detail="Only unbatched received intake can be cancelled",
        )
    intake.status = IntakeStatus.cancelled
    db.add(
        AdminAuditLog(
            cooperative_id=scoped_id,
            actor_id=_actor(current_user),
            action="produce_intake.cancelled",
            resource_type="produce_intake",
            resource_id=str(intake.id),
        )
    )
    db.commit()
    db.refresh(intake)
    return intake
