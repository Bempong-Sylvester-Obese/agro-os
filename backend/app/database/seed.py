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
    CooperativeMembership,
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


def _model_values(model, values: dict) -> dict:
    """Keep the seed runnable while unified-model changes land independently."""
    return {key: value for key, value in values.items() if hasattr(model, key)}


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
            "production_focus": "mixed",
            "animal_type": "Goats",
            "animal_scale": 12,
        },
        {
            "name": "Yaw Frimpong",
            "phone": "+233503621234",
            "location": "Volta",
            "crop_type": "Rice",
            "acreage": 3.2,
            "trust_score": 76.0,
        },
        {
            "name": "Esi Nyarko",
            "phone": "+233272345678",
            "location": "Central",
            "crop_type": "Poultry",
            "acreage": None,
            "trust_score": 74.0,
            "production_focus": "animal",
            "animal_type": "Chickens",
            "animal_scale": 250,
        },
    ]

    farmers: list[CooperativeMembership] = []
    for row in farmers_data:
        profile = Farmer(
            name=row["name"],
            phone=row["phone"],
            location=row["location"],
        )
        db.add(profile)
        db.flush()
        membership = CooperativeMembership(
            **_model_values(
                CooperativeMembership,
                {
                    "farmer_id": profile.id,
                    "cooperative_id": coop.id,
                    "membership_status": MembershipStatus.active,
                    "crop_type": row["crop_type"],
                    "acreage": row["acreage"],
                    "trust_score": row["trust_score"],
                    "production_focus": row.get("production_focus", "crop"),
                    "animal_type": row.get("animal_type"),
                    "animal_scale": row.get("animal_scale"),
                },
            )
        )
        db.add(membership)
        farmers.append(membership)
    db.flush()

    abena = farmers[0]
    kofi = farmers[1]
    ama = farmers[2]
    esi = farmers[4]

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
            **_model_values(
                Production,
                {
                    "farmer_id": abena.id,
                    "production_kind": "crop",
                    "product_name": "Maize",
                    "activity": "harvest",
                    "unit": "kg",
                    "expected_quantity": 1800.0,
                    "quantity": 920.0,
                    "production_date": datetime.utcnow() - timedelta(days=20),
                    "crop_type": "Maize",
                    "season": "2026A",
                    "expected_kg": 1800.0,
                    "quantity_kg": 920.0,
                    "harvest_date": datetime.utcnow() - timedelta(days=20),
                    "quality_grade": "B",
                },
            )
        )
    )
    db.add(
        Production(
            **_model_values(
                Production,
                {
                    "farmer_id": kofi.id,
                    "production_kind": "crop",
                    "product_name": "Cocoa",
                    "activity": "harvest",
                    "unit": "kg",
                    "expected_quantity": 2400.0,
                    "quantity": 2100.0,
                    "production_date": datetime.utcnow() - timedelta(days=12),
                    "crop_type": "Cocoa",
                    "season": "2026A",
                    "expected_kg": 2400.0,
                    "quantity_kg": 2100.0,
                    "harvest_date": datetime.utcnow() - timedelta(days=12),
                    "quality_grade": "A",
                },
            )
        )
    )
    db.add(
        Production(
            **_model_values(
                Production,
                {
                    "farmer_id": ama.id,
                    "production_kind": "animal",
                    "product_name": "Goats",
                    "activity": "offspring",
                    "unit": "head",
                    "expected_quantity": 12.0,
                    "quantity": 10.0,
                    "production_date": datetime.utcnow() - timedelta(days=8),
                    "season": "2026A",
                },
            )
        )
    )
    db.add(
        Production(
            **_model_values(
                Production,
                {
                    "farmer_id": esi.id,
                    "production_kind": "animal",
                    "product_name": "Eggs",
                    "activity": "collection",
                    "unit": "crates",
                    "expected_quantity": 80.0,
                    "quantity": 76.0,
                    "production_date": datetime.utcnow() - timedelta(days=3),
                    "season": "2026A",
                },
            )
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
