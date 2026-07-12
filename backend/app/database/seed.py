"""Golden Path demo seed data for cooperatives, farmers, and transactions."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database.demo_constants import DEMO_COOPERATIVE_NAME
from app.models.models import (
    Cooperative,
    CooperativeAttendance,
    Farmer,
    Loan,
    LoanStatus,
    MembershipStatus,
    Production,
    Transaction,
    TransactionStatus,
    TransactionType,
)

logger = logging.getLogger(__name__)

COOP_NAME = DEMO_COOPERATIVE_NAME


def seed_golden_path(db: Session) -> dict:
    """Insert demo records when the database is empty."""
    from app.config import get_settings

    settings = get_settings()
    if settings.app_env.lower() in ("production", "prod"):
        logger.warning("Refusing to seed demo data in production")
        return {"seeded": False, "reason": "production environment"}
    if not settings.seed_demo_data:
        return {"seeded": False, "reason": "SEED_DEMO_DATA is not enabled"}

    existing = db.query(Cooperative).filter(Cooperative.name == COOP_NAME).first()
    if existing:
        logger.info("Golden Path seed already present — skipping")
        return {"seeded": False, "cooperative_id": existing.id}

    coop = Cooperative(
        name=COOP_NAME,
        description="Hackathon demo cooperative for the Golden Path pitch",
        location="Kumasi, Ashanti Region",
        currency="GHS",
        moolre_account_number="DEMO-WALLET-001",
    )
    db.add(coop)
    db.flush()

    farmers_data = [
        {
            "name": "Abena Mensah",
            "phone": "+233552341234",
            "location": "Ashanti",
            "crop_type": "Maize",
            "acreage": 4.1,
            "trust_score": 58.0,
        },
        {
            "name": "Kofi Darko",
            "phone": "+233207731234",
            "location": "Brong-Ahafo",
            "crop_type": "Cocoa",
            "acreage": 5.4,
            "trust_score": 88.0,
        },
        {
            "name": "Ama Serwaa",
            "phone": "+233244567890",
            "location": "Eastern",
            "crop_type": "Cassava",
            "acreage": 3.0,
            "trust_score": 71.0,
        },
        {
            "name": "Yaw Frimpong",
            "phone": "+233503621234",
            "location": "Volta",
            "crop_type": "Rice",
            "acreage": 3.2,
            "trust_score": 76.0,
        },
    ]

    farmers: list[Farmer] = []
    for row in farmers_data:
        farmer = Farmer(
            cooperative_id=coop.id,
            membership_status=MembershipStatus.active,
            **row,
        )
        db.add(farmer)
        farmers.append(farmer)
    db.flush()

    abena = farmers[0]
    kofi = farmers[1]

    pending_ref = str(uuid.uuid4())
    db.add(
        Transaction(
            farmer_id=abena.id,
            transaction_type=TransactionType.dues,
            amount=120.0,
            status=TransactionStatus.pending,
            moolre_reference=pending_ref,
            payer_phone=abena.phone,
            channel="13",
            description="June 2026 cooperative dues",
        )
    )

    for farmer, amount, days_ago in [
        (kofi, 120.0, 3),
        (farmers[2], 120.0, 8),
        (farmers[3], 120.0, 12),
    ]:
        db.add(
            Transaction(
                farmer_id=farmer.id,
                transaction_type=TransactionType.dues,
                amount=amount,
                status=TransactionStatus.completed,
                moolre_reference=str(uuid.uuid4()),
                payer_phone=farmer.phone,
                channel="13",
                description="Monthly cooperative dues",
                created_at=datetime.utcnow() - timedelta(days=days_ago),
            )
        )

    db.add(
        Loan(
            farmer_id=abena.id,
            amount=3500.0,
            purpose="Fertilizer input loan",
            status=LoanStatus.requested,
        )
    )

    db.add(
        Production(
            farmer_id=abena.id,
            crop_type="Maize",
            season="2026A",
            expected_kg=1800.0,
            quantity_kg=920.0,
            quality_grade="B",
        )
    )
    db.add(
        Production(
            farmer_id=kofi.id,
            crop_type="Cocoa",
            season="2026A",
            expected_kg=2400.0,
            quantity_kg=2100.0,
            quality_grade="A",
        )
    )

    for farmer in farmers:
        db.add(
            CooperativeAttendance(
                farmer_id=farmer.id,
                event_name="Monthly cooperative meeting",
                event_date=datetime.utcnow() - timedelta(days=14),
                attended=farmer.name != "Yaw Frimpong",
            )
        )

    db.commit()
    logger.info("Golden Path seed data inserted for cooperative %s", coop.id)
    return {
        "seeded": True,
        "cooperative_id": coop.id,
        "abena_farmer_id": abena.id,
        "pending_dues_reference": pending_ref,
    }
