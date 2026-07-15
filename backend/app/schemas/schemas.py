"""Pydantic Schemas for Request / Response"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.models import (
    LoanStatus,
    MembershipStatus,
    TransactionStatus,
    TransactionType,
)

# ===========================================================================
# Cooperative
# ===========================================================================


class CooperativeBase(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    currency: str = "GHS"
    moolre_account_number: Optional[str] = None


class CooperativeCreate(CooperativeBase):
    pass


class CooperativeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    currency: Optional[str] = None
    moolre_account_number: Optional[str] = None


class CooperativeResponse(CooperativeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# Farmer
# ===========================================================================


class FarmerBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    location: Optional[str] = None
    crop_type: Optional[str] = None
    acreage: Optional[float] = None
    cooperative_id: int


class FarmerCreate(FarmerBase):
    pass


class FarmerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    crop_type: Optional[str] = None
    acreage: Optional[float] = None
    membership_status: Optional[MembershipStatus] = None
    cooperative_id: Optional[int] = None


class FarmerResponse(FarmerBase):
    # `id` is the cooperative membership ID used by cooperative operations.
    id: int
    farmer_id: int
    membership_status: MembershipStatus
    trust_score: float
    existing_farmer: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# Transaction
# ===========================================================================


class TransactionBase(BaseModel):
    farmer_id: int
    transaction_type: TransactionType
    amount: float = Field(..., gt=0)
    currency: str = "GHS"
    description: Optional[str] = None
    payer_phone: Optional[str] = None
    payee_phone: Optional[str] = None
    channel: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: int
    status: TransactionStatus
    moolre_reference: Optional[str] = None
    moolre_transfer_ref: Optional[str] = None
    loan_id: Optional[int] = None
    settlement_line_id: Optional[int] = None
    disbursement_batch_id: Optional[int] = None
    initiation_channel: str = "legacy"
    customer_action: str = "none"
    action_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionStatusUpdate(BaseModel):
    status: TransactionStatus


# ---------------------------------------------------------------------------
# Dues collection via Moolre USSD push
# ---------------------------------------------------------------------------


class DuesCollectRequest(BaseModel):
    farmer_id: int
    amount: float = Field(..., gt=0)
    channel: str = Field("13", description="Moolre channel code. 13=MTN Ghana, 6=Telecel, 7=AT")
    description: Optional[str] = "Cooperative dues payment"


class DuesCollectResponse(BaseModel):
    transaction_id: int
    moolre_reference: Optional[str] = None
    status: str
    message: str
    verification_required: bool = False
    outcome: Optional[str] = None
    moolre_code: Optional[str] = None
    customer_action: str = "none"
    action_expires_at: Optional[datetime] = None


class PaymentLinkRequest(BaseModel):
    farmer_id: int
    amount: float = Field(..., gt=0)
    email: str
    description: Optional[str] = "Cooperative payment"
    currency: str = "GHS"


class PaymentLinkResponse(BaseModel):
    success: bool
    payment_url: Optional[str] = None
    reference: Optional[str] = None
    transaction_id: int


class PaymentWebhookEventResponse(BaseModel):
    id: int
    event_type: str
    moolre_reference: Optional[str] = None
    transaction_id: Optional[int] = None
    signature_valid: bool
    processed: bool
    message: Optional[str] = None
    received_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# Loan
# ===========================================================================


class LoanCreate(BaseModel):
    farmer_id: int
    amount: float = Field(..., gt=0)
    currency: str = "GHS"
    purpose: Optional[str] = None
    expected_repayment_date: Optional[date] = Field(None, alias="repayment_date")

    model_config = {"populate_by_name": True}


class LoanCancel(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class LoanApproval(BaseModel):
    expected_repayment_date: Optional[date] = None


class LoanRejection(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class LoanResponse(BaseModel):
    id: int
    farmer_id: int
    amount: float
    currency: str
    purpose: Optional[str] = None
    expected_repayment_date: Optional[date] = None
    status: LoanStatus
    request_channel: str = "legacy"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    notification_status: Optional[str] = None
    moolre_transfer_ref: Optional[str] = None
    disbursed_at: Optional[datetime] = None
    repaid_at: Optional[datetime] = None
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    due_state: str = "not_due"
    days_overdue: int = 0
    last_reminder_at: Optional[datetime] = None
    next_reminder_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoanDisbursementStatus(BaseModel):
    loan_id: int
    loan_status: LoanStatus
    payout_status: str
    transfer_reference: Optional[str] = None
    can_cancel: bool
    can_retry: bool


class LoanReminderResponse(BaseModel):
    id: int
    loan_id: int
    reminder_kind: str
    scheduled_for: date
    status: str
    attempts: int
    provider_reference: Optional[str] = None
    sent_at: Optional[datetime] = None
    error: Optional[str] = None
    manual: bool

    class Config:
        from_attributes = True


# ===========================================================================
# Production
# ===========================================================================


class ProductionBase(BaseModel):
    farmer_id: int
    crop_type: str
    season: Optional[str] = None
    expected_kg: Optional[float] = None
    planted_date: Optional[datetime] = None
    quantity_kg: Optional[float] = None
    quality_grade: Optional[str] = None
    notes: Optional[str] = None


class ProductionCreate(ProductionBase):
    pass


class ProductionUpdate(BaseModel):
    harvest_date: Optional[datetime] = None
    quantity_kg: Optional[float] = None
    quality_grade: Optional[str] = None
    expected_kg: Optional[float] = None
    notes: Optional[str] = None


class ProductionResponse(ProductionBase):
    id: int
    harvest_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductionSummary(BaseModel):
    farmer_id: int
    total_productions: int
    total_kg_harvested: float
    harvest_completion_rate: float  # % of productions that have a harvest date


# ===========================================================================
# Trust Score
# ===========================================================================


class TrustScoreResponse(BaseModel):
    id: int
    farmer_id: int
    score: float
    payment_compliance: float
    production_history: float
    loan_repayment: float
    attendance: float
    calculated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# Attendance
# ===========================================================================


class AttendanceCreate(BaseModel):
    farmer_id: int
    event_name: str
    event_date: datetime
    attended: bool = False


class AttendanceResponse(AttendanceCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# Communications
# ===========================================================================


class SMSBroadcastRequest(BaseModel):
    cooperative_id: int
    message: str = Field(..., max_length=160)
    sent_by: Optional[str] = None


class DuesReminderRequest(BaseModel):
    cooperative_id: int
    amount: float
    due_date: str  # human-readable e.g. "30 June 2025"
    sent_by: Optional[str] = None


class SMSResponse(BaseModel):
    status: str
    recipients_count: int
    message: str
    log_id: Optional[int] = None


class CommunicationLogResponse(BaseModel):
    id: int
    message_type: str
    cooperative_id: Optional[int] = None
    recipients_count: int
    body: str
    moolre_ref: Optional[str] = None
    sent_by: Optional[str] = None
    status: str
    sent_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# Moolre / Payment helpers (returned to callers)
# ===========================================================================


class PaymentInitiateResponse(BaseModel):
    success: bool
    moolre_reference: Optional[str] = None
    message: str
    raw: Optional[dict] = None


class TransferInitiateResponse(BaseModel):
    success: bool
    moolre_transfer_ref: Optional[str] = None
    message: str
    raw: Optional[dict] = None


class UssdSessionResponse(BaseModel):
    id: int
    session_id: Optional[str] = None
    phone: str
    input_path: Optional[str] = None
    response_text: str
    farmer_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
