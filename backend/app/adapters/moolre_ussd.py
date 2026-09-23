"""Moolre USSD gateway adapter — translates Moolre JSON to UssdRequest/UssdResponse."""

import json
import logging

from fastapi import Request
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session

from app.services.ussd_application import (
    UssdApplicationService,
    UssdRequest,
    UssdResponse,
)

logger = logging.getLogger(__name__)

_ussd_app = UssdApplicationService()


def _to_moolre_response(req: UssdRequest, resp: UssdResponse) -> dict:
    return {
        "sessionId": req.session_id,
        "message": resp.text,
        "reply": resp.continue_session,
    }


async def handle_moolre_ussd(request: Request, db: Session) -> JSONResponse:
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    req = UssdRequest(
        session_id=payload.get("sessionId", ""),
        phone_number=payload.get("msisdn", ""),
        input_text=str(payload.get("message", "")).strip(),
        is_new_session=bool(payload.get("new")),
        metadata={"gateway": "moolre"},
    )
    resp = await _ussd_app.handle(req, db)
    return JSONResponse(_to_moolre_response(req, resp))
