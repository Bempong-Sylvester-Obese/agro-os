import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.db import Base


class WorkerRole(str, enum.Enum):
    worker = "worker"
    supervisor = "supervisor"


class WorkerStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, index=True)
    wage_rate = Column(Float, default=0.0)
    role = Column(Enum(WorkerRole), default=WorkerRole.worker)
    status = Column(Enum(WorkerStatus), default=WorkerStatus.active)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cooperative = relationship("Cooperative")

    __table_args__ = (
        UniqueConstraint("cooperative_id", "phone", name="uq_worker_phone_per_coop"),
        UniqueConstraint(
            "cooperative_id",
            "id",
            name="uq_workers_cooperative_id_id",
        ),
    )
