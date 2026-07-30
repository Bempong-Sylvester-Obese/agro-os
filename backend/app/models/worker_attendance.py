import enum
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


class Shift(str, enum.Enum):
    morning = "morning"
    afternoon = "afternoon"
    full_day = "full_day"


class WorkerAttendance(Base):
    __tablename__ = "worker_attendance"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    work_task_id = Column(Integer, ForeignKey("work_tasks.id"), nullable=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    hours_worked = Column(Float, nullable=True)
    shift = Column(Enum(Shift), nullable=False)
    logged_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    worker = relationship("Worker")
    work_task = relationship("WorkTask")
    cooperative = relationship("Cooperative")
    logger = relationship("User")
