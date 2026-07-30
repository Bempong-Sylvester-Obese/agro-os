from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class AttendanceCreate(BaseModel):
    worker_id: int
    work_task_id: Optional[int] = None
    date: date
    hours_worked: Optional[float] = None
    shift: Literal["morning", "afternoon", "full_day"]
    notes: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: int
    worker_id: int
    work_task_id: Optional[int] = None
    cooperative_id: int
    date: date
    hours_worked: Optional[float] = None
    shift: str
    logged_by: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceSummary(BaseModel):
    worker_id: int
    worker_name: str
    total_hours: float
    total_shifts: int
    period_start: date
    period_end: date
