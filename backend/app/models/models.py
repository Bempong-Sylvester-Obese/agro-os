"""Database Models for AgroOS"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
# User
# ---------------------------------------------------------------------------


class User(Base):
    """User / Admin Model for authentication"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="admin")
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to cooperative
    cooperative = relationship("Cooperative")


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
    memberships = relationship("CooperativeMembership", back_populates="cooperative")


# ---------------------------------------------------------------------------
# Farmer
# ---------------------------------------------------------------------------


class Farmer(Base):
    """Global farmer identity shared across cooperative memberships."""

    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships = relationship("CooperativeMembership", back_populates="farmer")


class CooperativeMembership(Base):
    """A farmer's cooperative-specific membership and operating profile."""

    __tablename__ = "cooperative_memberships"
    __table_args__ = (
        UniqueConstraint("farmer_id", "cooperative_id", name="uq_farmer_cooperative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    cooperative_id = Column(
        Integer, ForeignKey("cooperatives.id"), nullable=False, index=True
    )
    crop_type = Column(String, nullable=True)
    acreage = Column(Float, nullable=True)
    membership_status = Column(
        Enum(MembershipStatus), default=MembershipStatus.active
    )
    trust_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="memberships")
    cooperative = relationship("Cooperative", back_populates="memberships")
    transactions = relationship("Transaction", back_populates="farmer")
    productions = relationship("Production", back_populates="farmer")
    loans = relationship("Loan", back_populates="farmer")
    trust_scores = relationship("TrustScore", back_populates="farmer")
    attendances = relationship("CooperativeAttendance", back_populates="farmer")

    @property
    def name(self):
        return self.farmer.name

    @property
    def phone(self):
        return self.farmer.phone

    @property
    def email(self):
        return self.farmer.email

    @property
    def location(self):
        return self.farmer.location


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


class Transaction(Base):
    """Finance Transaction Model (dues, payouts, repayments)"""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(
        "membership_id",
        Integer,
        ForeignKey("cooperative_memberships.id"),
        nullable=False,
        index=True,
    )
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
    farmer = relationship("CooperativeMembership", back_populates="transactions")


# ---------------------------------------------------------------------------
# Loan
# ---------------------------------------------------------------------------


class Loan(Base):
    """Input / Cash Loan Model"""

    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(
        "membership_id",
        Integer,
        ForeignKey("cooperative_memberships.id"),
        nullable=False,
        index=True,
    )
    amount = Column(Float, nullable=False)
    currency = Column(String, default="GHS")
    purpose = Column(Text, nullable=True)
    expected_repayment_date = Column(Date, nullable=True)
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
    farmer = relationship("CooperativeMembership", back_populates="loans")


# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------


class Production(Base):
    """Production / Harvest Tracking Model"""

    __tablename__ = "productions"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(
        "membership_id",
        Integer,
        ForeignKey("cooperative_memberships.id"),
        nullable=False,
        index=True,
    )
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
    farmer = relationship("CooperativeMembership", back_populates="productions")


# ---------------------------------------------------------------------------
# Trust Score
# ---------------------------------------------------------------------------


class TrustScore(Base):
    """Trust Score Snapshot History"""

    __tablename__ = "trust_scores"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(
        "membership_id",
        Integer,
        ForeignKey("cooperative_memberships.id"),
        nullable=False,
        index=True,
    )
    score = Column(Float, nullable=False)
    payment_compliance = Column(Float, default=0.0)
    production_history = Column(Float, default=0.0)
    loan_repayment = Column(Float, default=0.0)
    attendance = Column(Float, default=0.0)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    farmer = relationship("CooperativeMembership", back_populates="trust_scores")


# ---------------------------------------------------------------------------
# Cooperative Attendance
# ---------------------------------------------------------------------------


class CooperativeAttendance(Base):
    """Meeting / Training Attendance Record"""

    __tablename__ = "cooperative_attendances"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(
        "membership_id",
        Integer,
        ForeignKey("cooperative_memberships.id"),
        nullable=False,
        index=True,
    )
    event_name = Column(String, nullable=False)
    event_date = Column(DateTime, nullable=False)
    attended = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    farmer = relationship("CooperativeMembership", back_populates="attendances")


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


# ---------------------------------------------------------------------------
# Payment Webhook Audit
# ---------------------------------------------------------------------------


class PaymentWebhookEvent(Base):
    """Audit log for incoming Moolre payment webhooks."""

    __tablename__ = "payment_webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, default="payment")
    moolre_reference = Column(String, nullable=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    signature_valid = Column(Boolean, default=True)
    payload = Column(Text, nullable=False)
    processed = Column(Boolean, default=False)
    message = Column(String, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# USSD Session Log
# ---------------------------------------------------------------------------


class UssdSession(Base):
    """Lightweight USSD interaction log for dashboard visibility."""

    __tablename__ = "ussd_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=False, index=True)
    input_path = Column(String, nullable=True)
    response_text = Column(Text, nullable=True)
    farmer_id = Column(
        "membership_id",
        Integer,
        ForeignKey("cooperative_memberships.id"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agro-AI Prediction Audit
# ---------------------------------------------------------------------------


class AgroAiPredictionLog(Base):
    """Database audit trail for Agro-AI predictions."""

    __tablename__ = "agro_ai_prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    farmer_id = Column(String, nullable=True)
    cooperative_id = Column(String, nullable=True)
    actor_id = Column(String, nullable=True)
    model_version = Column(String, nullable=False)
    feature_schema_version = Column(String, nullable=False)
    requested_credit_amount = Column(Integer, default=0)
    features = Column(Text, nullable=False)
    prediction = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
