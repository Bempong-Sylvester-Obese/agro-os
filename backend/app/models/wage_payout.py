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
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.db import Base


class PayoutStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    paid = "paid"
    failed = "failed"


class WagePayout(Base):
    __tablename__ = "wage_payouts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cooperative_id", "worker_id"],
            ["workers.cooperative_id", "workers.id"],
            name="fk_wage_payouts_cooperative_worker",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    worker_id = Column(Integer, nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_hours = Column(Float, default=0.0)
    total_shifts = Column(Integer, default=0)
    wage_rate = Column(Float, nullable=False)
    gross_amount = Column(Float, nullable=False)
    status = Column(Enum(PayoutStatus), default=PayoutStatus.pending)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    provider_payment_ref = Column(String, nullable=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cooperative = relationship("Cooperative", overlaps="worker")
    worker = relationship("Worker", overlaps="cooperative")
    approver = relationship("User")
