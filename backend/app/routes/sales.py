"""Produce sales and buyer-funds verification."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import (
    AdminAuditLog,
    AggregationBatch,
    AggregationBatchStatus,
    Buyer,
    BuyerPaymentReceipt,
    ProduceSale,
    ProduceSaleStatus,
    ReceiptStatus,
    User,
)
from app.schemas.market import (
    ReceiptCreate,
    ReceiptDecision,
    ReceiptResponse,
    SaleCreate,
    SaleResponse,
)
from app.services.auth_service import get_current_user, require_roles

router = APIRouter(prefix="/sales", tags=["produce-sales"])
CENT = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def _scope(user: User | None, cooperative_id: int | None) -> int:
    return resolve_cooperative_scope(
        current_user=user,
        cooperative_id=cooperative_id,
        settings=get_settings(),
    )


def _actor(user: User | None) -> str:
    return str(user.id) if user else "system"


def _sale(
    db: Session, sale_id: int, cooperative_id: int, *, lock: bool = False
) -> ProduceSale:
    query = db.query(ProduceSale).filter(
        ProduceSale.id == sale_id,
        ProduceSale.cooperative_id == cooperative_id,
    )
    sale = query.with_for_update().first() if lock else query.first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale


def _audit(
    db: Session,
    sale: ProduceSale,
    actor: str,
    action: str,
    details: str | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            cooperative_id=sale.cooperative_id,
            actor_id=actor,
            action=action,
            resource_type="produce_sale",
            resource_id=str(sale.id),
            details=details,
        )
    )


@router.post("/", response_model=SaleResponse, status_code=201)
def create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer", "sales_officer")
    ),
):
    cooperative_id = _scope(current_user, payload.cooperative_id)
    batch = (
        db.query(AggregationBatch)
        .filter(
            AggregationBatch.id == payload.aggregation_batch_id,
            AggregationBatch.cooperative_id == cooperative_id,
        )
        .with_for_update()
        .first()
    )
    buyer = db.query(Buyer).filter(
        Buyer.id == payload.buyer_id,
        Buyer.cooperative_id == cooperative_id,
        Buyer.is_active.is_(True),
    ).first()
    if not batch or not buyer:
        raise HTTPException(status_code=404, detail="Batch or buyer not found")
    if batch.status != AggregationBatchStatus.closed:
        raise HTTPException(status_code=409, detail="Batch must be closed before sale")
    if (
        db.query(ProduceSale)
        .filter(ProduceSale.aggregation_batch_id == batch.id)
        .first()
    ):
        raise HTTPException(
            status_code=409,
            detail="This aggregation batch already has a sale",
        )
    if Decimal(payload.quantity_kg) > Decimal(str(batch.total_quantity_kg)):
        raise HTTPException(
            status_code=422,
            detail="Sale quantity exceeds aggregated quantity",
        )
    gross = _money(Decimal(payload.quantity_kg) * Decimal(payload.unit_price))
    sale = ProduceSale(
        cooperative_id=cooperative_id,
        aggregation_batch_id=batch.id,
        buyer_id=buyer.id,
        quantity_kg=payload.quantity_kg,
        unit_price=payload.unit_price,
        gross_amount=gross,
        currency=payload.currency.upper(),
        created_by=_actor(current_user),
    )
    db.add(sale)
    db.flush()
    _audit(db, sale, _actor(current_user), "produce_sale.created")
    db.commit()
    db.refresh(sale)
    return sale


@router.get("/", response_model=list[SaleResponse])
def list_sales(
    cooperative_id: int | None = None,
    status: ProduceSaleStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    scoped_id = _scope(current_user, cooperative_id)
    query = db.query(ProduceSale).filter(ProduceSale.cooperative_id == scoped_id)
    if status is not None:
        query = query.filter(ProduceSale.status == status)
    return query.order_by(ProduceSale.created_at.desc()).all()


@router.post("/{sale_id}/confirm", response_model=SaleResponse)
def confirm_sale(
    sale_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer", "sales_officer")
    ),
):
    scoped_id = _scope(current_user, cooperative_id)
    sale = _sale(db, sale_id, scoped_id, lock=True)
    if sale.status != ProduceSaleStatus.draft:
        raise HTTPException(status_code=409, detail="Only a draft sale can be confirmed")
    batch = (
        db.query(AggregationBatch)
        .filter(AggregationBatch.id == sale.aggregation_batch_id)
        .with_for_update()
        .one()
    )
    if batch.status != AggregationBatchStatus.closed:
        raise HTTPException(status_code=409, detail="Sale batch is not closed")
    sale.status = ProduceSaleStatus.confirmed
    sale.sold_at = datetime.utcnow()
    batch.status = AggregationBatchStatus.sold
    _audit(db, sale, _actor(current_user), "produce_sale.confirmed")
    db.commit()
    db.refresh(sale)
    return sale


@router.post(
    "/{sale_id}/receipts",
    response_model=ReceiptResponse,
    status_code=201,
)
def submit_receipt(
    sale_id: int,
    payload: ReceiptCreate,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer", "sales_officer")
    ),
):
    scoped_id = _scope(current_user, cooperative_id)
    sale = _sale(db, sale_id, scoped_id, lock=True)
    if sale.status not in (ProduceSaleStatus.confirmed, ProduceSaleStatus.funded):
        raise HTTPException(status_code=409, detail="Sale is not accepting receipts")
    receipt = BuyerPaymentReceipt(
        cooperative_id=scoped_id,
        sale_id=sale.id,
        amount=payload.amount,
        reference=payload.reference.strip(),
        received_at=payload.received_at or datetime.utcnow(),
        submitted_by=_actor(current_user),
    )
    db.add(receipt)
    db.flush()
    _audit(
        db,
        sale,
        _actor(current_user),
        "buyer_receipt.submitted",
        f"receipt_id={receipt.id};amount={receipt.amount}",
    )
    db.commit()
    db.refresh(receipt)
    return receipt


@router.get("/{sale_id}/receipts", response_model=list[ReceiptResponse])
def list_receipts(
    sale_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    scoped_id = _scope(current_user, cooperative_id)
    _sale(db, sale_id, scoped_id)
    return (
        db.query(BuyerPaymentReceipt)
        .filter(BuyerPaymentReceipt.sale_id == sale_id)
        .order_by(BuyerPaymentReceipt.created_at)
        .all()
    )


def _decide_receipt(
    *,
    db: Session,
    sale_id: int,
    receipt_id: int,
    cooperative_id: int,
    actor: str,
    verify: bool,
    reason: str | None,
) -> BuyerPaymentReceipt:
    sale = _sale(db, sale_id, cooperative_id, lock=True)
    receipt = (
        db.query(BuyerPaymentReceipt)
        .filter(
            BuyerPaymentReceipt.id == receipt_id,
            BuyerPaymentReceipt.sale_id == sale.id,
            BuyerPaymentReceipt.cooperative_id == cooperative_id,
        )
        .with_for_update()
        .first()
    )
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if receipt.status != ReceiptStatus.pending:
        raise HTTPException(status_code=409, detail="Receipt already decided")
    if actor != "system" and receipt.submitted_by == actor:
        raise HTTPException(
            status_code=409,
            detail="Receipt submitter cannot verify or reject their own receipt",
        )
    if verify:
        verified = _money(
            db.query(func.coalesce(func.sum(BuyerPaymentReceipt.amount), 0))
            .filter(
                BuyerPaymentReceipt.sale_id == sale.id,
                BuyerPaymentReceipt.status == ReceiptStatus.verified,
            )
            .scalar()
        )
        if verified + _money(receipt.amount) > _money(sale.gross_amount):
            raise HTTPException(
                status_code=409,
                detail="Verified receipts would exceed sale gross amount",
            )
        receipt.status = ReceiptStatus.verified
        receipt.verified_by = actor
        receipt.verified_at = datetime.utcnow()
        if verified + _money(receipt.amount) == _money(sale.gross_amount):
            sale.status = ProduceSaleStatus.funded
        action = "buyer_receipt.verified"
    else:
        if not reason or len(reason.strip()) < 3:
            raise HTTPException(status_code=422, detail="Rejection reason is required")
        receipt.status = ReceiptStatus.rejected
        receipt.verified_by = actor
        receipt.verified_at = datetime.utcnow()
        receipt.rejection_reason = reason.strip()
        action = "buyer_receipt.rejected"
    _audit(
        db,
        sale,
        actor,
        action,
        f"receipt_id={receipt.id};amount={receipt.amount}",
    )
    db.commit()
    db.refresh(receipt)
    return receipt


@router.post(
    "/{sale_id}/receipts/{receipt_id}/verify",
    response_model=ReceiptResponse,
)
def verify_receipt(
    sale_id: int,
    receipt_id: int,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer")
    ),
):
    return _decide_receipt(
        db=db,
        sale_id=sale_id,
        receipt_id=receipt_id,
        cooperative_id=_scope(current_user, cooperative_id),
        actor=_actor(current_user),
        verify=True,
        reason=None,
    )


@router.post(
    "/{sale_id}/receipts/{receipt_id}/reject",
    response_model=ReceiptResponse,
)
def reject_receipt(
    sale_id: int,
    receipt_id: int,
    payload: ReceiptDecision,
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        require_roles("admin", "finance_officer")
    ),
):
    return _decide_receipt(
        db=db,
        sale_id=sale_id,
        receipt_id=receipt_id,
        cooperative_id=_scope(current_user, cooperative_id),
        actor=_actor(current_user),
        verify=False,
        reason=payload.reason,
    )
