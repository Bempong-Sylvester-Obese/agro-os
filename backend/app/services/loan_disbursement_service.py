"""Loan disbursement domain service.

Owns the payout flow (initiate transfer, reconcile provider status, compare-and-set
loan/transaction state). HTTP routes and USSD adapters call into this module; it
never imports from ``app.routes``.
"""
import logging
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import (
    CooperativeMembership as Farmer,
    Loan,
    LoanStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.schemas.schemas import LoanDisbursementStatus
from app.services.loan_ledger import (
    disburse_external_ref,
    latest_loan_transaction,
    loan_transaction_description,
    provider_amount_matches,
)
from app.services.providers.factory import get_payment_provider

logger = logging.getLogger(__name__)


def disbursement_status_response(
    loan: Loan,
    payout: Transaction | None,
) -> LoanDisbursementStatus:
    payout_status = payout.status.value if payout else "none"
    return LoanDisbursementStatus(
        loan_id=loan.id,
        loan_status=loan.status,
        payout_status=payout_status,
        transfer_reference=(payout.provider_transfer_ref if payout else None) or loan.provider_transfer_ref,
        can_cancel=loan.status in (LoanStatus.requested, LoanStatus.approved)
        and (payout is None or payout.status == TransactionStatus.failed),
        can_retry=loan.status == LoanStatus.approved
        and payout is not None
        and payout.status == TransactionStatus.failed,
    )


def apply_disbursement_status(
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
            loan.provider_transfer_ref = tx.provider_transfer_ref
            loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
            db.commit()
        return loan
    if tx.status != TransactionStatus.pending or loan.status != LoanStatus.approved:
        return loan
    if transfer_ref and not tx.provider_transfer_ref:
        tx.provider_transfer_ref = transfer_ref

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
                or "The payment provider reversed the transfer. The loan remains approved and can be retried.",
            )
        return loan

    if status_result["status"] == "pending":
        return loan

    if not provider_amount_matches(loan.amount, status_result.get("amount")):
        raise HTTPException(
            status_code=502,
            detail="Transfer amount mismatch — loan remains approved",
        )

    tx.status = TransactionStatus.completed
    tx.customer_action = "none"
    tx.action_expires_at = None
    loan.status = LoanStatus.disbursed
    loan.provider_transfer_ref = transfer_ref or tx.provider_transfer_ref
    loan.disbursed_at = datetime.utcnow()
    db.commit()
    db.refresh(loan)
    return loan


async def reconcile_disbursement(*, loan: Loan, db: Session) -> tuple[Loan, Transaction | None]:
    """Reconcile the latest payout attempt with the provider and return (loan, payout)."""
    loan_id = loan.id
    payout = latest_loan_transaction(db, loan=loan, transaction_type=TransactionType.payout)
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
            loan.provider_transfer_ref = payout.provider_transfer_ref
            loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
            db.commit()
    if (
        loan.status == LoanStatus.approved
        and payout
        and payout.status == TransactionStatus.pending
        and payout.provider_transfer_ref
    ):
        payout_id = payout.id
        transfer_ref = payout.provider_transfer_ref
        provider = get_payment_provider()
        account_number, wallet_error = await provider.resolve_verified_account(None)
        if wallet_error:
            raise HTTPException(status_code=502, detail=wallet_error)
        status_result = await provider.transfer_status(
            reference=transfer_ref,
            account_number=account_number,
            id_type="2",
        )
        db.expire_all()
        loan = apply_disbursement_status(
            loan_id=loan_id,
            payout_id=payout_id,
            transfer_ref=transfer_ref,
            status_result=status_result,
            db=db,
            raise_on_failed=False,
        )
        payout = db.query(Transaction).filter(Transaction.id == payout_id).one()
    return loan, payout


async def disburse_loan(*, loan: Loan, farmer: Farmer, db: Session) -> Loan:
    """Disburse an approved loan via the payment provider and record the payout.

    The caller is responsible for authorization, scope checks and audit logging.
    """
    loan_id = loan.id
    ext_ref = disburse_external_ref(loan.id)
    provider = get_payment_provider()
    # Always disburse from the platform merchant wallet (MoMo-enabled), not an alternate coop wallet.
    account_number, wallet_error = await provider.resolve_verified_account(None)
    if wallet_error:
        raise HTTPException(status_code=502, detail=wallet_error)

    loan = db.query(Loan).filter(Loan.id == loan_id).with_for_update().one()
    if loan.status != LoanStatus.approved:
        raise HTTPException(
            status_code=409,
            detail=f"Loan changed to '{loan.status}' before payout could start.",
        )
    existing_tx = latest_loan_transaction(
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
        existing_ref = existing_tx.provider_transfer_ref
        db.commit()
        status_result = await provider.transfer_status(
            reference=existing_ref,
            account_number=account_number,
            id_type="2",
        )
        db.expire_all()
        if status_result["status"] == "failed":
            apply_disbursement_status(
                loan_id=loan_id,
                payout_id=existing_id,
                transfer_ref=existing_ref,
                status_result=status_result,
                db=db,
                raise_on_failed=False,
            )
        else:
            return apply_disbursement_status(
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
    latest_tx = latest_loan_transaction(
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
        loan.provider_transfer_ref = latest_tx.provider_transfer_ref
        loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
        db.commit()
        return loan

    attempt_tx = Transaction(
        farmer_id=farmer.id,
        loan_id=loan.id,
        transaction_type=TransactionType.payout,
        amount=loan.amount,
        currency=loan.currency,
        status=TransactionStatus.pending,
        provider_transfer_ref=ext_ref,
        payee_phone=farmer.phone,
        description=loan_transaction_description(loan.id, TransactionType.payout),
    )
    db.add(attempt_tx)
    db.commit()
    db.refresh(attempt_tx)
    attempt_id = attempt_tx.id

    transfer_result = await provider.initiate_transfer(
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
            locked_attempt.provider_transfer_ref = (
                transfer_result.get("provider_transfer_ref")
                or locked_attempt.provider_transfer_ref
            )
            db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Transfer failed: {transfer_result['message']}",
        )

    transfer_ref = transfer_result.get("provider_transfer_ref") or attempt_tx.provider_transfer_ref
    status_result = await provider.transfer_status(
        reference=transfer_ref,
        account_number=account_number,
        id_type="2",
    )
    db.expire_all()
    return apply_disbursement_status(
        loan_id=loan_id,
        payout_id=attempt_id,
        transfer_ref=transfer_ref,
        status_result=status_result,
        db=db,
    )
