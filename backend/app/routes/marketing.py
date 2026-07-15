"""Public conversion endpoints backed by durable records."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import DemoBooking
from app.schemas.marketing import DemoBookingCreate, DemoBookingResponse

router = APIRouter(prefix="/marketing", tags=["marketing"])


@router.post("/demo-bookings", response_model=DemoBookingResponse, status_code=201)
def create_demo_booking(
    body: DemoBookingCreate,
    db: Session = Depends(get_db),
):
    """Persist a consultation request and return its server-generated reference."""
    booking = DemoBooking(
        reference=f"AGO-DEMO-{uuid.uuid4().hex[:12].upper()}",
        **body.model_dump(),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
