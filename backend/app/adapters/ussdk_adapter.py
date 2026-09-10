"""USSDK hook adapter — translates USSDK JSON hooks into application-service calls.

USSDK (https://www.ussdk.me) builds the USSD menu/screens visually and calls
these endpoints as "hooks" before rendering each step.  This module handles
signature verification and payload parsing; the actual business logic lives
in UssdApplicationService.
"""

import hashlib
import hmac
import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.ussd_application import UssdApplicationService

logger = logging.getLogger(__name__)

_ussd_app = UssdApplicationService()


def verify_ussdk_signature(body: bytes, signature: str | None) -> bool:
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


async def parsed_and_verified(request, x_ussdk_signature: str | None) -> dict:
    body = await request.body()
    if not verify_ussdk_signature(body, x_ussdk_signature):
        raise HTTPException(status_code=401, detail="Invalid USSDK signature")
    try:
        return await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")


async def handle_loan_balance(payload: dict, db: Session) -> dict:
    msisdn = payload.get("props", {}).get("session", {}).get("msisdn", "")
    values = payload.get("props", {}).get("values", {})
    return await _ussd_app.check_loan_balance(
        phone=msisdn,
        membership_id=values.get("membership_id"),
        db=db,
    )


async def handle_loan_request(payload: dict, db: Session) -> dict:
    session = payload.get("props", {}).get("session", {})
    values = payload.get("props", {}).get("values", {})
    try:
        amount = float(values.get("amount", ""))
    except (TypeError, ValueError):
        return {"action": "retry", "message": "Enter a valid loan amount."}

    purpose = str(values.get("purpose", "")).strip()
    return await _ussd_app.request_loan(
        phone=session.get("msisdn", ""),
        amount=amount,
        purpose=purpose,
        membership_id=values.get("membership_id"),
        db=db,
    )


async def handle_pay_dues(payload: dict, db: Session) -> dict:
    session = payload.get("props", {}).get("session", {})
    values = payload.get("props", {}).get("values", {})

    amount_raw = values.get("amount")
    otp_code = values.get("otp_code") or None
    external_ref = values.get("external_ref") or str(uuid.uuid4())

    if not amount_raw:
        return {"action": "retry", "message": "Enter a valid amount."}

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        return {"action": "retry", "message": "Enter a valid amount."}

    return await _ussd_app.pay_dues(
        phone=session.get("msisdn", ""),
        amount=amount,
        otp_code=otp_code,
        external_ref=external_ref,
        membership_id=values.get("membership_id"),
        db=db,
    )


async def handle_loan_repayment(payload: dict, db: Session) -> dict:
    session = payload.get("props", {}).get("session", {})
    values = payload.get("props", {}).get("values", {})

    transaction_id = values.get("transaction_id")
    otp_code = str(values.get("otp_code", "")).strip() or None
    loan_id = values.get("loan_id")

    return await _ussd_app.repay_loan(
        phone=session.get("msisdn", ""),
        loan_id=loan_id,
        transaction_id=transaction_id,
        otp_code=otp_code,
        membership_id=values.get("membership_id"),
        db=db,
    )


async def handle_pending_payment(payload: dict, db: Session) -> dict:
    session = payload.get("props", {}).get("session", {})
    values = payload.get("props", {}).get("values", {})

    transaction_id = values.get("transaction_id")
    otp_code = str(values.get("otp_code", "")).strip() or None

    return await _ussd_app.pending_payment(
        phone=session.get("msisdn", ""),
        transaction_id=transaction_id,
        otp_code=otp_code,
        membership_id=values.get("membership_id"),
        db=db,
    )


async def handle_wallet_balance(payload: dict, db: Session) -> dict:
    msisdn = payload.get("props", {}).get("session", {}).get("msisdn", "")
    values = payload.get("props", {}).get("values", {})
    return await _ussd_app.check_wallet_balance(
        phone=msisdn,
        membership_id=values.get("membership_id"),
        db=db,
    )


async def handle_announcements(payload: dict, db: Session) -> dict:
    msisdn = payload.get("props", {}).get("session", {}).get("msisdn", "")
    values = payload.get("props", {}).get("values", {})
    return await _ussd_app.view_announcements(
        phone=msisdn,
        membership_id=values.get("membership_id"),
        db=db,
    )
