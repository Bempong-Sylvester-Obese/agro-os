"""Loan Management Routes"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import Farmer, Loan, LoanStatus, Transaction, TransactionStatus, TransactionType, User
from app.services.auth_service import get_current_user
from app.schemas.schemas import LoanApprove, LoanCreate, LoanResponse
from app.services.moolre_service import MoolreService
from app.services.trust_score_service import TrustScoreService

router = APIRouter(prefix="/loans", tags=["loans"])


def _get_loan_or_404(loan_id: int, db: Session) -> Loan:
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@router.post("/", response_model=LoanResponse, status_code=201)
def create_loan(loan_in: LoanCreate, db: Session = Depends(get_db)):
    """Farmer requests an input / cash loan."""
    farmer = db.query(Farmer).filter(Farmer.id == loan_in.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    loan = Loan(**loan_in.model_dump())
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.get("/", response_model=list[LoanResponse])
def list_loans(
    farmer_id: int | None = None,
    status: LoanStatus | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List loans with optional filters."""
    query = db.query(Loan)
    if current_user.cooperative_id:
        query = query.join(Farmer, Loan.farmer_id == Farmer.id).filter(Farmer.cooperative_id == current_user.cooperative_id)
    if farmer_id is not None:
        query = query.filter(Loan.farmer_id == farmer_id)
    if status is not None:
        query = query.filter(Loan.status == status)
    return query.order_by(Loan.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{loan_id}", response_model=LoanResponse)
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    """Get loan details."""
    return _get_loan_or_404(loan_id, db)


@router.post("/{loan_id}/approve", response_model=LoanResponse)
def approve_loan(loan_id: int, approval: LoanApprove, db: Session = Depends(get_db)):
    """Approve a requested loan."""
    loan = _get_loan_or_404(loan_id, db)
    if loan.status != LoanStatus.requested:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve loan in '{loan.status}' state. Must be 'requested'.",
        )
    loan.status = LoanStatus.approved
    loan.approved_by = approval.approved_by
    loan.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(loan)
    return loan


@router.post("/{loan_id}/reject", response_model=LoanResponse)
def reject_loan(loan_id: int, db: Session = Depends(get_db)):
    """Reject a requested loan."""
    loan = _get_loan_or_404(loan_id, db)
    if loan.status != LoanStatus.requested:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject loan in '{loan.status}' state.",
        )
    loan.status = LoanStatus.rejected
    db.commit()
    db.refresh(loan)
    return loan


@router.post("/{loan_id}/disburse", response_model=LoanResponse)
async def disburse_loan(loan_id: int, db: Session = Depends(get_db)):
    """
    Disburse an approved loan by triggering a Moolre transfer to the farmer's phone.
    Marks loan as 'disbursed' and creates a payout Transaction record.
    """
    loan = _get_loan_or_404(loan_id, db)
    if loan.status != LoanStatus.approved:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot disburse loan in '{loan.status}' state. Must be 'approved'.",
        )

    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    ext_ref = str(uuid.uuid4())
    moolre = MoolreService()
    transfer_result = await moolre.initiate_transfer(
        receiver_phone=farmer.phone,
        amount=loan.amount,
        currency=loan.currency,
        external_ref=ext_ref,
        reference=f"AgroOS loan #{loan.id}",
    )

    if not transfer_result["success"]:
        failed_tx = Transaction(
            farmer_id=farmer.id,
            transaction_type=TransactionType.payout,
            amount=loan.amount,
            currency=loan.currency,
            status=TransactionStatus.failed,
            moolre_transfer_ref=transfer_result.get("moolre_transfer_ref"),
            payee_phone=farmer.phone,
            description=f"Loan disbursement #{loan.id}",
        )
        db.add(failed_tx)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Moolre transfer failed: {transfer_result['message']}",
        )

    tx = Transaction(
        farmer_id=farmer.id,
        transaction_type=TransactionType.payout,
        amount=loan.amount,
        currency=loan.currency,
        status=TransactionStatus.completed,
        moolre_transfer_ref=transfer_result.get("moolre_transfer_ref"),
        payee_phone=farmer.phone,
        description=f"Loan disbursement #{loan.id}",
    )
    db.add(tx)

    loan.status = LoanStatus.disbursed
    loan.moolre_transfer_ref = transfer_result.get("moolre_transfer_ref")
    loan.disbursed_at = datetime.utcnow()
    db.commit()
    db.refresh(loan)

    return loan


@router.post("/{loan_id}/repay", response_model=LoanResponse)
def repay_loan(loan_id: int, db: Session = Depends(get_db)):
    """
    Record full repayment of a disbursed loan.
    Creates a repayment Transaction and recalculates Trust Score.
    """
    loan = _get_loan_or_404(loan_id, db)
    if loan.status != LoanStatus.disbursed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot repay loan in '{loan.status}' state. Must be 'disbursed'.",
        )

    # Repayment transaction
    tx = Transaction(
        farmer_id=loan.farmer_id,
        transaction_type=TransactionType.repayment,
        amount=loan.amount,
        currency=loan.currency,
        status=TransactionStatus.completed,
        description=f"Loan repayment #{loan.id}",
    )
    db.add(tx)

    loan.status = LoanStatus.repaid
    loan.repaid_at = datetime.utcnow()
    db.commit()

    # Recalculate trust score
    TrustScoreService.calculate_trust_score(loan.farmer_id, db)

    db.refresh(loan)
    return loan
