"""Loan Management Routes"""

import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.dependencies.cooperative_scope import CooperativeScope, require_cooperative_scope, resolve_cooperative_scope
from app.models.models import (
    AdminAuditLog,
    Loan,
    LoanReminder,
    LoanStatus,
    TransactionStatus,
    TransactionType,
    User,
)
from app.models.models import (
    CooperativeMembership as Farmer,
)
from app.schemas.schemas import (
    LoanApproval,
    LoanCancel,
    LoanCreate,
    LoanDisbursementStatus,
    LoanRejection,
    LoanReminderResponse,
    LoanResponse,
)
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)
from app.services.communications_service import CommunicationsService
from app.services.loan_disbursement_service import (
    disburse_loan as disburse_loan_service,
    disbursement_status_response,
    reconcile_disbursement,
)
from app.services.loan_ledger import latest_loan_transaction as _latest_loan_transaction
from app.services.loan_repayment_service import start_farmer_loan_repayment

router = APIRouter(prefix="/loans", tags=["loans"])
logger = logging.getLogger(__name__)


def _get_loan_or_404(
    loan_id: int,
    db: Session,
    current_user: User | None = None,
    *,
    lock: bool = False,
) -> Loan:
    query = db.query(Loan).filter(Loan.id == loan_id)
    if lock:
        query = query.with_for_update()
    loan = query.first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Loan not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)
    return loan


def _audit_loan_action(
    db: Session,
    *,
    loan: Loan,
    current_user: User | None,
    action: str,
    details: str | None = None,
) -> None:
    if current_user is None:
        return
    db.add(
        AdminAuditLog(
            cooperative_id=loan.farmer.cooperative_id,
            actor_id=str(current_user.id),
            action=action,
            resource_type="loan",
            resource_id=str(loan.id),
            details=details,
        )
    )


@router.post("/", response_model=LoanResponse, status_code=201, include_in_schema=False)
def create_loan(
    loan_in: LoanCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Legacy local-development fixture; production requests originate via USSD."""
    settings = get_settings()
    if current_user is not None or settings.app_env.lower() not in ("test", "testing"):
        raise HTTPException(
            status_code=403,
            detail="Loan requests must be submitted by the farmer through USSD.",
        )
    farmer = db.query(Farmer).filter(Farmer.id == loan_in.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)

    loan = Loan(**loan_in.model_dump(), request_channel="legacy_api")
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.get("/", response_model=list[LoanResponse])
def list_loans(
    farmer_id: int | None = None,
    status: LoanStatus | None = None,
    cooperative_id: int | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
    cooperative_scope: CooperativeScope | None = Depends(require_cooperative_scope),
):
    """List loans with optional filters."""
    settings = get_settings()
    scoped_coop_id = resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=cooperative_id,
        settings=settings,
    )
    query = (
        db.query(Loan)
        .options(joinedload(Loan.reminders))
        .join(Farmer, Loan.farmer_id == Farmer.id)
        .filter(Farmer.cooperative_id == scoped_coop_id)
    )
    if farmer_id is not None:
        query = query.filter(Loan.farmer_id == farmer_id)
    if status is not None:
        query = query.filter(Loan.status == status)
    return query.order_by(Loan.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{loan_id}", response_model=LoanResponse)
def get_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
    cooperative_scope: CooperativeScope | None = Depends(require_cooperative_scope),
):
    """Get loan details."""
    return _get_loan_or_404(loan_id, db, current_user)


@router.get("/{loan_id}/reminders", response_model=list[LoanReminderResponse])
def list_loan_reminders(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
    cooperative_scope: CooperativeScope | None = Depends(require_cooperative_scope),
):
    _get_loan_or_404(loan_id, db, current_user)
    return (
        db.query(LoanReminder)
        .filter(LoanReminder.loan_id == loan_id)
        .order_by(LoanReminder.created_at.desc())
        .all()
    )


@router.post("/{loan_id}/reminders", response_model=LoanReminderResponse)
async def send_loan_reminder(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    loan = _get_loan_or_404(loan_id, db, current_user)
    if loan.status != LoanStatus.disbursed:
        raise HTTPException(
            status_code=409,
            detail="Repayment reminders are only available for disbursed loans.",
        )
    if not loan.expected_repayment_date:
        raise HTTPException(status_code=409, detail="Loan has no repayment due date.")
    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    reminder = await CommunicationsService().send_loan_repayment_reminder(
        loan=loan,
        farmer=farmer,
        reminder_kind="manual",
        scheduled_for=date.today(),
        db=db,
        manual=True,
        sent_by=str(current_user.id) if current_user else None,
    )
    _audit_loan_action(
        db,
        loan=loan,
        current_user=current_user,
        action="loan.reminder_sent",
        details=f"reminder_id={reminder.id};status={reminder.status}",
    )
    db.commit()
    if reminder.status != "sent":
        raise HTTPException(status_code=502, detail=reminder.error or "Reminder failed")
    return reminder


@router.post("/{loan_id}/approve", response_model=LoanResponse)
def approve_loan(
    loan_id: int,
    approval: LoanApproval = Body(default_factory=LoanApproval),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Approve a requested loan."""
    loan = _get_loan_or_404(loan_id, db, current_user, lock=True)
    if loan.status != LoanStatus.requested:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve loan in '{loan.status}' state. Must be 'requested'.",
        )
    repayment_date = approval.expected_repayment_date
    if repayment_date is None:
        if get_settings().app_env.lower() not in ("test", "testing"):
            raise HTTPException(
                status_code=422,
                detail="Expected repayment date is required.",
            )
        repayment_date = date.today() + timedelta(days=30)
    if repayment_date <= date.today():
        raise HTTPException(
            status_code=422,
            detail="Expected repayment date must be in the future.",
        )
    loan.status = LoanStatus.approved
    loan.expected_repayment_date = repayment_date
    loan.approved_by = str(current_user.id) if current_user is not None else "system"
    loan.approved_at = datetime.utcnow()
    _audit_loan_action(
        db,
        loan=loan,
        current_user=current_user,
        action="loan.approved",
        details=f"amount={loan.amount}",
    )
    db.commit()
    db.refresh(loan)
    return loan


@router.post("/{loan_id}/reject", response_model=LoanResponse)
async def reject_loan(
    loan_id: int,
    rejection: LoanRejection,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Reject a requested loan."""
    loan = _get_loan_or_404(loan_id, db, current_user)
    if loan.status != LoanStatus.requested:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject loan in '{loan.status}' state.",
        )
    loan.status = LoanStatus.rejected
    loan.rejection_reason = rejection.reason.strip()
    loan.rejected_by = str(current_user.id) if current_user is not None else "system"
    loan.rejected_at = datetime.utcnow()
    _audit_loan_action(
        db,
        loan=loan,
        current_user=current_user,
        action="loan.rejected",
        details=f"reason={loan.rejection_reason}",
    )
    db.commit()
    db.refresh(loan)
    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    try:
        result = await CommunicationsService().send_loan_rejection(
            loan=loan,
            farmer=farmer,
            reason=loan.rejection_reason,
            db=db,
            sent_by=str(current_user.id) if current_user else None,
        )
        loan.notification_status = "sent" if result["success"] else "failed"
    except Exception:
        logger.exception("Could not send rejection SMS for loan %s", loan.id)
        loan.notification_status = "failed"
    return loan


@router.post("/{loan_id}/cancel", response_model=LoanResponse)
def cancel_loan(
    loan_id: int,
    body: LoanCancel,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Cancel a loan only while no payout is in flight or completed."""
    loan = _get_loan_or_404(loan_id, db, current_user)
    loan = db.query(Loan).filter(Loan.id == loan_id).with_for_update().one()
    if loan.status not in (LoanStatus.requested, LoanStatus.approved):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel loan in '{loan.status}' state.",
        )

    payout = _latest_loan_transaction(
        db,
        loan=loan,
        transaction_type=TransactionType.payout,
    )
    if payout and payout.status == TransactionStatus.pending:
        raise HTTPException(
            status_code=409,
            detail="Payout is still processing. Check its transfer status before cancelling.",
        )
    if payout and payout.status == TransactionStatus.completed:
        loan.status = LoanStatus.disbursed
        loan.provider_transfer_ref = payout.provider_transfer_ref
        loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="Payout already completed; the loan cannot be cancelled.",
        )

    loan.status = LoanStatus.cancelled
    loan.cancelled_by = current_user.email if current_user else "system"
    loan.cancelled_at = datetime.utcnow()
    loan.cancellation_reason = body.reason.strip()
    _audit_loan_action(
        db,
        loan=loan,
        current_user=current_user,
        action="loan.cancelled",
        details=f"reason={loan.cancellation_reason}",
    )
    db.commit()
    db.refresh(loan)
    return loan


@router.get("/{loan_id}/disbursement-status", response_model=LoanDisbursementStatus)
async def get_disbursement_status(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Reconcile the latest payout attempt and return safe operator actions."""
    loan = _get_loan_or_404(loan_id, db, current_user)
    loan, payout = await reconcile_disbursement(loan=loan, db=db)
    return disbursement_status_response(loan, payout)


@router.post("/{loan_id}/disburse", response_model=LoanResponse)
async def disburse_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """
    Disburse an approved loan by triggering a provider transfer to the farmer's phone.
    Marks loan as 'disbursed' and creates a payout Transaction record.
    """
    loan = _get_loan_or_404(loan_id, db, current_user)
    if loan.status == LoanStatus.disbursed:
        return loan
    if loan.status != LoanStatus.approved:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot disburse loan in '{loan.status}' state. Must be 'approved'.",
        )

    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    _audit_loan_action(
        db,
        loan=loan,
        current_user=current_user,
        action="loan.disbursement_requested",
        details=f"amount={loan.amount}",
    )
    db.commit()

    return await disburse_loan_service(loan=loan, farmer=farmer, db=db)


@router.post("/{loan_id}/repay", response_model=LoanResponse, include_in_schema=False)
async def legacy_repay_loan_fixture(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Test-only compatibility fixture; production repayment starts on USSD."""
    settings = get_settings()
    if current_user is not None or settings.app_env.lower() not in ("test", "testing"):
        raise HTTPException(
            status_code=403,
            detail="Loan repayments must be initiated by the farmer through USSD.",
        )
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    return await start_farmer_loan_repayment(
        loan_id=loan_id,
        farmer=farmer,
        db=db,
        initiation_channel="test_fixture",
    )
