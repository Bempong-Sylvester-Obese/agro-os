"""Communications Routes — SMS broadcast and reminder endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import CommunicationLog, Cooperative, User
from app.services.auth_service import get_current_user
from app.schemas.schemas import (
    CommunicationLogResponse,
    DuesReminderRequest,
    SMSBroadcastRequest,
    SMSResponse,
)
from app.services.communications_service import CommunicationsService

router = APIRouter(prefix="/communications", tags=["communications"])


@router.post("/sms/broadcast", response_model=SMSResponse)
async def broadcast_sms(request: SMSBroadcastRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Send a free-form SMS broadcast to all active members of a cooperative.
    Message must be ≤ 160 characters (enforced by schema).
    """
    coop = db.query(Cooperative).filter(Cooperative.id == request.cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    service = CommunicationsService()
    result = await service.broadcast_to_cooperative(
        cooperative_id=request.cooperative_id,
        message=request.message,
        db=db,
        sent_by=request.sent_by,
    )
    return SMSResponse(
        status="success" if result["success"] else "failed",
        recipients_count=result["recipients_count"],
        message=result["message"],
        log_id=result.get("log_id"),
    )


@router.post("/sms/dues-reminder", response_model=SMSResponse)
async def send_dues_reminder(request: DuesReminderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Send a dues-payment reminder SMS to all active members of a cooperative.
    Uses the Moolre merchant USSD code from config for the payment instruction.
    """
    coop = db.query(Cooperative).filter(Cooperative.id == request.cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    service = CommunicationsService()
    result = await service.send_dues_reminder_to_cooperative(
        cooperative_id=request.cooperative_id,
        amount=request.amount,
        due_date=request.due_date,
        db=db,
        sent_by=request.sent_by,
    )
    return SMSResponse(
        status="success" if result["success"] else "failed",
        recipients_count=result["recipients_count"],
        message=result["message"],
        log_id=result.get("log_id"),
    )


@router.get("/logs", response_model=list[CommunicationLogResponse])
def list_communication_logs(
    cooperative_id: int | None = None,
    skip: int = 0,
    limit: int = Query(default=50, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """List sent communication logs, optionally filtered by cooperative."""
    query = db.query(CommunicationLog)
    if current_user and current_user.cooperative_id:
        query = query.filter(CommunicationLog.cooperative_id == current_user.cooperative_id)
    elif cooperative_id is not None:
        query = query.filter(CommunicationLog.cooperative_id == cooperative_id)
    else:
        settings = get_settings()
        if settings.auth_enabled:
            raise HTTPException(status_code=401, detail="Authentication required")
        raise HTTPException(status_code=400, detail="cooperative_id is required")
    return query.order_by(CommunicationLog.sent_at.desc()).offset(skip).limit(limit).all()
