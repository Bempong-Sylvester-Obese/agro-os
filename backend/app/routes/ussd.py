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
    AT sends cumulative input in `text` ('1*500'); the adapter forwards the latest
    segment to the shared UssdApplicationService keyed by `sessionId`.
    """
    return await handle_at_callback(request, sessionId, phoneNumber, text, db)
