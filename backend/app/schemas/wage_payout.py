from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class PayrollPeriod(BaseModel):
    period_start: date
    period_end: date


class PayrollSummaryItem(BaseModel):
    worker_id: int
    worker_name: str
    phone: str
    wage_rate: float
    total_hours: float
    total_shifts: int
    gross_amount: float


class PayrollSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    total_workers: int
    total_gross: float
    items: list[PayrollSummaryItem]


class WagePayoutResponse(BaseModel):
    id: int
    cooperative_id: int
    worker_id: int
    period_start: date
    period_end: date
    total_hours: float
    total_shifts: int
    wage_rate: float
    gross_amount: float
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    moolre_reference: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PayrollHistoryResponse(BaseModel):
    period_start: date
    period_end: date
    status: str
    total_workers: int
    total_gross: float
    paid_at: Optional[datetime] = None
    payouts: list[WagePayoutResponse]
