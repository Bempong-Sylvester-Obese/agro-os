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

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.models.models import Cooperative, Loan, LoanStatus
from app.routes.transactions import _run_dues_collect
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

