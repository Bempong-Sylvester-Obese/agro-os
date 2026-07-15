"""Settlement approval, payout, retry, and reconciliation APIs."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import (
    AdminAuditLog,
    BuyerPaymentReceipt,
    ProduceSale,
    ProduceSaleStatus,
    ReceiptStatus,
    SettlementLine,
    SettlementRun,
    SettlementStatus,
    User,
)
from app.schemas.market import (
    PayoutResult,
    ReconciliationResult,
    SettlementCalculate,
    SettlementResponse,
)
from app.services.auth_service import get_current_user, require_roles
from app.services.communications_service import CommunicationsService
from app.services.settlement_service import SettlementService, money

router = APIRouter(prefix="/settlements", tags=["settlements"])


def _scope(user: User | None, cooperative_id: int | None) -> int:
    return resolve_cooperative_scope(
        current_user=user,
        cooperative_id=cooperative_id,
        settings=get_settings(),
    )


def _actor(user: User | None) -> str:
    return str(user.id) if user else "system"


@router.post(
    "/sales/{sale_id}/calculate",
    response_model=SettlementResponse,
    status_code=201,
)
def calculate_settlement(
    sale_id: int,
    payload: SettlementCalculate,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer")
    ),
):
    return SettlementService.calculate(
        db,
        sale_id=sale_id,
        cooperative_id=_scope(current_user, cooperative_id),
        config=payload,
        actor=current_user,
    )


@router.get("/", response_model=list[SettlementResponse])
def list_settlements(
    cooperative_id: int | None = None,
    status: SettlementStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    scoped_id = _scope(current_user, cooperative_id)
    query = (
        db.query(SettlementRun)
        .options(
            joinedload(SettlementRun.lines).joinedload(
                SettlementLine.deductions
            )
        )
        .filter(SettlementRun.cooperative_id == scoped_id)
    )
    if status is not None:
        query = query.filter(SettlementRun.status == status)
    return query.order_by(SettlementRun.created_at.desc()).all()


@router.get("/{settlement_id}", response_model=SettlementResponse)
def get_settlement(
    settlement_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    return SettlementService.load(
        db, settlement_id, _scope(current_user, cooperative_id)
    )


@router.post("/{settlement_id}/submit", response_model=SettlementResponse)
def submit_settlement(
    settlement_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer")
    ),
):
    scoped_id = _scope(current_user, cooperative_id)
    settlement = (
        db.query(SettlementRun)
        .filter(
            SettlementRun.id == settlement_id,
            SettlementRun.cooperative_id == scoped_id,
        )
        .with_for_update()
        .first()
    )
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    if settlement.status != SettlementStatus.draft:
        raise HTTPException(status_code=409, detail="Only a draft can be submitted")
    settlement.status = SettlementStatus.pending_approval
    settlement.submitted_at = datetime.utcnow()
    db.add(
        AdminAuditLog(
            cooperative_id=scoped_id,
            actor_id=_actor(current_user),
            action="settlement.submitted",
            resource_type="settlement",
            resource_id=str(settlement.id),
        )
    )
    db.commit()
    return SettlementService.load(db, settlement.id, scoped_id)


@router.post("/{settlement_id}/approve", response_model=SettlementResponse)
def approve_settlement(
    settlement_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    scoped_id = _scope(current_user, cooperative_id)
    settlement = (
        db.query(SettlementRun)
        .filter(
            SettlementRun.id == settlement_id,
            SettlementRun.cooperative_id == scoped_id,
        )
        .with_for_update()
        .first()
    )
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    if settlement.status != SettlementStatus.pending_approval:
        raise HTTPException(
            status_code=409,
            detail="Only a submitted settlement can be approved",
        )
    actor = _actor(current_user)
    if actor != "system" and settlement.calculated_by == actor:
        raise HTTPException(
            status_code=409,
            detail="Settlement calculator cannot approve the same settlement",
        )
    verified = money(
        db.query(func.coalesce(func.sum(BuyerPaymentReceipt.amount), 0))
        .filter(
            BuyerPaymentReceipt.sale_id == settlement.sale_id,
            BuyerPaymentReceipt.status == ReceiptStatus.verified,
        )
        .scalar()
    )
    if verified < money(settlement.gross_total):
        raise HTTPException(
            status_code=409,
            detail="Verified buyer funds no longer cover this settlement",
        )
    settlement.status = SettlementStatus.approved
    settlement.approved_by = actor
    settlement.approved_at = datetime.utcnow()
    db.add(
        AdminAuditLog(
            cooperative_id=scoped_id,
            actor_id=actor,
            action="settlement.approved",
            resource_type="settlement",
            resource_id=str(settlement.id),
            details=f"net_total={settlement.net_total}",
        )
    )
    db.commit()
    return SettlementService.load(db, settlement.id, scoped_id)


@router.post("/{settlement_id}/disburse", response_model=PayoutResult)
async def disburse_settlement(
    settlement_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer")
    ),
):
    settlement, batch, attempted = await SettlementService.disburse(
        db,
        settlement_id=settlement_id,
        cooperative_id=_scope(current_user, cooperative_id),
        actor=current_user,
        retry_failed=False,
    )
    return PayoutResult(
        settlement=settlement,
        disbursement_batch=batch,
        attempted_line_ids=attempted,
    )


@router.post("/{settlement_id}/retry-failed", response_model=PayoutResult)
async def retry_failed_settlement_lines(
    settlement_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer")
    ),
):
    settlement, batch, attempted = await SettlementService.disburse(
        db,
        settlement_id=settlement_id,
        cooperative_id=_scope(current_user, cooperative_id),
        actor=current_user,
        retry_failed=True,
    )
    return PayoutResult(
        settlement=settlement,
        disbursement_batch=batch,
        attempted_line_ids=attempted,
    )


@router.post("/{settlement_id}/reconcile", response_model=ReconciliationResult)
async def reconcile_settlement(
    settlement_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer")
    ),
):
    scoped_id = _scope(current_user, cooperative_id)
    before = {
        line.id
        for line in db.query(SettlementLine)
        .filter(
            SettlementLine.settlement_run_id == settlement_id,
            SettlementLine.paid_at.is_not(None),
        )
        .all()
    }
    settlement, reconciled = await SettlementService.reconcile(
        db,
        settlement_id=settlement_id,
        cooperative_id=scoped_id,
        actor=current_user,
    )
    newly_paid = [
        line
        for line in settlement.lines
        if line.id not in before and line.paid_at is not None
    ]
    communications = CommunicationsService()
    for line in newly_paid:
        try:
            await communications.send_settlement_statement(
                settlement=settlement,
                line=line,
                db=db,
                sent_by=_actor(current_user),
            )
        except Exception:
            # The settled payment remains authoritative; failed SMS is logged
            # independently and can be retried without changing finance state.
            pass
    if settlement.status == SettlementStatus.completed:
        sale = (
            db.query(ProduceSale)
            .filter(ProduceSale.id == settlement.sale_id)
            .with_for_update()
            .one()
        )
        sale.status = ProduceSaleStatus.settled
        db.commit()
    return ReconciliationResult(
        settlement=settlement,
        reconciled_line_ids=reconciled,
    )
