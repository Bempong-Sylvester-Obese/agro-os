from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class WorkerCreate(BaseModel):
    name: str
    phone: str
    wage_rate: float = 0.0
    role: Literal["worker", "supervisor"] = "worker"


class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    wage_rate: Optional[float] = None
    role: Optional[Literal["worker", "supervisor"]] = None
    status: Optional[Literal["active", "inactive"]] = None


class WorkerResponse(BaseModel):
    id: int
    cooperative_id: int
    name: str
    phone: str
    wage_rate: float
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
