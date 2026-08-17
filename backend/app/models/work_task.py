import enum
from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.db import Base


class TaskType(str, enum.Enum):
    planting = "planting"
    weeding = "weeding"
    harvesting = "harvesting"
    irrigation = "irrigation"
    fertilizing = "fertilizing"
    general = "general"


class TaskStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class WorkTask(Base):
    __tablename__ = "work_tasks"
    __table_args__ = (
        UniqueConstraint(
            "cooperative_id",
            "id",
            name="uq_work_tasks_cooperative_id_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(Enum(TaskType), nullable=False)
    location = Column(String, nullable=True)
    scheduled_date = Column(Date, nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.open)
    created_at = Column(DateTime, default=datetime.utcnow)

    cooperative = relationship("Cooperative")
    assigner = relationship("User")
    assignments = relationship("WorkerAssignment", back_populates="task")


class WorkerAssignment(Base):
    __tablename__ = "worker_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cooperative_id", "work_task_id"],
            ["work_tasks.cooperative_id", "work_tasks.id"],
            name="fk_worker_assignments_cooperative_task",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["cooperative_id", "worker_id"],
            ["workers.cooperative_id", "workers.id"],
            name="fk_worker_assignments_cooperative_worker",
            ondelete="CASCADE",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, nullable=False, index=True)
    work_task_id = Column(Integer, nullable=False, index=True)
    worker_id = Column(Integer, nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("WorkTask", back_populates="assignments")
    worker = relationship("Worker", overlaps="assignments,task")
