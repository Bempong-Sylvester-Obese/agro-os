"""Contracts for cooperative produce sales and farmer settlements."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.models import (
    AggregationBatchStatus,
    DisbursementBatchStatus,
    IntakeStatus,
    ProduceSaleStatus,
    ReceiptStatus,
    SettlementDeductionType,
    SettlementLineStatus,
    SettlementStatus,
)


class OrmSchema(BaseModel):
    model_config = {"from_attributes": True}


class IntakeCreate(BaseModel):
    cooperative_id: int | None = None
    membership_id: int
    crop_type: str = Field(min_length=1, max_length=100)
    quantity_kg: Decimal = Field(gt=0, decimal_places=3)
    quality_grade: str | None = Field(default=None, max_length=30)
    collection_point: str | None = Field(default=None, max_length=200)
    received_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)


class IntakeResponse(OrmSchema):
    id: int
    cooperative_id: int
    membership_id: int
    aggregation_batch_id: int | None
    crop_type: str
    quantity_kg: Decimal
    net_quantity_kg: Decimal | None
    quality_grade: str | None
    collection_point: str | None
    rejection_reason: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    received_at: datetime
    status: IntakeStatus
    notes: str | None
    created_by: str
    created_at: datetime


class IntakeReview(BaseModel):
    net_quantity_kg: Decimal | None = Field(default=None, gt=0, decimal_places=3)
    quality_grade: str | None = Field(default=None, max_length=30)
    reason: str | None = Field(default=None, max_length=500)


class BatchCreate(BaseModel):
    cooperative_id: int | None = None
    code: str = Field(min_length=1, max_length=80)
    crop_type: str = Field(min_length=1, max_length=100)


class BatchIntakes(BaseModel):
    intake_ids: list[int] = Field(min_length=1)


class BatchResponse(OrmSchema):
    id: int
    cooperative_id: int
    code: str
    crop_type: str
    status: AggregationBatchStatus
    total_quantity_kg: Decimal
    created_by: str
    closed_at: datetime | None
    created_at: datetime


class BuyerCreate(BaseModel):
    cooperative_id: int | None = None
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=1000)


class BuyerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class BuyerResponse(OrmSchema):
    id: int
    cooperative_id: int
    name: str
    phone: str | None
    email: str | None
    address: str | None
    is_active: bool
    created_by: str
    created_at: datetime


class SaleCreate(BaseModel):
    cooperative_id: int | None = None
    aggregation_batch_id: int
    buyer_id: int
    quantity_kg: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="GHS", min_length=3, max_length=3)


class SaleResponse(OrmSchema):
    id: int
    cooperative_id: int
    aggregation_batch_id: int
    buyer_id: int
    quantity_kg: Decimal
    unit_price: Decimal
    gross_amount: Decimal
    currency: str
    status: ProduceSaleStatus
    sold_at: datetime | None
    created_by: str
    created_at: datetime


class ReceiptCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    reference: str = Field(min_length=1, max_length=200)
    received_at: datetime | None = None


class ReceiptDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ReceiptResponse(OrmSchema):
    id: int
    cooperative_id: int
    sale_id: int
    amount: Decimal
    reference: str
    status: ReceiptStatus
    received_at: datetime
    submitted_by: str
    verified_by: str | None
    verified_at: datetime | None
    rejection_reason: str | None
    created_at: datetime


class ManualDeductionInput(BaseModel):
    membership_id: int
    amount: Decimal = Field(gt=0, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)


class SettlementCalculate(BaseModel):
    cooperative_fee_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    transport_total: Decimal = Field(default=Decimal("0"), ge=0)
    quality_total: Decimal = Field(default=Decimal("0"), ge=0)
    manual_deductions: list[ManualDeductionInput] = Field(default_factory=list)
    deduct_outstanding_loans: bool = False


class DeductionResponse(OrmSchema):
    id: int
    deduction_type: SettlementDeductionType
    amount: Decimal
    description: str | None
    loan_id: int | None


class SettlementLineResponse(OrmSchema):
    id: int
    settlement_run_id: int
    membership_id: int
    quantity_kg: Decimal
    unit_price: Decimal
    gross_amount: Decimal
    deductions_total: Decimal
    net_amount: Decimal
    status: SettlementLineStatus
    payout_reference: str
    paid_at: datetime | None
    last_error: str | None
    deductions: list[DeductionResponse] = Field(default_factory=list)


class SettlementResponse(OrmSchema):
    id: int
    cooperative_id: int
    sale_id: int
    status: SettlementStatus
    currency: str
    cooperative_fee_percent: Decimal
    transport_total: Decimal
    quality_total: Decimal
    gross_total: Decimal
    verified_funds_total: Decimal
    deductions_total: Decimal
    net_total: Decimal
    snapshot_json: str
    calculated_by: str
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    lines: list[SettlementLineResponse] = Field(default_factory=list)


class DisbursementBatchResponse(OrmSchema):
    id: int
    settlement_run_id: int
    status: DisbursementBatchStatus
    attempt_number: int
    created_by: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class PayoutResult(BaseModel):
    settlement: SettlementResponse
    disbursement_batch: DisbursementBatchResponse
    attempted_line_ids: list[int]


class ReconciliationResult(BaseModel):
    settlement: SettlementResponse
    reconciled_line_ids: list[int]
