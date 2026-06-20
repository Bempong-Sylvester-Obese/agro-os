"""
Trust Score Calculation Service

Rules-based scoring formula (transparent / explainable for MVP).

Weights (sum = 1.0):
  Payment Compliance  0.40  – dues paid on time
  Production History  0.25  – harvest completion rate + volume
  Loan Repayment      0.20  – loans repaid vs. disbursed
  Attendance          0.15  – cooperative meetings / training attended

Score range: 0 – 100
"""

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
    TrustScore,
)


class TrustScoreService:
    """Calculate and persist farmer trust scores."""

    # ------------------------------------------------------------------ weights
    PAYMENT_COMPLIANCE_WEIGHT = 0.40
    PRODUCTION_HISTORY_WEIGHT = 0.25
    LOAN_REPAYMENT_WEIGHT = 0.20
    ATTENDANCE_WEIGHT = 0.15

    # ------------------------------------------------------------------ main

    @staticmethod
    def calculate_trust_score(farmer_id: int, db: Session) -> TrustScore:
        """Calculate, persist, and return a new TrustScore snapshot."""
        farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
        if not farmer:
            raise ValueError(f"Farmer {farmer_id} not found")

        payment_score = TrustScoreService._payment_compliance(farmer_id, db)
        production_score = TrustScoreService._production_history(farmer_id, db)
        loan_score = TrustScoreService._loan_repayment(farmer_id, db)
        attendance_score = TrustScoreService._attendance(farmer_id, db)

        total = (
            payment_score * TrustScoreService.PAYMENT_COMPLIANCE_WEIGHT
            + production_score * TrustScoreService.PRODUCTION_HISTORY_WEIGHT
            + loan_score * TrustScoreService.LOAN_REPAYMENT_WEIGHT
            + attendance_score * TrustScoreService.ATTENDANCE_WEIGHT
        )
        total = round(max(0.0, min(100.0, total)), 2)

        # Persist snapshot
        snapshot = TrustScore(
            farmer_id=farmer_id,
            score=total,
            payment_compliance=round(payment_score, 2),
            production_history=round(production_score, 2),
            loan_repayment=round(loan_score, 2),
            attendance=round(attendance_score, 2),
        )
        db.add(snapshot)

        # Update live score on farmer record
        farmer.trust_score = total
        db.commit()
        db.refresh(snapshot)

        return snapshot

    @staticmethod
    def get_score_history(farmer_id: int, db: Session, limit: int = 10) -> list[TrustScore]:
        """Return the last N trust score snapshots for trend charts."""
        return (
            db.query(TrustScore)
            .filter(TrustScore.farmer_id == farmer_id)
            .order_by(TrustScore.calculated_at.desc())
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------ sub-scores

    @staticmethod
    def _payment_compliance(farmer_id: int, db: Session) -> float:
        """
        Percentage of dues transactions that are completed (0–100).
        Default 50 if no dues history.
        """
        dues = (
            db.query(Transaction)
            .filter(
                Transaction.farmer_id == farmer_id,
                Transaction.transaction_type == TransactionType.dues,
            )
            .all()
        )
        if not dues:
            return 50.0
        completed = sum(1 for t in dues if t.status == TransactionStatus.completed)
        return (completed / len(dues)) * 100

    @staticmethod
    def _production_history(farmer_id: int, db: Session) -> float:
        """
        Based on harvest completion rate over the past 12 months.
        Bonus points for consistent volume and multiple cycles.
        Default 50 if no production data.
        """
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        productions = (
            db.query(Production)
            .filter(
                Production.farmer_id == farmer_id,
                Production.created_at >= one_year_ago,
            )
            .all()
        )
        if not productions:
            return 50.0

        completed = [p for p in productions if p.harvest_date is not None]
        base = (len(completed) / len(productions)) * 100

        # Bonus: multiple cycles show active farming
        if len(productions) >= 2:
            base = min(100.0, base + 5)
        if len(productions) >= 4:
            base = min(100.0, base + 5)

        # Bonus: actual kg reported
        with_kg = [p for p in completed if p.quantity_kg and p.quantity_kg > 0]
        if with_kg:
            base = min(100.0, base + 5)

        return base

    @staticmethod
    def _loan_repayment(farmer_id: int, db: Session) -> float:
        """
        Ratio of repaid loans to total disbursed loans.
        75 (low-risk default) if no loan history.
        """
        disbursed_loans = (
            db.query(Loan)
            .filter(
                Loan.farmer_id == farmer_id,
                Loan.status.in_([LoanStatus.disbursed, LoanStatus.repaid]),
            )
            .all()
        )
        if not disbursed_loans:
            return 75.0
        repaid = sum(1 for ln in disbursed_loans if ln.status == LoanStatus.repaid)
        return (repaid / len(disbursed_loans)) * 100

    @staticmethod
    def _attendance(farmer_id: int, db: Session) -> float:
        """
        Percentage of cooperative events attended over the past 12 months.
        Default 50 if no attendance records.
        """
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        records = (
            db.query(CooperativeAttendance)
            .filter(
                CooperativeAttendance.farmer_id == farmer_id,
                CooperativeAttendance.event_date >= one_year_ago,
            )
            .all()
        )
        if not records:
            return 50.0
        attended = sum(1 for r in records if r.attended)
        return (attended / len(records)) * 100
