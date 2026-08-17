from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import Announcement, CooperativeMembership, User
from app.schemas.announcement import AnnouncementCreate, AnnouncementResponse
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/announcements", tags=["announcements"])

@router.get("/", response_model=list[AnnouncementResponse])
def list_announcements(
    cooperative_id: int = Query(...),
    skip: int = 0,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    return (
        db.query(Announcement)
        .filter(
            Announcement.cooperative_id == cooperative_id,
            Announcement.deleted_at.is_(None),
        )
        .order_by(Announcement.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

@router.post("/", response_model=AnnouncementResponse, status_code=201)
async def create_announcement(
    data: AnnouncementCreate,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    announcement = Announcement(
        cooperative_id=cooperative_id,
        title=data.title,
        body=data.body,
        send_sms=data.send_sms,
        created_by=current_user.id if current_user else None,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    if data.send_sms:
        from app.services.communications_service import CommunicationsService
        comm = CommunicationsService()
        memberships = (
            db.query(CooperativeMembership)
            .filter(
                CooperativeMembership.cooperative_id == cooperative_id,
                CooperativeMembership.membership_status == "active",
                CooperativeMembership.sms_consent.is_(True),
            )
            .all()
        )
        for m in memberships:
            if m.phone:
                await comm.send_single_sms(
                    recipient=m.phone,
                    message=f"[{announcement.title}] {announcement.body}",
                    db=db,
                    cooperative_id=cooperative_id,
                )

    return announcement

@router.delete("/{announcement_id}", status_code=204)
def delete_announcement(
    announcement_id: int,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    announcement = (
        db.query(Announcement)
        .filter(
            Announcement.id == announcement_id,
            Announcement.cooperative_id == cooperative_id,
            Announcement.deleted_at.is_(None),
        )
        .first()
    )
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    announcement.deleted_at = datetime.now(timezone.utc)
    db.commit()
