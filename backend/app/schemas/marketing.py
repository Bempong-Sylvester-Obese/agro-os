"""Validated public marketing request schemas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

DemoTopic = Literal[
    "Full platform evaluation",
    "Payments and MoMo operations",
    "AgroCredit Trust Scores",
    "USSD and field access",
    "Member and production management",
    "Enterprise implementation",
]
DemoTime = Literal["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00"]


class DemoBookingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    cooperative: str = Field(min_length=2, max_length=160)
    size: str = Field(min_length=1, max_length=60)
    topic: DemoTopic
    notes: str | None = Field(default=None, max_length=2000)
    selected_date: date
    selected_time: DemoTime
    is_enterprise: bool = False

    @field_validator("selected_date")
    @classmethod
    def date_must_be_future(cls, value: date) -> date:
        if value <= date.today():
            raise ValueError("selected_date must be in the future")
        return value


class DemoBookingResponse(DemoBookingCreate):
    reference: str
    created_at: datetime
