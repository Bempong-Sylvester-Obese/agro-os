"""Extract Agro-AI feature vectors from operational farmer records."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import (
    CooperativeAttendance,
    Loan,
    LoanStatus,
    Production,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.models.models import (
    CooperativeMembership as Farmer,
)


def _ratio(numerator: float, denominator: float, default: float = 0.5) -> float:
    if denominator <= 0:
        return default
    return max(0.0, min(1.0, numerator / denominator))


def _production_amount(record: Production, generic_name: str, legacy_name: str):
    """Prefer unified production values while accepting legacy crop records."""
    generic = getattr(record, generic_name, None)
    return generic if generic is not None else getattr(record, legacy_name, None)


def _animal_scale_value(value) -> float | None:
    """Normalize numeric or labelled animal scale into the v1 acreage slot."""
    if value is None:
        return None
    try:
        count = float(value)
        if count <= 20:
            return 1.5
        if count <= 100:
            return 3.5
        return 6.0
    except (TypeError, ValueError):
        scales = {
            "small": 1.5,
            "small-scale": 1.5,
            "medium": 3.5,
            "medium-scale": 3.5,
            "large": 6.0,
            "large-scale": 6.0,
        }
        return scales.get(str(value).strip().lower())


def _v1_production_scale(farmer: Farmer) -> float:
    """Map unified crop/animal scale onto the artifact-compatible v1 feature."""
    acreage = float(farmer.acreage) if farmer.acreage is not None else None
    animal_scale = _animal_scale_value(getattr(farmer, "animal_scale", None))
    raw_focus = getattr(farmer, "production_focus", "")
    focus = str(getattr(raw_focus, "value", raw_focus) or "").lower()

    if focus == "animal" and animal_scale is not None:
        return animal_scale
    if focus == "mixed" and animal_scale is not None:
        return max(acreage or 0.0, animal_scale)
    return acreage or animal_scale or 2.5


def extract_features_from_farmer(farmer: Farmer, db: Session) -> dict[str, float]:
    """Build the exact v1 feature vector from unified operational records."""

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
        completed = [
            record
            for record in productions
            if getattr(record, "production_date", None) is not None
            or record.harvest_date is not None
        ]
        output_scores = []
        for record in productions:
            expected = _production_amount(record, "expected_quantity", "expected_kg")
            actual = _production_amount(record, "quantity", "quantity_kg")
            if expected and actual is not None:
                output_scores.append(actual / expected)
        if output_scores:
            yield_performance = _ratio(sum(output_scores), len(output_scores))
        else:
            yield_performance = 0.55
        if not completed:
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
        # Names and order are frozen for agro-ai-features-v1 artifacts.
        "acreage": _v1_production_scale(farmer),
        "cooperative_tenure_months": tenure_months,
        "prior_loans_repaid": float(prior_loans_repaid),
        "outstanding_balance_ratio": round(outstanding_balance_ratio, 3),
        "savings_rate": round(savings_rate, 3),
    }
