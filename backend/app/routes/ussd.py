# USSD Gateway (Africa's Talking format) — delegates to app.adapters.at_adapter

import logging

from fastapi import APIRouter, Depends, Form, Request, Response
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.adapters.at_adapter import handle_at_callback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ussd", tags=["ussd"])

@router.post("/callback")
async def ussd_callback(
    request: Request,
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
    db: Session = Depends(get_db)
):
    """
    Native USSD Gateway Router using Africa's Talking format.
    State is managed by the `text` string which contains inputs separated by '*'.
    """
    return await handle_at_callback(request, phoneNumber, text, db)
