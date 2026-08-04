from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class FarmProductionCreate(BaseModel):
    crop_type: str
    season: str
    location: Optional[str] = None
    planted_date: date
    expected_harvest_date: Optional[date] = None
    actual_harvest_date: Optional[date] = None
    expected_quantity_kg: float
    actual_quantity_kg: Optional[float] = None
    quality_grade: Optional[str] = None
    notes: Optional[str] = None


class FarmProductionUpdate(BaseModel):
    crop_type: Optional[str] = None
    season: Optional[str] = None
    location: Optional[str] = None
    planted_date: Optional[date] = None
    expected_harvest_date: Optional[date] = None
    actual_harvest_date: Optional[date] = None
    expected_quantity_kg: Optional[float] = None
    actual_quantity_kg: Optional[float] = None
    quality_grade: Optional[str] = None
    notes: Optional[str] = None


class FarmProductionResponse(BaseModel):
    id: int
    cooperative_id: int
    crop_type: str
    season: str
    location: Optional[str] = None
    planted_date: date
    expected_harvest_date: Optional[date] = None
    actual_harvest_date: Optional[date] = None
    expected_quantity_kg: float
    actual_quantity_kg: Optional[float] = None
    quality_grade: Optional[str] = None
    notes: Optional[str] = None
    logged_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
