from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: Literal["planting", "weeding", "harvesting", "irrigation", "fertilizing", "general"]
    location: Optional[str] = None
    scheduled_date: date
    worker_ids: list[int] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[Literal["planting", "weeding", "harvesting", "irrigation", "fertilizing", "general"]] = None
    location: Optional[str] = None
    scheduled_date: Optional[date] = None
    status: Optional[Literal["open", "in_progress", "completed", "cancelled"]] = None


class WorkerAssignmentResponse(BaseModel):
    id: int
    work_task_id: int
    worker_id: int
    assigned_at: datetime

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: int
    cooperative_id: int
    title: str
    description: Optional[str] = None
    task_type: str
    location: Optional[str] = None
    scheduled_date: date
    assigned_by: int
    status: str
    created_at: datetime
    assignments: list[WorkerAssignmentResponse] = []

    class Config:
        from_attributes = True


class TaskAssignmentCreate(BaseModel):
    worker_ids: list[int]
