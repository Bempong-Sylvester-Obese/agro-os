"""
USSDK Hook Adapter Routes

USSDK (https://www.ussdk.me) builds the USSD menu/screens visually and calls
these endpoints as "hooks" before rendering each step.  This module handles
authentication and delegates to app.adapters.ussdk_adapter which translates
the hook payload into calls against the shared UssdApplicationService.
"""

import logging

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.adapters.ussdk_adapter import (
    parsed_and_verified,
    handle_loan_balance,
    handle_loan_request,
    handle_pay_dues,
    handle_loan_repayment,
    handle_pending_payment,
    handle_wallet_balance,
    handle_announcements,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ussdk", tags=["ussdk"])


@router.post("/loan-balance")
async def loan_balance(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    payload = await parsed_and_verified(request, x_ussdk_signature)
    return await handle_loan_balance(payload, db)


@router.post("/loan-request")
async def loan_request(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    payload = await parsed_and_verified(request, x_ussdk_signature)
    session = payload.get("props", {}).get("session", {})
    values = payload.get("props", {}).get("values", {})
    try:
        amount = float(values.get("amount", ""))
    except (TypeError, ValueError):
        return {"action": "retry", "message": "Enter a valid loan amount."}
    purpose = str(values.get("purpose", "")).strip()
    return await handle_loan_request(payload, db)


@router.post("/pay-dues")
async def pay_dues(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    payload = await parsed_and_verified(request, x_ussdk_signature)
    values = payload.get("props", {}).get("values", {})
    if not values.get("amount"):
        return {"action": "retry", "message": "Enter a valid amount."}
    return await handle_pay_dues(payload, db)


@router.post("/loan-repayment")
async def loan_repayment(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    payload = await parsed_and_verified(request, x_ussdk_signature)
    return await handle_loan_repayment(payload, db)


@router.post("/pending-payment")
async def pending_payment(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    payload = await parsed_and_verified(request, x_ussdk_signature)
    return await handle_pending_payment(payload, db)


@router.post("/wallet-balance")
async def wallet_balance(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    payload = await parsed_and_verified(request, x_ussdk_signature)
    return await handle_wallet_balance(payload, db)


@router.post("/announcements")
async def announcements(
    request: Request,
    db: Session = Depends(get_db),
    x_ussdk_signature: str | None = Header(default=None),
):
    payload = await parsed_and_verified(request, x_ussdk_signature)
    return await handle_announcements(payload, db)

