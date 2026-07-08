"""Extract Agro-AI feature vectors from operational farmer records."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import (
    CooperativeAttendance,
    Farmer,
    Loan,
    LoanStatus,
    Production,
    Transaction,
    TransactionStatus,
    TransactionType,
)


def _ratio(numerator: float, denominator: float, default: float = 0.5) -> float:
    if denominator <= 0:
        return default
    return max(0.0, min(1.0, numerator / denominator))


def extract_features_from_farmer(farmer: Farmer, db: Session) -> dict[str, float]:
    """Build Agro-AI features from DB records; defaults when history is sparse."""

    dues = (
        db.query(Transaction)
        .filter(
            Transaction.farmer_id == farmer.id,
            Transaction.transaction_type == TransactionType.dues,
        )
        .all()
    )
    completed_dues = [tx for tx in dues if tx.status == TransactionStatus.completed]
    dues_payment_rate = _ratio(len(completed_dues), len(dues) if dues else 1)

    recent_cutoff = datetime.utcnow() - timedelta(days=365)
    on_time = sum(
        1
        for tx in completed_dues
        if tx.created_at and tx.created_at >= recent_cutoff
    )
    on_time_payment_rate = _ratio(on_time, max(len(completed_dues), 1))

    productions = db.query(Production).filter(Production.farmer_id == farmer.id).all()
    if productions:
        harvested = [record for record in productions if record.quantity_kg]
        yield_scores = []
        for record in productions:
            if record.expected_kg and record.quantity_kg:
                yield_scores.append(record.quantity_kg / record.expected_kg)
        yield_performance = _ratio(sum(yield_scores), len(yield_scores) if yield_scores else 1)
        if not harvested:
            yield_performance = max(yield_performance * 0.7, 0.35)
    else:
        yield_performance = 0.55

    attendance_rows = (
        db.query(CooperativeAttendance)
        .filter(CooperativeAttendance.farmer_id == farmer.id)
        .all()
    )
    attendance_rate = _ratio(
        sum(1 for row in attendance_rows if row.attended),
        len(attendance_rows) if attendance_rows else 1,
    )

    loans = db.query(Loan).filter(Loan.farmer_id == farmer.id).all()
    prior_loans_repaid = sum(1 for loan in loans if loan.status == LoanStatus.repaid)
    disbursed_total = sum(loan.amount for loan in loans if loan.status == LoanStatus.disbursed)
    completed_total = sum(tx.amount for tx in completed_dues)
    outstanding_balance_ratio = _ratio(disbursed_total, disbursed_total + completed_total + 500)

    tenure_months = 12
    if farmer.created_at:
        tenure_months = max(
            1,
            int((datetime.utcnow() - farmer.created_at).days / 30),
        )

    savings_rate = _ratio(
        sum(tx.amount for tx in completed_dues),
        max(sum(tx.amount for tx in dues), 120.0),
        default=0.45,
    )

    return {
        "dues_payment_rate": round(dues_payment_rate, 3),
        "on_time_payment_rate": round(on_time_payment_rate, 3),
        "yield_performance": round(yield_performance, 3),
        "attendance_rate": round(attendance_rate, 3),
        "acreage": float(farmer.acreage or 2.5),
        "cooperative_tenure_months": tenure_months,
        "prior_loans_repaid": float(prior_loans_repaid),
        "outstanding_balance_ratio": round(outstanding_balance_ratio, 3),
        "savings_rate": round(savings_rate, 3),
    }
