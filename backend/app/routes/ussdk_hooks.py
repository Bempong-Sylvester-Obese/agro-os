"""
USSDK Hook Adapter Routes

USSDK (https://www.ussdk.me) builds the USSD menu/screens visually and calls
these endpoints as "hooks" before rendering each step. This module translates
USSDK's hook payload shape into calls against the existing dues-collection
logic in app/routes/transactions.py, so Moolre auth, OTP handling, transaction
records, and Trust Score recalculation all stay in one place.

USSDK hook request shape:
{
  "input": {"key": "2"},
  "props": {
    "session": {"msisdn": "0240000001", "network": "mtn", "serviceCode": "*123*45#"},
    "values": {"amount": "5", "otp_code": "123456"}
  }
}
"""

import hashlib
import hmac
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.models.models import (
    Cooperative,
    Loan,
    LoanStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.routes.loans import resume_loan_repayment_customer_action
from app.routes.transactions import (
    _run_dues_collect,
    expire_customer_actions,
    pending_customer_actions,
    resume_dues_customer_action,
)
from app.services.loan_request_service import (
    PendingLoanRequestError,
    create_farmer_loan_request,
)
from app.services.membership_service import (
    cooperative_selection_payload,
    resolve_phone_membership,
)
from app.services.moolre_service import MoolreService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ussdk", tags=["ussdk"])


def _verify_ussdk_signature(body: bytes, signature: str | None) -> bool:
    """Verify USSDK's X-USSDK-Signature header (HMAC-SHA256 of the raw body).

    Mirrors the pattern already used for Moolre's webhook signature in
    app/routes/webhooks.py. If no secret is configured, verification is
    skipped for local development — never leave it unset in production.
    """
    settings = get_settings()
    if not settings.ussdk_hook_secret:
        if settings.app_env.lower() in ("production", "prod"):
            logger.error("USSDK_HOOK_SECRET is required in production")
            return False
        logger.warning("USSDK_HOOK_SECRET not set — skipping signature verification")
        return True
    if not signature:
        return False
    expected = hmac.new(
        settings.ussdk_hook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


async def _parsed_and_verified(
    request: Request, x_ussdk_signature: str | None
) -> dict:
    body = await request.body()
    if not _verify_ussdk_signature(body, x_ussdk_signature):
        raise HTTPException(status_code=401, detail="Invalid USSDK signature")
    try:
        return await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")


@router.post("/loan-balance")
async def loan_balance(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    """Hook for the 'Check Loan Balance' USSD step."""
    payload = await _parsed_and_verified(request, x_ussdk_signature)
    msisdn = payload.get("props", {}).get("session", {}).get("msisdn", "")
    values = payload.get("props", {}).get("values", {})

    farmer, memberships = resolve_phone_membership(
        msisdn, db, membership_id=values.get("membership_id")
    )
    if not farmer:
        if len(memberships) > 1:
            return cooperative_selection_payload(memberships)
        return {"registered": False, "balance": None, "name": None}

    active_loans = (
        db.query(Loan)
        .filter(Loan.farmer_id == farmer.id, Loan.status == LoanStatus.disbursed)
        .all()
    )
    total = sum(ln.amount for ln in active_loans)
    return {"registered": True, "name": farmer.name, "balance": total}


@router.post("/loan-request")
async def loan_request(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    """Create a farmer-originated loan request from a signed USSDK screen."""
    payload = await _parsed_and_verified(request, x_ussdk_signature)
    session = payload.get("props", {}).get("session", {})
    values = payload.get("props", {}).get("values", {})
    farmer, memberships = resolve_phone_membership(
        session.get("msisdn", ""),
        db,
        membership_id=values.get("membership_id"),
    )
    if not farmer:
        if len(memberships) > 1:
            return cooperative_selection_payload(memberships)
        return {
            "action": "end",
            "message": "Phone not registered with AgroOS. Contact your cooperative.",
        }

    try:
        amount = float(values.get("amount", ""))
    except (TypeError, ValueError):
        return {"action": "retry", "message": "Enter a valid loan amount."}

    purpose = str(values.get("purpose", "")).strip()
    try:
        loan = create_farmer_loan_request(
            membership=farmer,
            amount=amount,
            purpose=purpose,
            db=db,
            request_channel="ussdk",
        )
    except PendingLoanRequestError as exc:
        return {"action": "end", "message": str(exc)}
    except ValueError as exc:
        return {"action": "retry", "message": str(exc)}

    return {
        "action": "end",
        "loan_id": loan.id,
        "status": loan.status.value,
        "message": f"Loan request #{loan.id} submitted for cooperative review.",
    }


@router.post("/pay-dues")
async def pay_dues(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    """Hook for the 'Pay Cooperative Dues' USSD step.

    Called twice in the OTP-required case: once to start the push, and once
    more with otp_code + external_ref set (from the previous response) to
    resume the same transaction rather than starting a new one.
    """
    payload = await _parsed_and_verified(request, x_ussdk_signature)
    session = payload.get("props", {}).get("session", {})
    values = payload.get("props", {}).get("values", {})

    msisdn = session.get("msisdn", "")
    amount_raw = values.get("amount")
    otp_code = values.get("otp_code") or None
    external_ref = values.get("external_ref") or str(uuid.uuid4())

    if not amount_raw:
        return {
            "action": "retry",
            "message": "Enter a valid amount.",
        }

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        return {"action": "retry", "message": "Enter a valid amount."}

    farmer, memberships = resolve_phone_membership(
        msisdn, db, membership_id=values.get("membership_id")
    )
    if not farmer:
        if len(memberships) > 1:
            return cooperative_selection_payload(memberships)
        return {
            "action": "end",
            "message": "Phone not registered with AgroOS. Contact your cooperative.",
        }

    result = await _run_dues_collect(
        farmer=farmer,
        amount=amount,
        channel="13",
        description="Cooperative dues (USSD)",
        external_ref=external_ref,
        otp_code=otp_code,
        db=db,
        initiation_channel="ussdk",
    )

    if result.outcome == "verification_required":
        return {
            "verification_required": True,
            "external_ref": external_ref,
            "message": result.message,
        }

    if result.status == "pending":
        return {
            "verification_required": False,
            "message": "Approve the payment prompt on your phone to complete.",
        }

    return {
        "action": "end",
        "message": result.message or "Payment could not be started. Try again later.",
    }


@router.post("/pending-payment")
async def pending_payment(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    """List or resume payment actions owned by the calling farmer phone."""
    payload = await _parsed_and_verified(request, x_ussdk_signature)
    session = payload.get("props", {}).get("session", {})
    values = payload.get("props", {}).get("values", {})
    farmer, memberships = resolve_phone_membership(
        session.get("msisdn", ""),
        db,
        membership_id=values.get("membership_id"),
    )
    if not farmer:
        if len(memberships) > 1:
            return cooperative_selection_payload(memberships)
        return {"action": "end", "message": "Phone not registered with AgroOS."}

    transaction_id = values.get("transaction_id")
    if not transaction_id:
        actions = pending_customer_actions(farmer=farmer, db=db)
        return {
            "action": "select_payment" if actions else "end",
            "message": (
                "Choose a pending payment."
                if actions
                else "You have no pending payments."
            ),
            "payments": [
                {
                    "transaction_id": tx.id,
                    "type": tx.transaction_type.value,
                    "amount": tx.amount,
                    "customer_action": tx.customer_action,
                }
                for tx in actions
            ],
        }

    try:
        selected_id = int(transaction_id)
    except (TypeError, ValueError):
        return {"action": "retry", "message": "Choose a valid pending payment."}
    expire_customer_actions(db, farmer_id=farmer.id)
    tx = (
        db.query(Transaction)
        .filter(
            Transaction.id == selected_id,
            Transaction.farmer_id == farmer.id,
            Transaction.status == TransactionStatus.pending,
            Transaction.customer_action.in_(("otp", "processing_otp", "approval")),
            Transaction.action_expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not tx:
        return {"action": "end", "message": "Pending payment not found."}
    if tx.customer_action == "approval":
        return {
            "action": "end",
            "message": "Approve the payment prompt on your phone to complete.",
        }
    if tx.customer_action == "processing_otp":
        return {
            "action": "end",
            "message": "Your OTP is already being processed. Check again shortly.",
        }

    otp_code = str(values.get("otp_code", "")).strip()
    if not otp_code:
        return {
            "action": "request_otp",
            "transaction_id": tx.id,
            "message": "Enter the OTP sent to your phone.",
        }
    try:
        if tx.transaction_type == TransactionType.dues:
            result = await resume_dues_customer_action(
                transaction=tx,
                farmer=farmer,
                otp_code=otp_code,
                db=db,
            )
            message = result.message
            retry_otp = result.customer_action == "otp"
        elif tx.transaction_type == TransactionType.repayment:
            loan = await resume_loan_repayment_customer_action(
                transaction=tx,
                farmer=farmer,
                otp_code=otp_code,
                db=db,
            )
            message = (
                "Loan repayment completed."
                if loan.status == LoanStatus.repaid
                else "OTP accepted. Approve the repayment prompt on your phone."
            )
            retry_otp = tx.customer_action == "otp"
        else:
            return {"action": "end", "message": "Unsupported pending payment."}
    except HTTPException as exc:
        return {
            "action": "end" if exc.status_code in (404, 410) else "retry",
            "message": str(exc.detail),
        }
    except Exception:
        logger.exception("Pending payment completion failed for transaction %s", tx.id)
        return {
            "action": "end",
            "message": "Payment could not be completed. Check again shortly.",
        }
    if retry_otp:
        return {
            "action": "request_otp",
            "transaction_id": tx.id,
            "message": message or "OTP verification is still required. Try again.",
        }
    return {"action": "end", "message": message}


@router.post("/wallet-balance")
async def wallet_balance(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    """Hook for a 'Check Cooperative Wallet Balance' USSD step.

    Calls Moolre's real account/status endpoint via MoolreService.account_status,
    using the farmer's cooperative wallet if set, falling back to the server-wide
    MOOLRE_ACCOUNT_NUMBER otherwise.
    """
    payload = await _parsed_and_verified(request, x_ussdk_signature)
    msisdn = payload.get("props", {}).get("session", {}).get("msisdn", "")
    values = payload.get("props", {}).get("values", {})

    farmer, memberships = resolve_phone_membership(
        msisdn, db, membership_id=values.get("membership_id")
    )
    if not farmer:
        if len(memberships) > 1:
            return cooperative_selection_payload(memberships)
        return {
            "action": "end",
            "message": "Phone not registered with AgroOS. Contact your cooperative.",
        }

    cooperative = (
        db.query(Cooperative).filter(Cooperative.id == farmer.cooperative_id).first()
    )
    coop_account = cooperative.moolre_account_number if cooperative else None

    moolre = MoolreService()
    result = await moolre.account_status(account_number=coop_account)

    if not result.get("success"):
        return {
            "action": "end",
            "message": "Could not reach Moolre right now. Try again later.",
        }

    balance = result.get("balance")
    account_name = result.get("account_name") or "your cooperative"
    return {
        "message": f"{account_name} wallet balance: GHS {balance}",
    }


@router.post("/announcements")
async def announcements(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    """Hook for a 'View Announcements' USSD step.

    Shows the announcement on the USSD screen and also sends it via SMS
    through Moolre's real SMS endpoint (MoolreService.send_single_sms),
    so the announcement isn't lost when the USSD session times out.
    """
    payload = await _parsed_and_verified(request, x_ussdk_signature)
    msisdn = payload.get("props", {}).get("session", {}).get("msisdn", "")
    values = payload.get("props", {}).get("values", {})

    farmer, memberships = resolve_phone_membership(
        msisdn, db, membership_id=values.get("membership_id")
    )
    announcement_text = "No new announcements. Check with your cooperative leader."

    if not farmer and len(memberships) > 1:
        return cooperative_selection_payload(memberships)
    if farmer:
        moolre = MoolreService()
        sms_result = await moolre.send_single_sms(
            phone=farmer.phone,
            message=announcement_text,
            ref=f"announce-{farmer.id}",
        )
        if sms_result.get("success"):
            return {"message": f"{announcement_text}\n(Also sent via SMS.)"}

    return {"message": announcement_text}

