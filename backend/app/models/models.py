"""Database Models for AgroOS"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.db import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MembershipStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class TransactionType(str, enum.Enum):
    dues = "dues"
    loan = "loan"
    payout = "payout"
    repayment = "repayment"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class LoanStatus(str, enum.Enum):
    requested = "requested"
    approved = "approved"
    disbursed = "disbursed"
    repaid = "repaid"
    rejected = "rejected"


class MessageType(str, enum.Enum):
    sms = "sms"
    whatsapp = "whatsapp"


# ---------------------------------------------------------------------------
# Cooperative
# ---------------------------------------------------------------------------


class Cooperative(Base):
    """Cooperative / Farmer Union Model"""

    __tablename__ = "cooperatives"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    currency = Column(String, default="GHS")
    # Moolre wallet that holds cooperative funds
    moolre_account_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmers = relationship("Farmer", back_populates="cooperative")


# ---------------------------------------------------------------------------
# Farmer
# ---------------------------------------------------------------------------


class Farmer(Base):
    """Farmer / Member Model"""

    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    location = Column(String, nullable=True)
    crop_type = Column(String, nullable=True)
    acreage = Column(Float, nullable=True)
    membership_status = Column(
        Enum(MembershipStatus), default=MembershipStatus.active
    )
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False)
    trust_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cooperative = relationship("Cooperative", back_populates="farmers")
    transactions = relationship("Transaction", back_populates="farmer")
    productions = relationship("Production", back_populates="farmer")
    loans = relationship("Loan", back_populates="farmer")
    trust_scores = relationship("TrustScore", back_populates="farmer")
    attendances = relationship("CooperativeAttendance", back_populates="farmer")


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


class Transaction(Base):
    """Finance Transaction Model (dues, payouts, repayments)"""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="GHS")
    status = Column(Enum(TransactionStatus), default=TransactionStatus.pending)
    # Moolre refs
    moolre_reference = Column(String, unique=True, nullable=True)  # payment ref
    moolre_transfer_ref = Column(String, unique=True, nullable=True)  # transfer ref
    # Participant phones (for USSD / mobile money)
    payer_phone = Column(String, nullable=True)
    payee_phone = Column(String, nullable=True)
    channel = Column(String, nullable=True)  # e.g. "13" = MTN Ghana
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="transactions")


# ---------------------------------------------------------------------------
# Loan
# ---------------------------------------------------------------------------


class Loan(Base):
    """Input / Cash Loan Model"""

    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="GHS")
    purpose = Column(Text, nullable=True)
    status = Column(Enum(LoanStatus), default=LoanStatus.requested)
    # Approval
    approved_by = Column(String, nullable=True)  # admin name / id
    approved_at = Column(DateTime, nullable=True)
    # Disbursement
    moolre_transfer_ref = Column(String, nullable=True)
    disbursed_at = Column(DateTime, nullable=True)
    # Repayment
    repaid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="loans")


# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------


class Production(Base):
    """Production / Harvest Tracking Model"""

    __tablename__ = "productions"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    crop_type = Column(String, nullable=False)
    season = Column(String, nullable=True)  # e.g. "2025A"
    expected_kg = Column(Float, nullable=True)
    planted_date = Column(DateTime, nullable=True)
    harvest_date = Column(DateTime, nullable=True)
    quantity_kg = Column(Float, nullable=True)
    quality_grade = Column(String, nullable=True)  # A, B, C
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="productions")


# ---------------------------------------------------------------------------
# Trust Score
# ---------------------------------------------------------------------------


class TrustScore(Base):
    """Trust Score Snapshot History"""

    __tablename__ = "trust_scores"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    score = Column(Float, nullable=False)
    payment_compliance = Column(Float, default=0.0)
    production_history = Column(Float, default=0.0)
    loan_repayment = Column(Float, default=0.0)
    attendance = Column(Float, default=0.0)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="trust_scores")


# ---------------------------------------------------------------------------
# Cooperative Attendance
# ---------------------------------------------------------------------------


class CooperativeAttendance(Base):
    """Meeting / Training Attendance Record"""

    __tablename__ = "cooperative_attendances"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    event_name = Column(String, nullable=False)
    event_date = Column(DateTime, nullable=False)
    attended = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="attendances")


# ---------------------------------------------------------------------------
# Communication Log
# ---------------------------------------------------------------------------


class CommunicationLog(Base):
    """Log of SMS / WhatsApp messages sent"""

    __tablename__ = "communication_logs"

    id = Column(Integer, primary_key=True, index=True)
    message_type = Column(Enum(MessageType), default=MessageType.sms)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=True)
    recipients_count = Column(Integer, default=0)
    body = Column(Text, nullable=False)
    moolre_ref = Column(String, nullable=True)
    sent_by = Column(String, nullable=True)  # admin identifier
    status = Column(String, default="sent")
    sent_at = Column(DateTime, default=datetime.utcnow)
