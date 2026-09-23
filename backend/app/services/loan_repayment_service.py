"""Loan repayment domain service.

Owns farmer-initiated repayment (collection) including OTP resumption and
provider reconciliation. Shared by the HTTP routes and every USSD gateway; it
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
from app.services.communications_service import CommunicationsService
from app.services.customer_action_service import (
    CUSTOMER_ACTION_TTL,
    INITIATING_ACTION_TTL,
    PROCESSING_ACTION_TTL,
    expire_customer_actions,
)
from app.services.loan_ledger import (
    cooperative_account,
    latest_loan_transaction,
    loan_transaction_description,
    provider_amount_matches,
    repay_external_ref,
)
from app.services.providers.factory import get_payment_provider
from app.services.trust_score_service import TrustScoreService

logger = logging.getLogger(__name__)

__all__ = [
    "finalize_repayment",
    "resume_loan_repayment_customer_action",
    "start_farmer_loan_repayment",
]


async def finalize_repayment(
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
        raise HTTPException(status_code=502, detail="Repayment collection failed reconciliation")

    if status_result["status"] == "pending":
        if tx.customer_action in ("initiating", "processing_otp"):
            tx.action_expires_at = datetime.utcnow() + INITIATING_ACTION_TTL
            db.commit()
        db.refresh(loan)
        return loan

    if not provider_amount_matches(loan.amount, status_result.get("amount")):
        db.refresh(loan)
        raise HTTPException(
            status_code=502,
            detail="Repayment amount mismatch — loan remains disbursed",
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


async def start_farmer_loan_repayment(
    *,
    loan_id: int,
    farmer: Farmer,
    db: Session,
    initiation_channel: str,
):
    """Start a repayment selected by the authenticated farmer's phone channel."""
    loan = db.query(Loan).filter(
        Loan.id == loan_id,
        Loan.farmer_id == farmer.id,
    ).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.status == LoanStatus.repaid:
        return loan
    if loan.status != LoanStatus.disbursed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot repay loan in '{loan.status}' state. Must be 'disbursed'.",
        )

    provider = get_payment_provider()
    account_number = cooperative_account(farmer, db)

    expire_customer_actions(db, loan_id=loan.id)
    loan = (
        db.query(Loan)
        .filter(Loan.id == loan_id)
        .with_for_update()
        .one()
    )
    existing_tx = latest_loan_transaction(db, loan=loan, transaction_type=TransactionType.repayment)
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
            status_result = await provider.payment_status(
                external_ref=existing_tx.provider_payment_ref,
                account_number=account_number,
            )
            return await finalize_repayment(
                loan=loan,
                tx=existing_tx,
                status_result=status_result,
                db=db,
            )

    ext_ref = repay_external_ref(loan.id)
    tx = Transaction(
        farmer_id=loan.farmer_id,
        loan_id=loan.id,
        transaction_type=TransactionType.repayment,
        amount=loan.amount,
        currency=loan.currency,
        status=TransactionStatus.pending,
        provider_payment_ref=ext_ref,
        payer_phone=farmer.phone,
        description=loan_transaction_description(loan.id, TransactionType.repayment),
        initiation_channel=initiation_channel,
        customer_action="initiating",
        action_expires_at=datetime.utcnow() + INITIATING_ACTION_TTL,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # Preserve ambiguous attempts for status reconciliation: if this raises, a
    # retry must never generate a fresh reference until this one is terminal.
    payment_result = await provider.initiate_payment(
        payer_phone=farmer.phone,
        amount=loan.amount,
        currency=loan.currency,
        external_ref=ext_ref,
        reference=f"Loan repayment #{loan.id}",
        account_number=account_number,
    )

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
            detail=f"Repayment collection failed: {payment_result['message']}",
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
                reference=tx.provider_payment_ref,
                db=db,
                sent_by=None,
            )
        except Exception as exc:
            logger.warning(
                "Could not send repayment-action SMS for transaction %s: %s",
                tx.id,
                exc,
            )
        return loan

    status_result = await provider.payment_status(
        external_ref=payment_result.get("external_ref") or ext_ref,
        account_number=account_number,
    )
    return await finalize_repayment(loan=loan, tx=tx, status_result=status_result, db=db)


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
    ext_ref = locked_transaction.provider_payment_ref or repay_external_ref(loan.id)
    provider = get_payment_provider()
    account_number = cooperative_account(farmer, db)
    payment_result = await provider.initiate_payment(
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
            detail=f"Repayment verification failed: {payment_result['message']}",
        )

    if payment_result.get("verification_required"):
        transaction.customer_action = "otp"
        transaction.action_expires_at = datetime.utcnow() + CUSTOMER_ACTION_TTL
        db.commit()
        return loan

    transaction.customer_action = "approval"
    transaction.action_expires_at = datetime.utcnow() + CUSTOMER_ACTION_TTL
    db.commit()

    status_result = await provider.payment_status(
        external_ref=payment_result.get("external_ref") or ext_ref,
        account_number=account_number,
    )
    return await finalize_repayment(
        loan=loan,
        tx=transaction,
        status_result=status_result,
        db=db,
    )
