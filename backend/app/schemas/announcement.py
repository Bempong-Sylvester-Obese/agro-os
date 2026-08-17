from datetime import datetime
from pydantic import BaseModel

class AnnouncementCreate(BaseModel):
    title: str
    body: str
    send_sms: bool = False

class AnnouncementResponse(BaseModel):
    id: int
    cooperative_id: int
    title: str
    body: str
    send_sms: bool
    created_by: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True
