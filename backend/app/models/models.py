"""Database Models for AgroOS"""

import enum
from datetime import date, datetime, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
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


class ProductionFocus(str, enum.Enum):
    crop = "crop"
    animal = "animal"
    mixed = "mixed"


class ProductionKind(str, enum.Enum):
    crop = "crop"
    animal = "animal"


class TransactionType(str, enum.Enum):
    dues = "dues"
    loan = "loan"
    payout = "payout"
    settlement_payout = "settlement_payout"
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
    cancelled = "cancelled"


class MessageType(str, enum.Enum):
    sms = "sms"
    whatsapp = "whatsapp"


class IntakeStatus(str, enum.Enum):
    received = "received"
    accepted = "accepted"
    rejected = "rejected"
    batched = "batched"
    cancelled = "cancelled"


class AggregationBatchStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    sold = "sold"


class ProduceSaleStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    funded = "funded"
    settled = "settled"


class ReceiptStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class SettlementStatus(str, enum.Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"
    processing = "processing"
    partially_paid = "partially_paid"
    completed = "completed"


class SettlementLineStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    paid = "paid"
    failed = "failed"


class SettlementDeductionType(str, enum.Enum):
    cooperative_fee = "cooperative_fee"
    transport = "transport"
    quality = "quality"
    manual = "manual"
    loan = "loan"


class DisbursementBatchStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    partially_failed = "partially_failed"
    completed = "completed"


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
    is_active = Column(Boolean, default=True, nullable=False)
    onboarding_role = Column(String, nullable=True)
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
    subscription_plan = Column(String, default="starter", nullable=False)
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
    production_focus = Column(
        Enum(ProductionFocus, native_enum=False),
        default=ProductionFocus.crop,
        server_default=ProductionFocus.crop.value,
        nullable=False,
        index=True,
    )
    animal_type = Column(String, nullable=True)
    animal_scale = Column(Float, nullable=True)
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
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True, index=True)
    settlement_line_id = Column(
        Integer, ForeignKey("settlement_lines.id"), nullable=True, index=True
    )
    disbursement_batch_id = Column(
        Integer, ForeignKey("disbursement_batches.id"), nullable=True, index=True
    )
    # Participant phones (for USSD / mobile money)
    payer_phone = Column(String, nullable=True)
    payee_phone = Column(String, nullable=True)
    channel = Column(String, nullable=True)  # e.g. "13" = MTN Ghana
    description = Column(Text, nullable=True)
    initiation_channel = Column(String, default="legacy", nullable=False)
    customer_action = Column(String, default="none", nullable=False, index=True)
    action_expires_at = Column(DateTime, nullable=True)
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
    request_channel = Column(String, default="legacy", nullable=False)
    # Approval
    approved_by = Column(String, nullable=True)  # admin name / id
    approved_at = Column(DateTime, nullable=True)
    # Rejection
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(String, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    # Disbursement
    moolre_transfer_ref = Column(String, nullable=True)
    disbursed_at = Column(DateTime, nullable=True)
    # Repayment
    repaid_at = Column(DateTime, nullable=True)
    # Cancellation
    cancelled_by = Column(String, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmer = relationship("CooperativeMembership", back_populates="loans")
    reminders = relationship("LoanReminder", back_populates="loan")

    @property
    def due_state(self) -> str:
        if self.status == LoanStatus.repaid:
            return "paid"
        if self.status != LoanStatus.disbursed or not self.expected_repayment_date:
            return "not_due"
        delta = (self.expected_repayment_date - date.today()).days
        if delta < 0:
            return "overdue"
        if delta == 0:
            return "due_today"
        if delta <= 7:
            return "due_soon"
        return "scheduled"

    @property
    def days_overdue(self) -> int:
        if self.due_state != "overdue" or not self.expected_repayment_date:
            return 0
        return (date.today() - self.expected_repayment_date).days

    @property
    def last_reminder_at(self):
        sent = [reminder.sent_at for reminder in self.reminders if reminder.sent_at]
        return max(sent) if sent else None

    @property
    def next_reminder_date(self):
        if self.status != LoanStatus.disbursed or not self.expected_repayment_date:
            return None
        today = date.today()
        before_due = [
            self.expected_repayment_date - timedelta(days=days)
            for days in (7, 3, 1, 0)
        ]
        upcoming = [scheduled for scheduled in before_due if scheduled >= today]
        if upcoming:
            return min(upcoming)
        days_overdue = (today - self.expected_repayment_date).days
        overdue_intervals = [1, 3, 7]
        future_intervals = [
            interval for interval in overdue_intervals if interval >= days_overdue
        ]
        if future_intervals:
            return self.expected_repayment_date + timedelta(days=min(future_intervals))
        weeks = (days_overdue // 7) + 1
        return self.expected_repayment_date + timedelta(days=weeks * 7)


class LoanReminder(Base):
    """Idempotent delivery record for a loan repayment reminder."""

    __tablename__ = "loan_reminders"
    __table_args__ = (
        UniqueConstraint(
            "loan_id",
            "reminder_kind",
            "scheduled_for",
            name="uq_loan_reminder_delivery",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    reminder_kind = Column(String, nullable=False)
    scheduled_for = Column(Date, nullable=False)
    status = Column(String, default="pending", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    provider_reference = Column(String, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    manual = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    loan = relationship("Loan", back_populates="reminders")


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
    crop_type = Column(String, nullable=True)
    production_kind = Column(
        Enum(ProductionKind, native_enum=False),
        default=ProductionKind.crop,
        server_default=ProductionKind.crop.value,
        nullable=False,
        index=True,
    )
    product_name = Column(String, nullable=True)
    activity = Column(String, nullable=True)
    unit = Column(String, default="kg", server_default="kg", nullable=False)
    expected_quantity = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    production_date = Column(DateTime, nullable=True)
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


# ---------------------------------------------------------------------------
# Administrator Audit Trail
# ---------------------------------------------------------------------------


class AdminAuditLog(Base):
    """Append-only cooperative-scoped record of administrator actions."""

    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    actor_id = Column(String, nullable=False)
    action = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
        index=True,
    )


class AdminActionConfirmation(Base):
    """Single-use confirmation for a sensitive administrator action."""

    __tablename__ = "admin_action_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(String, unique=True, nullable=False, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False)


class DemoBooking(Base):
    """Persisted marketing consultation request."""

    __tablename__ = "demo_bookings"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)
    cooperative = Column(String, nullable=False)
    size = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    selected_date = Column(Date, nullable=False, index=True)
    selected_time = Column(String, nullable=False)
    is_enterprise = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# Cooperative produce market and settlement workflow
# ---------------------------------------------------------------------------


class ProduceIntake(Base):
    __tablename__ = "produce_intakes"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    membership_id = Column(
        Integer, ForeignKey("cooperative_memberships.id"), nullable=False, index=True
    )
    aggregation_batch_id = Column(
        Integer, ForeignKey("aggregation_batches.id"), nullable=True, index=True
    )
    crop_type = Column(String, nullable=False)
    quantity_kg = Column(Numeric(18, 3), nullable=False)
    net_quantity_kg = Column(Numeric(18, 3), nullable=True)
    quality_grade = Column(String, nullable=True)
    collection_point = Column(String, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(IntakeStatus), default=IntakeStatus.received, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    membership = relationship("CooperativeMembership")
    aggregation_batch = relationship("AggregationBatch", back_populates="intakes")


class AggregationBatch(Base):
    __tablename__ = "aggregation_batches"
    __table_args__ = (
        UniqueConstraint("cooperative_id", "code", name="uq_aggregation_batch_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    crop_type = Column(String, nullable=False)
    status = Column(
        Enum(AggregationBatchStatus), default=AggregationBatchStatus.open, nullable=False
    )
    total_quantity_kg = Column(Numeric(18, 3), default=0, nullable=False)
    created_by = Column(String, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    intakes = relationship("ProduceIntake", back_populates="aggregation_batch")
    sales = relationship("ProduceSale", back_populates="aggregation_batch")


class Buyer(Base):
    __tablename__ = "buyers"
    __table_args__ = (
        UniqueConstraint("cooperative_id", "name", name="uq_buyer_cooperative_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales = relationship("ProduceSale", back_populates="buyer")


class ProduceSale(Base):
    __tablename__ = "produce_sales"
    __table_args__ = (
        UniqueConstraint(
            "aggregation_batch_id",
            name="uq_produce_sale_aggregation_batch",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    aggregation_batch_id = Column(
        Integer, ForeignKey("aggregation_batches.id"), nullable=False, index=True
    )
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=False, index=True)
    quantity_kg = Column(Numeric(18, 3), nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    gross_amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String, default="GHS", nullable=False)
    status = Column(Enum(ProduceSaleStatus), default=ProduceSaleStatus.draft, nullable=False)
    sold_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    aggregation_batch = relationship("AggregationBatch", back_populates="sales")
    buyer = relationship("Buyer", back_populates="sales")
    receipts = relationship("BuyerPaymentReceipt", back_populates="sale")
    settlement_runs = relationship("SettlementRun", back_populates="sale")


class BuyerPaymentReceipt(Base):
    __tablename__ = "buyer_payment_receipts"
    __table_args__ = (
        UniqueConstraint("cooperative_id", "reference", name="uq_buyer_receipt_reference"),
    )

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    sale_id = Column(Integer, ForeignKey("produce_sales.id"), nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    reference = Column(String, nullable=False)
    status = Column(Enum(ReceiptStatus), default=ReceiptStatus.pending, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_by = Column(String, nullable=False)
    verified_by = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sale = relationship("ProduceSale", back_populates="receipts")


class SettlementRun(Base):
    __tablename__ = "settlement_runs"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    sale_id = Column(Integer, ForeignKey("produce_sales.id"), nullable=False, index=True)
    status = Column(Enum(SettlementStatus), default=SettlementStatus.draft, nullable=False)
    currency = Column(String, default="GHS", nullable=False)
    cooperative_fee_percent = Column(Numeric(7, 4), default=0, nullable=False)
    transport_total = Column(Numeric(18, 2), default=0, nullable=False)
    quality_total = Column(Numeric(18, 2), default=0, nullable=False)
    gross_total = Column(Numeric(18, 2), nullable=False)
    verified_funds_total = Column(Numeric(18, 2), nullable=False)
    deductions_total = Column(Numeric(18, 2), nullable=False)
    net_total = Column(Numeric(18, 2), nullable=False)
    snapshot_json = Column(Text, nullable=False)
    calculated_by = Column(String, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sale = relationship("ProduceSale", back_populates="settlement_runs")
    lines = relationship("SettlementLine", back_populates="settlement_run")
    disbursement_batches = relationship(
        "DisbursementBatch", back_populates="settlement_run"
    )


class SettlementLine(Base):
    __tablename__ = "settlement_lines"
    __table_args__ = (
        UniqueConstraint("settlement_run_id", "membership_id", name="uq_settlement_member"),
    )

    id = Column(Integer, primary_key=True, index=True)
    settlement_run_id = Column(
        Integer, ForeignKey("settlement_runs.id"), nullable=False, index=True
    )
    membership_id = Column(
        Integer, ForeignKey("cooperative_memberships.id"), nullable=False, index=True
    )
    quantity_kg = Column(Numeric(18, 3), nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    gross_amount = Column(Numeric(18, 2), nullable=False)
    deductions_total = Column(Numeric(18, 2), nullable=False)
    net_amount = Column(Numeric(18, 2), nullable=False)
    status = Column(
        Enum(SettlementLineStatus), default=SettlementLineStatus.pending, nullable=False
    )
    payout_reference = Column(String, unique=True, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    settlement_run = relationship("SettlementRun", back_populates="lines")
    membership = relationship("CooperativeMembership")
    deductions = relationship("SettlementDeduction", back_populates="settlement_line")
    transactions = relationship("Transaction", foreign_keys="Transaction.settlement_line_id")


class SettlementDeduction(Base):
    __tablename__ = "settlement_deductions"

    id = Column(Integer, primary_key=True, index=True)
    settlement_line_id = Column(
        Integer, ForeignKey("settlement_lines.id"), nullable=False, index=True
    )
    deduction_type = Column(Enum(SettlementDeductionType), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    description = Column(Text, nullable=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    settlement_line = relationship("SettlementLine", back_populates="deductions")


class DisbursementBatch(Base):
    __tablename__ = "disbursement_batches"

    id = Column(Integer, primary_key=True, index=True)
    settlement_run_id = Column(
        Integer, ForeignKey("settlement_runs.id"), nullable=False, index=True
    )
    status = Column(
        Enum(DisbursementBatchStatus),
        default=DisbursementBatchStatus.pending,
        nullable=False,
    )
    attempt_number = Column(Integer, default=1, nullable=False)
    created_by = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    settlement_run = relationship("SettlementRun", back_populates="disbursement_batches")
    transactions = relationship(
        "Transaction", foreign_keys="Transaction.disbursement_batch_id"
    )
