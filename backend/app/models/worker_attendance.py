import enum
from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.db import Base


class Shift(str, enum.Enum):
    morning = "morning"
    afternoon = "afternoon"
    full_day = "full_day"


class WorkerAttendance(Base):
    __tablename__ = "worker_attendance"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cooperative_id", "worker_id"],
            ["workers.cooperative_id", "workers.id"],
            name="fk_worker_attendance_cooperative_worker",
        ),
        ForeignKeyConstraint(
            ["cooperative_id", "work_task_id"],
            ["work_tasks.cooperative_id", "work_tasks.id"],
            name="fk_worker_attendance_cooperative_task",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, nullable=False, index=True)
    work_task_id = Column(Integer, nullable=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    hours_worked = Column(Float, nullable=True)
    shift = Column(Enum(Shift), nullable=False)
    logged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    worker = relationship("Worker", overlaps="cooperative")
    work_task = relationship("WorkTask", overlaps="cooperative,worker")
    cooperative = relationship("Cooperative", overlaps="work_task,worker")
    logger = relationship("User")
