"""Loan Management Routes"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import Cooperative, Farmer, Loan, LoanStatus, Transaction, TransactionStatus, TransactionType, User
from app.services.auth_service import get_current_user
from app.schemas.schemas import LoanApprove, LoanCreate, LoanRepayVerifyRequest, LoanResponse
from app.services.moolre_service import MoolreService
from app.services.trust_score_service import TrustScoreService

router = APIRouter(prefix="/loans", tags=["loans"])


def _disburse_external_ref(loan_id: int) -> str:
    return f"agro-loan-disburse-{loan_id}"


def _repay_external_ref(loan_id: int) -> str:
    return f"agro-loan-repay-{loan_id}"


def _provider_amount_matches(expected: float, provider_amount) -> bool:
    if provider_amount is None or provider_amount == "":
        return False
    try:
        return abs(float(provider_amount) - float(expected)) < 0.01
    except (TypeError, ValueError):
        return False


def _get_loan_or_404(loan_id: int, db: Session) -> Loan:
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


def _cooperative_account(farmer: Farmer, db: Session) -> str | None:
    """Return the cooperative Moolre wallet when configured."""
    cooperative = db.query(Cooperative).filter(Cooperative.id == farmer.cooperative_id).first()
    return cooperative.moolre_account_number if cooperative else None


def _latest_loan_transaction(
    db: Session,
    *,
    loan: Loan,
    transaction_type: TransactionType,
) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(
            Transaction.farmer_id == loan.farmer_id,
            Transaction.transaction_type == transaction_type,
            Transaction.description == f"Loan {'disbursement' if transaction_type == TransactionType.payout else 'repayment'} #{loan.id}",
        )
        .order_by(Transaction.created_at.desc())
        .first()
    )


async def _finalize_disbursement(
    *,
    loan: Loan,
    farmer: Farmer,
    transfer_result: dict,
    status_result: dict,
    db: Session,
) -> Loan:
    if status_result["status"] == "failed":
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
        raise HTTPException(status_code=502, detail="Moolre transfer failed reconciliation")

    if status_result["status"] == "pending":
        pending_tx = Transaction(
            farmer_id=farmer.id,
            transaction_type=TransactionType.payout,
            amount=loan.amount,
            currency=loan.currency,
            status=TransactionStatus.pending,
            moolre_transfer_ref=transfer_result.get("moolre_transfer_ref"),
            payee_phone=farmer.phone,
            description=f"Loan disbursement #{loan.id}",
        )
        db.add(pending_tx)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="Moolre transfer pending — loan remains approved until transfer completes",
        )

    if not _provider_amount_matches(loan.amount, status_result.get("amount")):
        pending_tx = Transaction(
            farmer_id=farmer.id,
            transaction_type=TransactionType.payout,
            amount=loan.amount,
            currency=loan.currency,
            status=TransactionStatus.pending,
            moolre_transfer_ref=transfer_result.get("moolre_transfer_ref"),
            payee_phone=farmer.phone,
            description=f"Loan disbursement #{loan.id}",
        )
        db.add(pending_tx)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="Moolre transfer amount mismatch — loan remains approved",
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


async def _finalize_repayment(
    *,
    loan: Loan,
    tx: Transaction,
    status_result: dict,
    db: Session,
) -> Loan:
    if status_result["status"] == "failed":
        tx.status = TransactionStatus.failed
        db.commit()
        raise HTTPException(status_code=502, detail="Moolre repayment collection failed reconciliation")

    if status_result["status"] == "pending":
        db.refresh(loan)
        return loan

    if not _provider_amount_matches(loan.amount, status_result.get("amount")):
        db.refresh(loan)
        raise HTTPException(
            status_code=502,
            detail="Moolre repayment amount mismatch — loan remains disbursed",
        )

    tx.status = TransactionStatus.completed
    loan.status = LoanStatus.repaid
    loan.repaid_at = datetime.utcnow()
    db.commit()

    TrustScoreService.calculate_trust_score(loan.farmer_id, db)

    db.refresh(loan)
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
    cooperative_id: int | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """List loans with optional filters."""
    settings = get_settings()
    scoped_coop_id = resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=cooperative_id,
        settings=settings,
    )
    query = db.query(Loan).join(Farmer, Loan.farmer_id == Farmer.id).filter(
        Farmer.cooperative_id == scoped_coop_id
    )
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
    if loan.status == LoanStatus.disbursed:
        return loan
    if loan.status != LoanStatus.approved:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot disburse loan in '{loan.status}' state. Must be 'approved'.",
        )

    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    ext_ref = _disburse_external_ref(loan.id)
    moolre = MoolreService()
    # Always disburse from the platform merchant wallet (MoMo-enabled), not an alternate coop wallet.
    account_number, wallet_error = await moolre.resolve_verified_account(None)
    if wallet_error:
        raise HTTPException(status_code=502, detail=wallet_error)

    existing_tx = _latest_loan_transaction(db, loan=loan, transaction_type=TransactionType.payout)
    if existing_tx and existing_tx.status == TransactionStatus.completed:
        loan.status = LoanStatus.disbursed
        loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
        db.commit()
        db.refresh(loan)
        return loan

    if existing_tx and existing_tx.status == TransactionStatus.pending:
        status_result = await moolre.transfer_status(
            external_ref=ext_ref,
            account_number=account_number,
        )
        transfer_result = {"moolre_transfer_ref": existing_tx.moolre_transfer_ref, "external_ref": ext_ref}
        return await _finalize_disbursement(
            loan=loan,
            farmer=farmer,
            transfer_result=transfer_result,
            status_result=status_result,
            db=db,
        )

    transfer_result = await moolre.initiate_transfer(
        receiver_phone=farmer.phone,
        amount=loan.amount,
        currency=loan.currency,
        external_ref=ext_ref,
        reference=f"AgroOS loan #{loan.id}",
        account_number=account_number,
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

    status_result = await moolre.transfer_status(
        external_ref=transfer_result.get("external_ref") or ext_ref,
        account_number=account_number,
    )
    return await _finalize_disbursement(
        loan=loan,
        farmer=farmer,
        transfer_result=transfer_result,
        status_result=status_result,
        db=db,
    )


@router.post("/{loan_id}/repay", response_model=LoanResponse)
async def repay_loan(loan_id: int, db: Session = Depends(get_db)):
    """
    Initiate Moolre collection for loan repayment.
    Marks the loan repaid only after payment_status confirms the collection.
    """
    loan = _get_loan_or_404(loan_id, db)
    if loan.status == LoanStatus.repaid:
        return loan
    if loan.status != LoanStatus.disbursed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot repay loan in '{loan.status}' state. Must be 'disbursed'.",
        )

    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    ext_ref = _repay_external_ref(loan.id)
    moolre = MoolreService()
    account_number = _cooperative_account(farmer, db)

    existing_tx = _latest_loan_transaction(db, loan=loan, transaction_type=TransactionType.repayment)
    if existing_tx and existing_tx.status == TransactionStatus.pending:
        status_result = await moolre.payment_status(
            external_ref=existing_tx.moolre_reference or ext_ref,
            account_number=account_number,
        )
        return await _finalize_repayment(loan=loan, tx=existing_tx, status_result=status_result, db=db)

    payment_result = await moolre.initiate_payment(
        payer_phone=farmer.phone,
        amount=loan.amount,
        currency=loan.currency,
        external_ref=ext_ref,
        reference=f"Loan repayment #{loan.id}",
        account_number=account_number,
    )

    if not payment_result["success"] and not payment_result.get("verification_required"):
        failed_tx = Transaction(
            farmer_id=loan.farmer_id,
            transaction_type=TransactionType.repayment,
            amount=loan.amount,
            currency=loan.currency,
            status=TransactionStatus.failed,
            moolre_reference=payment_result.get("external_ref") or ext_ref,
            payer_phone=farmer.phone,
            description=f"Loan repayment #{loan.id}",
        )
        db.add(failed_tx)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Moolre repayment collection failed: {payment_result['message']}",
        )

    moolre_ref = payment_result.get("moolre_reference") or ext_ref
    tx = Transaction(
        farmer_id=loan.farmer_id,
        transaction_type=TransactionType.repayment,
        amount=loan.amount,
        currency=loan.currency,
        status=TransactionStatus.pending,
        moolre_reference=moolre_ref,
        payer_phone=farmer.phone,
        description=f"Loan repayment #{loan.id}",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    if payment_result.get("verification_required"):
        raise HTTPException(
            status_code=428,
            detail={
                "message": "OTP verification required. Retry via POST /loans/{loan_id}/repay/verify.",
                "transaction_id": tx.id,
                "loan_id": loan.id,
            },
        )

    status_result = await moolre.payment_status(
        external_ref=payment_result.get("external_ref") or ext_ref,
        account_number=account_number,
    )
    return await _finalize_repayment(loan=loan, tx=tx, status_result=status_result, db=db)


@router.post("/{loan_id}/repay/verify", response_model=LoanResponse)
async def verify_loan_repay(
    loan_id: int,
    body: LoanRepayVerifyRequest,
    db: Session = Depends(get_db),
):
    """Submit OTP to complete a pending loan repayment collection."""
    loan = _get_loan_or_404(loan_id, db)
    if loan.status != LoanStatus.disbursed:
        raise HTTPException(status_code=409, detail="Loan is not awaiting repayment")

    farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    tx = _latest_loan_transaction(db, loan=loan, transaction_type=TransactionType.repayment)
    if not tx or tx.status != TransactionStatus.pending:
        raise HTTPException(status_code=404, detail="No pending repayment transaction found")

    ext_ref = tx.moolre_reference or _repay_external_ref(loan.id)
    moolre = MoolreService()
    account_number = _cooperative_account(farmer, db)
    payment_result = await moolre.initiate_payment(
        payer_phone=farmer.phone,
        amount=loan.amount,
        currency=loan.currency,
        external_ref=ext_ref,
        otpcode=body.otp_code,
        reference=f"Loan repayment #{loan.id}",
        account_number=account_number,
    )

    if not payment_result["success"] and not payment_result.get("verification_required"):
        tx.status = TransactionStatus.failed
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Moolre repayment verification failed: {payment_result['message']}",
        )

    if payment_result.get("verification_required"):
        raise HTTPException(
            status_code=428,
            detail={
                "message": "OTP verification still required.",
                "transaction_id": tx.id,
                "loan_id": loan.id,
            },
        )

    status_result = await moolre.payment_status(
        external_ref=payment_result.get("external_ref") or ext_ref,
        account_number=account_number,
    )
    return await _finalize_repayment(loan=loan, tx=tx, status_result=status_result, db=db)
