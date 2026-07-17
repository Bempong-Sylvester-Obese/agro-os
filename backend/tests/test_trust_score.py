"""Unit tests for TrustScoreService sub-score formulas"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.models.models import (
    Cooperative,
    CooperativeAttendance,
    CooperativeMembership,
    Farmer,
    Loan,
    LoanStatus,
    Production,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.services.trust_score_service import TrustScoreService

# Dedicated in-memory DB for unit tests
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture()
def session():
    conn = engine.connect()
    tx = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    tx.rollback()
    conn.close()


@pytest.fixture()
def seeded(session):
    """Seed a cooperative + farmer for each test."""
    coop = Cooperative(name="Test Co-op", currency="GHS")
    session.add(coop)
    session.flush()

    profile = Farmer(name="Test Farmer", phone="+233999000001")
    session.add(profile)
    session.flush()
    membership = CooperativeMembership(
        farmer_id=profile.id,
        cooperative_id=coop.id,
    )
    session.add(membership)
    session.flush()
    return membership


# ---------------------------------------------------------------------------
# Payment compliance
# ---------------------------------------------------------------------------


def test_payment_compliance_no_dues_returns_50(session, seeded):
    score = TrustScoreService._payment_compliance(seeded.id, session)
    assert score == 50.0


def test_payment_compliance_all_completed(session, seeded):
    for _ in range(4):
        t = Transaction(
            farmer_id=seeded.id,
            transaction_type=TransactionType.dues,
            amount=50,
            status=TransactionStatus.completed,
        )
        session.add(t)
    session.flush()
    score = TrustScoreService._payment_compliance(seeded.id, session)
    assert score == 100.0


def test_payment_compliance_half_completed(session, seeded):
    for i in range(4):
        t = Transaction(
            farmer_id=seeded.id,
            transaction_type=TransactionType.dues,
            amount=50,
            status=TransactionStatus.completed if i < 2 else TransactionStatus.failed,
        )
        session.add(t)
    session.flush()
    score = TrustScoreService._payment_compliance(seeded.id, session)
    assert score == 50.0


# ---------------------------------------------------------------------------
# Loan repayment
# ---------------------------------------------------------------------------


def test_loan_repayment_no_loans_returns_75(session, seeded):
    score = TrustScoreService._loan_repayment(seeded.id, session)
    assert score == 75.0


def test_loan_repayment_all_repaid(session, seeded):
    for _ in range(3):
        ln = Loan(farmer_id=seeded.id, amount=200, status=LoanStatus.repaid)
        session.add(ln)
    session.flush()
    score = TrustScoreService._loan_repayment(seeded.id, session)
    assert score == 100.0


def test_loan_repayment_none_repaid(session, seeded):
    for _ in range(2):
        ln = Loan(farmer_id=seeded.id, amount=200, status=LoanStatus.disbursed)
        session.add(ln)
    session.flush()
    score = TrustScoreService._loan_repayment(seeded.id, session)
    assert score == 0.0


# ---------------------------------------------------------------------------
# Production history
# ---------------------------------------------------------------------------


def test_production_no_records_returns_50(session, seeded):
    score = TrustScoreService._production_history(seeded.id, session)
    assert score == 50.0


def test_production_all_harvested(session, seeded):
    for _ in range(2):
        p = Production(
            farmer_id=seeded.id,
            crop_type="Cocoa",
            harvest_date=datetime.utcnow(),
            quantity_kg=300.0,
        )
        session.add(p)
    session.flush()
    score = TrustScoreService._production_history(seeded.id, session)
    assert score > 50.0  # Should get bonuses


def test_production_none_harvested(session, seeded):
    p = Production(farmer_id=seeded.id, crop_type="Cocoa")
    session.add(p)
    session.flush()
    score = TrustScoreService._production_history(seeded.id, session)
    assert score == 0.0  # No harvests, no bonus


def test_animal_production_uses_generic_completion_and_output(session, seeded):
    incomplete = Production(
        farmer_id=seeded.id,
        production_kind="animal",
        product_name="Eggs",
        unit="crates",
    )
    production = Production(
        farmer_id=seeded.id,
        production_kind="animal",
        product_name="Eggs",
        unit="crates",
        expected_quantity=40.0,
        quantity=38.0,
        production_date=datetime.utcnow(),
    )
    session.add_all([incomplete, production])
    session.flush()

    # 50% completion + 5 multi-record bonus + 5 output bonus.
    # Without generic quantity handling this stays at 55.0.
    assert TrustScoreService._production_history(seeded.id, session) == 60.0


def test_mixed_production_counts_generic_and_legacy_records(session, seeded):
    animal = Production(farmer_id=seeded.id, crop_type="Goats")
    animal.production_kind = "animal"
    animal.quantity = 8.0
    animal.production_date = datetime.utcnow()
    crop = Production(
        farmer_id=seeded.id,
        crop_type="Cassava",
        quantity_kg=500.0,
        harvest_date=datetime.utcnow(),
    )
    session.add_all([animal, crop])
    session.flush()

    assert TrustScoreService._production_history(seeded.id, session) == 100.0


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------


def test_attendance_no_records_returns_50(session, seeded):
    score = TrustScoreService._attendance(seeded.id, session)
    assert score == 50.0


def test_attendance_all_attended(session, seeded):
    for i in range(3):
        a = CooperativeAttendance(
            farmer_id=seeded.id,
            event_name=f"Meeting {i}",
            event_date=datetime.utcnow() - timedelta(days=i * 30),
            attended=True,
        )
        session.add(a)
    session.flush()
    score = TrustScoreService._attendance(seeded.id, session)
    assert score == 100.0


def test_attendance_none_attended(session, seeded):
    for i in range(2):
        a = CooperativeAttendance(
            farmer_id=seeded.id,
            event_name=f"Event {i}",
            event_date=datetime.utcnow() - timedelta(days=i * 10),
            attended=False,
        )
        session.add(a)
    session.flush()
    score = TrustScoreService._attendance(seeded.id, session)
    assert score == 0.0


# ---------------------------------------------------------------------------
# Full score calculation
# ---------------------------------------------------------------------------


def test_full_trust_score_in_range(session, seeded):
    # Add some data
    session.add(
        Transaction(
            farmer_id=seeded.id,
            transaction_type=TransactionType.dues,
            amount=50,
            status=TransactionStatus.completed,
        )
    )
    session.add(
        Production(
            farmer_id=seeded.id,
            crop_type="Cocoa",
            harvest_date=datetime.utcnow(),
            quantity_kg=500.0,
        )
    )
    session.flush()

    snapshot = TrustScoreService.calculate_trust_score(seeded.id, session)
    assert 0.0 <= snapshot.score <= 100.0
    assert snapshot.farmer_id == seeded.id
