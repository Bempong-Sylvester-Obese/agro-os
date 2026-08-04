"""Dues collection domain service — extracted from routes/transactions.py."""
import logging
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import (
    Cooperative,
    CooperativeMembership as Farmer,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.schemas.schemas import DuesCollectResponse
from app.services.customer_action_service import CUSTOMER_ACTION_TTL, INITIATING_ACTION_TTL
from app.services.providers.factory import get_payment_provider

logger = logging.getLogger(__name__)


def _cooperative_account(farmer: Farmer, db: Session) -> str | None:
    cooperative = db.query(Cooperative).filter(Cooperative.id == farmer.cooperative_id).first()
    return cooperative.moolre_account_number if cooperative else None


def _dues_collect_response(tx: Transaction, result: dict) -> DuesCollectResponse:
    verification_required = result.get("verification_required", False)
    outcome = result.get("outcome")
    if outcome is None:
        if verification_required:
            outcome = "verification_required"
        elif result.get("success"):
            outcome = "push_sent"
        else:
            outcome = "failed"

    if tx.status == TransactionStatus.completed:
        status = "completed"
    elif tx.status == TransactionStatus.failed:
        status = "failed"
    elif outcome == "verification_required":
        status = "verification_required"
    elif (
        outcome in ("initiating", "processing_otp", "push_sent")
        or result.get("success")
        or verification_required
    ):
        status = "pending"
    else:
        status = "failed"

    return DuesCollectResponse(
        transaction_id=tx.id,
        moolre_reference=tx.moolre_reference,
        status=status,
        message=result.get("message")
        or ("Payment request sent" if result.get("success") else "Moolre request failed"),
        verification_required=verification_required,
        outcome=outcome,
        moolre_code=result.get("moolre_code"),
        customer_action=tx.customer_action,
        action_expires_at=tx.action_expires_at,
    )


async def run_dues_collect(
    *,
    farmer: Farmer,
    amount: float,
    channel: str,
    description: str | None,
    external_ref: str,
    otp_code: str | None,
    db: Session,
    initiation_channel: str = "ussd",
) -> DuesCollectResponse:
    tx = (
        db.query(Transaction)
        .filter(
            Transaction.moolre_reference == external_ref,
            Transaction.farmer_id == farmer.id,
        )
        .first()
    )
    if not tx:
        tx = Transaction(
            farmer_id=farmer.id,
            transaction_type=TransactionType.dues,
            amount=amount,
            currency="GHS",
            status=TransactionStatus.pending,
            moolre_reference=external_ref,
            payer_phone=farmer.phone,
            channel=channel,
            description=description,
            initiation_channel=initiation_channel,
            customer_action="initiating",
            action_expires_at=datetime.utcnow() + INITIATING_ACTION_TTL,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
    else:
        if tx.transaction_type != TransactionType.dues:
            raise HTTPException(status_code=409, detail="Payment reference type mismatch")
        if tx.status != TransactionStatus.pending:
            raise HTTPException(status_code=409, detail="Payment is no longer pending")
        if abs(float(tx.amount) - float(amount)) >= 0.01:
            raise HTTPException(status_code=409, detail="Payment amount mismatch")

    provider = get_payment_provider()
    coop_account = _cooperative_account(farmer, db)
    try:
        result = await provider.initiate_payment(
            payer_phone=farmer.phone,
            amount=amount,
            currency="GHS",
            channel=channel,
            external_ref=external_ref,
            otpcode=otp_code,
            reference=description or "Cooperative dues",
            account_number=coop_account,
        )
    except Exception:
        raise

    db.expire_all()
    tx = (
        db.query(Transaction)
        .filter(
            Transaction.moolre_reference == external_ref,
            Transaction.farmer_id == farmer.id,
        )
        .with_for_update()
        .one()
    )
    if tx.status in (TransactionStatus.completed, TransactionStatus.failed):
        return _dues_collect_response(
            tx,
            {
                "outcome": tx.status.value,
                "message": f"Payment already {tx.status.value}.",
            },
        )

    if result.get("moolre_reference") and result["moolre_reference"] != external_ref:
        ref_val = str(result["moolre_reference"]).lower()
        if ref_val not in ("all", "phoneno", "externalref", "senderid"):
            tx.moolre_reference = result["moolre_reference"]

    verification_required = result.get("verification_required", False) or result.get("outcome") == "verification_required"
    if verification_required:
        tx.customer_action = "otp"
        tx.action_expires_at = datetime.utcnow() + CUSTOMER_ACTION_TTL
    elif result.get("success") or result.get("outcome") == "push_sent":
        tx.customer_action = "approval"
        tx.action_expires_at = datetime.utcnow() + CUSTOMER_ACTION_TTL
    else:
        tx.status = TransactionStatus.failed
        tx.customer_action = "none"
        tx.action_expires_at = None
    db.commit()

    result = {**result, "verification_required": verification_required}

    return _dues_collect_response(tx, result)
