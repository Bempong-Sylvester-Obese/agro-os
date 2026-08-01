"""Aggregation batch lifecycle."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import (
    AdminAuditLog,
    AggregationBatch,
    AggregationBatchStatus,
    IntakeStatus,
    ProduceIntake,
    User,
)
from app.schemas.market import BatchCreate, BatchIntakes, BatchResponse
from app.services.auth_service import get_current_user, require_roles

router = APIRouter(prefix="/aggregation-batches", tags=["aggregation"])


def _scope(user: User | None, cooperative_id: int | None) -> int:
    return resolve_cooperative_scope(
        current_user=user,
        cooperative_id=cooperative_id,
        settings=get_settings(),
    )


def _actor(user: User | None) -> str:
    return str(user.id) if user else "system"


def _get_batch(
    db: Session, batch_id: int, cooperative_id: int, *, lock: bool = False
) -> AggregationBatch:
    query = db.query(AggregationBatch).filter(
        AggregationBatch.id == batch_id,
        AggregationBatch.cooperative_id == cooperative_id,
    )
    batch = query.with_for_update().first() if lock else query.first()
    if not batch:
        raise HTTPException(status_code=404, detail="Aggregation batch not found")
    return batch


@router.post("/", response_model=BatchResponse, status_code=201)
def create_batch(
    payload: BatchCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "field_officer", "operations_officer")
    ),
):
    cooperative_id = _scope(current_user, payload.cooperative_id)
    batch = AggregationBatch(
        cooperative_id=cooperative_id,
        code=payload.code.strip(),
        crop_type=payload.crop_type.strip(),
        created_by=_actor(current_user),
    )
    db.add(batch)
    db.flush()
    db.add(
        AdminAuditLog(
            cooperative_id=cooperative_id,
            actor_id=_actor(current_user),
            action="aggregation_batch.created",
            resource_type="aggregation_batch",
            resource_id=str(batch.id),
            details=f"code={batch.code}",
        )
    )
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/", response_model=list[BatchResponse])
def list_batches(
    cooperative_id: int | None = None,
    status: AggregationBatchStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    scoped_id = _scope(current_user, cooperative_id)
    query = db.query(AggregationBatch).filter(
        AggregationBatch.cooperative_id == scoped_id
    )
    if status is not None:
        query = query.filter(AggregationBatch.status == status)
    return query.order_by(AggregationBatch.created_at.desc()).all()


@router.post("/{batch_id}/intakes", response_model=BatchResponse)
def add_intakes(
    batch_id: int,
    payload: BatchIntakes,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "field_officer", "operations_officer")
    ),
):
    scoped_id = _scope(current_user, cooperative_id)
    batch = _get_batch(db, batch_id, scoped_id, lock=True)
    if batch.status != AggregationBatchStatus.open:
        raise HTTPException(status_code=409, detail="Batch is not open")
    intakes = (
        db.query(ProduceIntake)
        .filter(
            ProduceIntake.id.in_(set(payload.intake_ids)),
            ProduceIntake.cooperative_id == scoped_id,
        )
        .with_for_update()
        .all()
    )
    if len(intakes) != len(set(payload.intake_ids)):
        raise HTTPException(status_code=404, detail="One or more intakes not found")
    for intake in intakes:
        if intake.status != IntakeStatus.accepted:
            raise HTTPException(
                status_code=409,
                detail=f"Intake {intake.id} is not available",
            )
        if intake.crop_type.casefold() != batch.crop_type.casefold():
            raise HTTPException(
                status_code=422,
                detail=f"Intake {intake.id} crop does not match batch",
            )
        intake.aggregation_batch_id = batch.id
        intake.status = IntakeStatus.batched
    batch.total_quantity_kg = sum(
        (Decimal(str(item.net_quantity_kg)) for item in intakes),
        Decimal(str(batch.total_quantity_kg)),
    )
    db.add(
        AdminAuditLog(
            cooperative_id=scoped_id,
            actor_id=_actor(current_user),
            action="aggregation_batch.intakes_added",
            resource_type="aggregation_batch",
            resource_id=str(batch.id),
            details=f"intake_ids={','.join(map(str, sorted(payload.intake_ids)))}",
        )
    )
    db.commit()
    db.refresh(batch)
    return batch


@router.post("/{batch_id}/close", response_model=BatchResponse)
def close_batch(
    batch_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "field_officer", "operations_officer")
    ),
):
    scoped_id = _scope(current_user, cooperative_id)
    batch = _get_batch(db, batch_id, scoped_id, lock=True)
    if batch.status != AggregationBatchStatus.open:
        raise HTTPException(status_code=409, detail="Only an open batch can be closed")
    if Decimal(str(batch.total_quantity_kg)) <= 0:
        raise HTTPException(status_code=409, detail="Cannot close an empty batch")
    batch.status = AggregationBatchStatus.closed
    batch.closed_at = datetime.utcnow()
    db.add(
        AdminAuditLog(
            cooperative_id=scoped_id,
            actor_id=_actor(current_user),
            action="aggregation_batch.closed",
            resource_type="aggregation_batch",
            resource_id=str(batch.id),
        )
    )
    db.commit()
    db.refresh(batch)
    return batch
