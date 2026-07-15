"""Loan Management Routes"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import (
    AdminAuditLog,
    Cooperative,
    Loan,
    LoanStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)
from app.models.models import (
    CooperativeMembership as Farmer,
)
from app.routes.transactions import (
    CUSTOMER_ACTION_TTL,
    INITIATING_ACTION_TTL,
    PROCESSING_ACTION_TTL,
    expire_customer_actions,
)
from app.schemas.schemas import (
    LoanCancel,
    LoanCreate,
    LoanDisbursementStatus,
    LoanResponse,
)
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)
from app.services.communications_service import CommunicationsService
from app.services.moolre_service import MoolreService
from app.services.trust_score_service import TrustScoreService

router = APIRouter(prefix="/loans", tags=["loans"])
logger = logging.getLogger(__name__)


def _disburse_external_ref(loan_id: int) -> str:
    """Return Moolre's required numeric reference for each payout attempt.

    Moolre coerces alphanumeric references to ``0``, which makes separate
    attempts indistinguishable in its ledger. Keep this to 12 numeric digits,
    matching the format used by Moolre's own transfer examples.
    """
    loan_prefix = str(loan_id % 100).zfill(2)
    random_suffix = str(uuid.uuid4().int % 10_000_000_000).zfill(10)
    return f"{loan_prefix}{random_suffix}"


def _repay_external_ref(loan_id: int) -> str:
    return f"agro-loan-repay-{loan_id}-{uuid.uuid4().hex[:8]}"


def _provider_amount_matches(expected: float, provider_amount) -> bool:
    if provider_amount is None or provider_amount == "":
        return False
    try:
        return abs(float(provider_amount) - float(expected)) < 0.01
    except (TypeError, ValueError):
        return False


def _get_loan_or_404(
    loan_id: int, db: Session, current_user: User | None = None
) -> Loan:
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Loan not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)
    return loan


def _cooperative_account(farmer: Farmer, db: Session) -> str | None:
    """Return the cooperative Moolre wallet when configured."""
    cooperative = db.query(Cooperative).filter(Cooperative.id == farmer.cooperative_id).first()
    return cooperative.moolre_account_number if cooperative else None


def _latest_loan_transaction(
    db: Session,
    *,
    loan: Loan,
    transaction_type: TransactionType,
    lock: bool = False,
) -> Transaction | None:
    query = (
        db.query(Transaction)
        .filter(
            Transaction.farmer_id == loan.farmer_id,
            Transaction.transaction_type == transaction_type,
            Transaction.description == f"Loan {'disbursement' if transaction_type == TransactionType.payout else 'repayment'} #{loan.id}",
        )
        .order_by(Transaction.created_at.desc())
    )
    if lock:
        query = query.with_for_update()
    return query.first()


def _disbursement_status_response(
    loan: Loan,
    payout: Transaction | None,
) -> LoanDisbursementStatus:
    payout_status = payout.status.value if payout else "none"
    return LoanDisbursementStatus(
        loan_id=loan.id,
        loan_status=loan.status,
        payout_status=payout_status,
        transfer_reference=(payout.moolre_transfer_ref if payout else None) or loan.moolre_transfer_ref,
        can_cancel=loan.status in (LoanStatus.requested, LoanStatus.approved)
        and (payout is None or payout.status == TransactionStatus.failed),
        can_retry=loan.status == LoanStatus.approved
        and payout is not None
        and payout.status == TransactionStatus.failed,
    )


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


def _apply_disbursement_status(
    *,
    loan_id: int,
    payout_id: int,
    transfer_ref: str | None,
    status_result: dict,
    db: Session,
    raise_on_failed: bool = True,
) -> Loan:
    """Compare-and-set a provider result without regressing terminal state."""
    loan = db.query(Loan).filter(Loan.id == loan_id).with_for_update().one()
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == payout_id)
        .with_for_update()
        .one()
    )
    if loan.status == LoanStatus.disbursed or tx.status == TransactionStatus.completed:
        if tx.status == TransactionStatus.completed and loan.status == LoanStatus.approved:
            loan.status = LoanStatus.disbursed
            loan.moolre_transfer_ref = tx.moolre_transfer_ref
            loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
            db.commit()
        return loan
    if tx.status != TransactionStatus.pending or loan.status != LoanStatus.approved:
        return loan
    if transfer_ref and not tx.moolre_transfer_ref:
        tx.moolre_transfer_ref = transfer_ref

    if status_result["status"] == "failed":
        tx.status = TransactionStatus.failed
        tx.customer_action = "none"
        tx.action_expires_at = None
        db.commit()
        if raise_on_failed:
            provider_message = (status_result.get("raw") or {}).get("message")
            raise HTTPException(
                status_code=502,
                detail=provider_message
                or "Moolre reversed the transfer. The loan remains approved and can be retried.",
            )
        return loan

    if status_result["status"] == "pending":
        return loan

    if not _provider_amount_matches(loan.amount, status_result.get("amount")):
        raise HTTPException(
            status_code=502,
            detail="Moolre transfer amount mismatch — loan remains approved",
        )

    tx.status = TransactionStatus.completed
    tx.customer_action = "none"
    tx.action_expires_at = None
    loan.status = LoanStatus.disbursed
    loan.moolre_transfer_ref = transfer_ref or tx.moolre_transfer_ref
    loan.disbursed_at = datetime.utcnow()
    db.commit()
    db.refresh(loan)
    return loan


async def _finalize_repayment(
    *,
    loan: Loan,
    tx: Transaction,
    status_result: dict,
    db: Session,
) -> Loan:
    db.expire_all()
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == tx.id)
        .with_for_update()
        .one()
    )
    loan = (
        db.query(Loan).filter(Loan.id == loan.id).with_for_update().one()
    )
    if tx.status == TransactionStatus.completed or loan.status == LoanStatus.repaid:
        return loan
    if status_result["status"] == "failed":
        tx.status = TransactionStatus.failed
        tx.customer_action = "none"
        tx.action_expires_at = None
        db.commit()
        raise HTTPException(status_code=502, detail="Moolre repayment collection failed reconciliation")

    if status_result["status"] == "pending":
        if tx.customer_action in ("initiating", "processing_otp"):
            tx.action_expires_at = datetime.utcnow() + INITIATING_ACTION_TTL
            db.commit()
        db.refresh(loan)
        return loan

    if not _provider_amount_matches(loan.amount, status_result.get("amount")):
        db.refresh(loan)
        raise HTTPException(
            status_code=502,
            detail="Moolre repayment amount mismatch — loan remains disbursed",
        )

    tx.status = TransactionStatus.completed
    tx.customer_action = "none"
    tx.action_expires_at = None
    loan.status = LoanStatus.repaid
    loan.repaid_at = datetime.utcnow()
    db.commit()

    TrustScoreService.calculate_trust_score(loan.farmer_id, db)

    db.refresh(loan)
    return loan


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
):
    """List loans with optional filters."""
    settings = get_settings()
    scoped_coop_id = resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=cooperative_id,
        settings=settings,
    )
    query = db.query(Loan).join(Farmer, Loan.farmer_id == Farmer.id).filter(
        Farmer.cooperative_id == scoped_coop_id
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
):
    """Get loan details."""
    return _get_loan_or_404(loan_id, db, current_user)


@router.post("/{loan_id}/approve", response_model=LoanResponse)
def approve_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Approve a requested loan."""
    loan = _get_loan_or_404(loan_id, db, current_user)
    if loan.status != LoanStatus.requested:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve loan in '{loan.status}' state. Must be 'requested'.",
        )
    loan.status = LoanStatus.approved
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
def reject_loan(
    loan_id: int,
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
    _audit_loan_action(
        db,
        loan=loan,
        current_user=current_user,
        action="loan.rejected",
    )
    db.commit()
    db.refresh(loan)
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
            detail="Payout is still processing. Check its Moolre status before cancelling.",
        )
    if payout and payout.status == TransactionStatus.completed:
        loan.status = LoanStatus.disbursed
        loan.moolre_transfer_ref = payout.moolre_transfer_ref
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
    payout = _latest_loan_transaction(
        db,
        loan=loan,
        transaction_type=TransactionType.payout,
    )
    if (
        loan.status == LoanStatus.approved
        and payout
        and payout.status == TransactionStatus.completed
    ):
        loan = db.query(Loan).filter(Loan.id == loan_id).with_for_update().one()
        payout = (
            db.query(Transaction)
            .filter(Transaction.id == payout.id)
            .with_for_update()
            .one()
        )
        if loan.status == LoanStatus.approved and payout.status == TransactionStatus.completed:
            loan.status = LoanStatus.disbursed
            loan.moolre_transfer_ref = payout.moolre_transfer_ref
            loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
            db.commit()
    if (
        loan.status == LoanStatus.approved
        and payout
        and payout.status == TransactionStatus.pending
        and payout.moolre_transfer_ref
    ):
        payout_id = payout.id
        transfer_ref = payout.moolre_transfer_ref
        moolre = MoolreService()
        account_number, wallet_error = await moolre.resolve_verified_account(None)
        if wallet_error:
            raise HTTPException(status_code=502, detail=wallet_error)
        status_result = await moolre.transfer_status(
            reference=transfer_ref,
            account_number=account_number,
            id_type="2",
        )
        db.expire_all()
        loan = _apply_disbursement_status(
            loan_id=loan_id,
            payout_id=payout_id,
            transfer_ref=transfer_ref,
            status_result=status_result,
            db=db,
            raise_on_failed=False,
        )
        payout = db.query(Transaction).filter(Transaction.id == payout_id).one()
    return _disbursement_status_response(loan, payout)


@router.post("/{loan_id}/disburse", response_model=LoanResponse)
async def disburse_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """
    Disburse an approved loan by triggering a Moolre transfer to the farmer's phone.
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

    ext_ref = _disburse_external_ref(loan.id)
    moolre = MoolreService()
    # Always disburse from the platform merchant wallet (MoMo-enabled), not an alternate coop wallet.
    account_number, wallet_error = await moolre.resolve_verified_account(None)
    if wallet_error:
        raise HTTPException(status_code=502, detail=wallet_error)

    loan = db.query(Loan).filter(Loan.id == loan_id).with_for_update().one()
    if loan.status != LoanStatus.approved:
        raise HTTPException(
            status_code=409,
            detail=f"Loan changed to '{loan.status}' before payout could start.",
        )
    existing_tx = _latest_loan_transaction(
        db,
        loan=loan,
        transaction_type=TransactionType.payout,
        lock=True,
    )
    if existing_tx and existing_tx.status == TransactionStatus.completed:
        loan.status = LoanStatus.disbursed
        loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
        db.commit()
        db.refresh(loan)
        return loan

    if existing_tx and existing_tx.status == TransactionStatus.pending:
        existing_id = existing_tx.id
        existing_ref = existing_tx.moolre_transfer_ref
        db.commit()
        status_result = await moolre.transfer_status(
            reference=existing_ref,
            account_number=account_number,
            id_type="2",
        )
        db.expire_all()
        if status_result["status"] == "failed":
            _apply_disbursement_status(
                loan_id=loan_id,
                payout_id=existing_id,
                transfer_ref=existing_ref,
                status_result=status_result,
                db=db,
                raise_on_failed=False,
            )
        else:
            return _apply_disbursement_status(
                loan_id=loan_id,
                payout_id=existing_id,
                transfer_ref=existing_ref,
                status_result=status_result,
                db=db,
            )

    loan = db.query(Loan).filter(Loan.id == loan_id).with_for_update().one()
    if loan.status != LoanStatus.approved:
        if loan.status == LoanStatus.disbursed:
            return loan
        raise HTTPException(
            status_code=409,
            detail=f"Loan changed to '{loan.status}' before payout could start.",
        )
    latest_tx = _latest_loan_transaction(
        db,
        loan=loan,
        transaction_type=TransactionType.payout,
        lock=True,
    )
    if latest_tx and latest_tx.status == TransactionStatus.pending:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A payout is already processing. Reconcile it before retrying.",
        )
    if latest_tx and latest_tx.status == TransactionStatus.completed:
        loan.status = LoanStatus.disbursed
        loan.moolre_transfer_ref = latest_tx.moolre_transfer_ref
        loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
        db.commit()
        return loan

    attempt_tx = Transaction(
        farmer_id=farmer.id,
        transaction_type=TransactionType.payout,
        amount=loan.amount,
        currency=loan.currency,
        status=TransactionStatus.pending,
        moolre_transfer_ref=ext_ref,
        payee_phone=farmer.phone,
        description=f"Loan disbursement #{loan.id}",
    )
    db.add(attempt_tx)
    db.commit()
    db.refresh(attempt_tx)
    attempt_id = attempt_tx.id

    transfer_result = await moolre.initiate_transfer(
        receiver_phone=farmer.phone,
        amount=loan.amount,
        currency=loan.currency,
        external_ref=ext_ref,
        reference=f"AgroOS loan #{loan.id}",
        account_number=account_number,
    )

    if not transfer_result["success"]:
        db.expire_all()
        locked_attempt = (
            db.query(Transaction)
            .filter(Transaction.id == attempt_id)
            .with_for_update()
            .one()
        )
        if locked_attempt.status == TransactionStatus.pending:
            locked_attempt.status = TransactionStatus.failed
            locked_attempt.moolre_transfer_ref = (
                transfer_result.get("moolre_transfer_ref")
                or locked_attempt.moolre_transfer_ref
            )
            db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Moolre transfer failed: {transfer_result['message']}",
        )

    transfer_ref = transfer_result.get("moolre_transfer_ref") or attempt_tx.moolre_transfer_ref
    status_result = await moolre.transfer_status(
        reference=transfer_ref,
        account_number=account_number,
        id_type="2",
    )
    db.expire_all()
    return _apply_disbursement_status(
        loan_id=loan_id,
        payout_id=attempt_id,
        transfer_ref=transfer_ref,
        status_result=status_result,
        db=db,
    )


@router.post("/{loan_id}/repay", response_model=LoanResponse)
async def repay_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """
    Initiate Moolre collection for loan repayment.
    Marks the loan repaid only after payment_status confirms the collection.
    """
    loan = _get_loan_or_404(loan_id, db, current_user)
    if loan.status == LoanStatus.repaid:
        return loan
    if loan.status != LoanStatus.disbursed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot repay loan in '{loan.status}' state. Must be 'disbursed'.",
        )

    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    moolre = MoolreService()
    account_number = _cooperative_account(farmer, db)

    expire_customer_actions(db, farmer_id=farmer.id)
    loan = (
        db.query(Loan)
        .filter(Loan.id == loan_id)
        .with_for_update()
        .one()
    )
    existing_tx = _latest_loan_transaction(db, loan=loan, transaction_type=TransactionType.repayment)
    if existing_tx and existing_tx.status == TransactionStatus.pending:
        if existing_tx.customer_action == "none":
            # Retire attempts created before explicit initiation states existed.
            existing_tx.status = TransactionStatus.failed
            db.commit()
            existing_tx = None
        elif existing_tx.customer_action == "otp":
            return loan
        elif existing_tx.customer_action in ("initiating", "processing_otp"):
            if (
                existing_tx.action_expires_at
                and existing_tx.action_expires_at > datetime.utcnow()
            ):
                return loan
        if existing_tx is not None:
            status_result = await moolre.payment_status(
                external_ref=existing_tx.moolre_reference,
                account_number=account_number,
            )
            return await _finalize_repayment(
                loan=loan,
                tx=existing_tx,
                status_result=status_result,
                db=db,
            )

    ext_ref = _repay_external_ref(loan.id)
    _audit_loan_action(
        db,
        loan=loan,
        current_user=current_user,
        action="loan.repayment_requested",
        details=f"amount={loan.amount}",
    )
    tx = Transaction(
        farmer_id=loan.farmer_id,
        loan_id=loan.id,
        transaction_type=TransactionType.repayment,
        amount=loan.amount,
        currency=loan.currency,
        status=TransactionStatus.pending,
        moolre_reference=ext_ref,
        payer_phone=farmer.phone,
        description=f"Loan repayment #{loan.id}",
        initiation_channel="dashboard",
        customer_action="initiating",
        action_expires_at=datetime.utcnow() + INITIATING_ACTION_TTL,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    try:
        payment_result = await moolre.initiate_payment(
            payer_phone=farmer.phone,
            amount=loan.amount,
            currency=loan.currency,
            external_ref=ext_ref,
            reference=f"Loan repayment #{loan.id}",
            account_number=account_number,
        )
    except Exception:
        # Preserve ambiguous attempts for status reconciliation. A retry must
        # never generate a fresh reference until this one is terminal.
        raise

    db.expire_all()
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == tx.id)
        .with_for_update()
        .one()
    )
    loan = db.query(Loan).filter(Loan.id == loan_id).with_for_update().one()
    if tx.status == TransactionStatus.completed or loan.status == LoanStatus.repaid:
        return loan

    if not payment_result["success"] and not payment_result.get("verification_required"):
        tx.status = TransactionStatus.failed
        tx.customer_action = "none"
        tx.action_expires_at = None
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Moolre repayment collection failed: {payment_result['message']}",
        )

    tx.customer_action = (
        "otp" if payment_result.get("verification_required") else "approval"
    )
    tx.action_expires_at = datetime.utcnow() + CUSTOMER_ACTION_TTL
    db.commit()

    if payment_result.get("verification_required"):
        try:
            await CommunicationsService().send_payment_action_required(
                farmer=farmer,
                amount=loan.amount,
                reference=tx.moolre_reference,
                db=db,
                sent_by=str(current_user.id) if current_user else None,
            )
        except Exception as exc:
            logger.warning(
                "Could not send repayment-action SMS for transaction %s: %s",
                tx.id,
                exc,
            )
        return loan

    status_result = await moolre.payment_status(
        external_ref=payment_result.get("external_ref") or ext_ref,
        account_number=account_number,
    )
    return await _finalize_repayment(loan=loan, tx=tx, status_result=status_result, db=db)


async def resume_loan_repayment_customer_action(
    *,
    transaction: Transaction,
    farmer: Farmer,
    otp_code: str,
    db: Session,
) -> Loan:
    """Resume an OTP-gated loan repayment from the payer's USSD session."""
    now = datetime.utcnow()
    locked_transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction.id,
            Transaction.farmer_id == farmer.id,
        )
        .with_for_update()
        .first()
    )
    if not locked_transaction:
        raise HTTPException(status_code=404, detail="Pending payment not found")
    if locked_transaction.transaction_type != TransactionType.repayment:
        raise HTTPException(status_code=409, detail="Pending payment is not a repayment")
    if (
        locked_transaction.status != TransactionStatus.pending
        or locked_transaction.customer_action != "otp"
    ):
        raise HTTPException(status_code=409, detail="Repayment is not awaiting OTP")
    if (
        not locked_transaction.action_expires_at
        or locked_transaction.action_expires_at <= now
    ):
        locked_transaction.status = TransactionStatus.failed
        locked_transaction.customer_action = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Repayment verification has expired")

    loan = (
        db.query(Loan)
        .filter(Loan.id == locked_transaction.loan_id, Loan.farmer_id == farmer.id)
        .first()
    )
    if not loan or loan.status != LoanStatus.disbursed:
        raise HTTPException(status_code=409, detail="Loan is not awaiting repayment")

    locked_transaction.customer_action = "processing_otp"
    locked_transaction.action_expires_at = now + PROCESSING_ACTION_TTL
    db.commit()

    transaction_id = locked_transaction.id
    ext_ref = locked_transaction.moolre_reference or _repay_external_ref(loan.id)
    moolre = MoolreService()
    account_number = _cooperative_account(farmer, db)
    payment_result = await moolre.initiate_payment(
        payer_phone=farmer.phone,
        amount=loan.amount,
        currency=loan.currency,
        external_ref=ext_ref,
        otpcode=otp_code,
        reference=f"Loan repayment #{loan.id}",
        account_number=account_number,
    )

    db.expire_all()
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .with_for_update()
        .one()
    )
    loan = db.query(Loan).filter(Loan.id == loan.id).first()
    if transaction.status == TransactionStatus.completed:
        return loan

    if not payment_result["success"] and not payment_result.get("verification_required"):
        transaction.status = TransactionStatus.failed
        transaction.customer_action = "none"
        transaction.action_expires_at = None
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Moolre repayment verification failed: {payment_result['message']}",
        )

    if payment_result.get("verification_required"):
        transaction.customer_action = "otp"
        transaction.action_expires_at = datetime.utcnow() + CUSTOMER_ACTION_TTL
        db.commit()
        return loan

    transaction.customer_action = "approval"
    transaction.action_expires_at = datetime.utcnow() + CUSTOMER_ACTION_TTL
    db.commit()

    status_result = await moolre.payment_status(
        external_ref=payment_result.get("external_ref") or ext_ref,
        account_number=account_number,
    )
    return await _finalize_repayment(
        loan=loan,
        tx=transaction,
        status_result=status_result,
        db=db,
    )
