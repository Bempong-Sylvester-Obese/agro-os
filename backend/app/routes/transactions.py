"""Finance Transaction Routes"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import Farmer, Transaction, TransactionStatus, TransactionType
from app.schemas.schemas import (
    DuesCollectRequest,
    DuesCollectResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionStatusUpdate,
)
from app.services.moolre_service import MoolreService

router = APIRouter(prefix="/transactions", tags=["transactions"])


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=TransactionResponse, status_code=201)
def create_transaction(transaction_in: TransactionCreate, db: Session = Depends(get_db)):
    """Create a manual transaction record."""
    farmer = db.query(Farmer).filter(Farmer.id == transaction_in.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    tx = Transaction(**transaction_in.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/", response_model=list[TransactionResponse])
def list_transactions(
    farmer_id: int | None = None,
    status: TransactionStatus | None = None,
    transaction_type: TransactionType | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List transactions with optional filters."""
    query = db.query(Transaction)
    if farmer_id is not None:
        query = query.filter(Transaction.farmer_id == farmer_id)
    if status is not None:
        query = query.filter(Transaction.status == status)
    if transaction_type is not None:
        query = query.filter(Transaction.transaction_type == transaction_type)
    return query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Get a transaction by ID."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.get("/farmer/{farmer_id}", response_model=list[TransactionResponse])
def get_farmer_transactions(farmer_id: int, db: Session = Depends(get_db)):
    """Get all transactions for a specific farmer."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return (
        db.query(Transaction)
        .filter(Transaction.farmer_id == farmer_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )


@router.patch("/{transaction_id}/status", response_model=TransactionResponse)
def update_transaction_status(
    transaction_id: int,
    update: TransactionStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update the status of a transaction."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    tx.status = update.status
    db.commit()
    db.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# Dues collection via Moolre USSD push
# ---------------------------------------------------------------------------


@router.post("/dues/collect", response_model=DuesCollectResponse)
async def collect_dues(request: DuesCollectRequest, db: Session = Depends(get_db)):
    """
    Initiate cooperative dues collection via Moolre USSD payment push.
    Supports OTP verification retry if `external_ref` and `otp_code` are provided.
    Creates a pending Transaction record and fires the Moolre payment request.
    The webhook will later update the status to 'completed' or 'failed'.
    """
    farmer = db.query(Farmer).filter(Farmer.id == request.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    tx = None
    if request.external_ref:
        tx = db.query(Transaction).filter(Transaction.moolre_reference == request.external_ref).first()

    ext_ref = request.external_ref or str(uuid.uuid4())

    if not tx:
        # Create a pending transaction record first
        tx = Transaction(
            farmer_id=farmer.id,
            transaction_type=TransactionType.dues,
            amount=request.amount,
            currency="GHS",
            status=TransactionStatus.pending,
            moolre_reference=ext_ref,
            payer_phone=farmer.phone,
            channel=request.channel,
            description=request.description,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

    # Trigger Moolre payment
    moolre = MoolreService()
    result = await moolre.initiate_payment(
        payer_phone=farmer.phone,
        amount=request.amount,
        currency="GHS",
        channel=request.channel,
        external_ref=ext_ref,
        otpcode=request.otp_code,
        reference=request.description or "Cooperative dues",
    )

    # Update moolre_reference if Moolre returned a different one
    if result.get("moolre_reference") and result["moolre_reference"] != ext_ref:
        tx.moolre_reference = result["moolre_reference"]
        db.commit()

    verification_required = result.get("verification_required", False)
    status = "pending" if (result["success"] or verification_required) else "failed"

    return DuesCollectResponse(
        transaction_id=tx.id,
        moolre_reference=tx.moolre_reference,
        status=status,
        message=result["message"] or ("Payment request sent" if result["success"] else "Moolre request failed"),
        verification_required=verification_required,
    )


# ---------------------------------------------------------------------------
# Moolre sync — list transactions from Moolre account
# ---------------------------------------------------------------------------


@router.get("/moolre/account-transactions")
async def list_moolre_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
):
    """
    Proxy to Moolre List Transactions API for the cooperative wallet.
    Returns raw Moolre transaction data for the finance dashboard.
    """
    moolre = MoolreService()
    return await moolre.list_transactions(
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@router.get("/moolre/wallet-balance")
async def get_wallet_balance():
    """Check cooperative Moolre wallet balance."""
    moolre = MoolreService()
    return await moolre.account_status()
