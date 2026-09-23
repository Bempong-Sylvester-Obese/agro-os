from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel

PayType = Literal["daily", "shift", "monthly"]


class WorkerCreate(BaseModel):
    name: str
    phone: str
    wage_rate: float = 0.0
    role: Literal["worker", "supervisor"] = "worker"
    hire_date: date | None = None
    pay_type: PayType = "daily"
    user_id: int | None = None


class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    wage_rate: Optional[float] = None
    role: Optional[Literal["worker", "supervisor"]] = None
    status: Optional[Literal["active", "inactive"]] = None
    hire_date: date | None = None
    pay_type: Optional[PayType] = None
    user_id: int | None = None


class WorkerResponse(BaseModel):
    id: int
    cooperative_id: int
    name: str
    phone: str
    wage_rate: float
    role: str
    status: str
    hire_date: date | None = None
    pay_type: str = "daily"
    user_id: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
