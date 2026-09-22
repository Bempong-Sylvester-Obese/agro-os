"""Africa's Talking USSD gateway adapter.

Pure transport translation: AT posts form fields (``sessionId``, ``phoneNumber``,
cumulative ``text`` such as ``"1*500"``) and expects a ``CON``/``END``-prefixed
plain-text reply. The menu itself lives in :class:`UssdApplicationService`, which
persists per-session state keyed by ``sessionId`` — so we only forward the most
recent ``*``-segment as this step's input.
"""

import hmac
import logging

from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.ussd_application import (
    UssdApplicationService,
    UssdRequest,
    UssdResponse,
)

logger = logging.getLogger(__name__)

GATEWAY_NAME = "africas_talking"

_ussd_app = UssdApplicationService()


def _to_at_response(resp: UssdResponse) -> Response:
    prefix = "CON" if resp.continue_session else "END"
    return Response(content=f"{prefix} {resp.text}", media_type="text/plain")


def _verify_secret(request: Request) -> None:
    settings = get_settings()
    configured_secret = settings.ussd_callback_secret
    if not configured_secret:
        if settings.app_env.lower() in ("production", "prod"):
            logger.error("USSD_CALLBACK_SECRET is required in production")
            raise HTTPException(status_code=401, detail="Invalid USSD callback secret")
        return
    supplied_secret = request.query_params.get("secret", "")
    if not hmac.compare_digest(supplied_secret, configured_secret):
        raise HTTPException(status_code=401, detail="Invalid USSD callback secret")


def to_ussd_request(*, session_id: str, phone_number: str, text: str) -> UssdRequest:
    """Translate AT's cumulative ``text`` into a single-step UssdRequest."""
    segments = [segment for segment in (text or "").split("*")] if text else []
    return UssdRequest(
        session_id=session_id,
        phone_number=phone_number,
        input_text=segments[-1].strip() if segments else "",
        is_new_session=not segments,
        metadata={"gateway": GATEWAY_NAME, "cumulative_text": text or ""},
    )


async def handle_at_callback(
    request: Request,
    session_id: str,
    phone_number: str,
    text: str,
    db: Session,
) -> Response:
    _verify_secret(request)
    req = to_ussd_request(session_id=session_id, phone_number=phone_number, text=text)
    resp = await _ussd_app.handle(req, db)
    return _to_at_response(resp)
