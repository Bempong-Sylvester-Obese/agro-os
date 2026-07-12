"""Remove Golden Path demo cooperative data from a database."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.database.demo_constants import DEMO_COOPERATIVE_NAME
from app.models.models import (
    Cooperative,
    CooperativeAttendance,
    Farmer,
    Loan,
    PaymentWebhookEvent,
    Production,
    Transaction,
    TrustScore,
)

logger = logging.getLogger(__name__)


def purge_demo_cooperative(db: Session, *, dry_run: bool = False) -> dict:
    """
    Delete the Kuapa Kokoo demo cooperative and all member-linked records.
    Real cooperatives (e.g. Tamale Food) are untouched.
    """
    coop = db.query(Cooperative).filter(Cooperative.name == DEMO_COOPERATIVE_NAME).first()
    if not coop:
        return {"deleted": False, "reason": "demo cooperative not found"}

    farmers = db.query(Farmer).filter(Farmer.cooperative_id == coop.id).all()
    farmer_ids = [f.id for f in farmers]

    tx_ids: list[int] = []
    if farmer_ids:
        tx_ids = [
            row.id
            for row in db.query(Transaction.id).filter(Transaction.farmer_id.in_(farmer_ids)).all()
        ]

    coop_id = coop.id
    coop_name = coop.name
    counts = {
        "cooperative_id": coop_id,
        "cooperative_name": coop_name,
        "farmers": len(farmer_ids),
        "transactions": len(tx_ids),
        "loans": db.query(Loan).filter(Loan.farmer_id.in_(farmer_ids)).count() if farmer_ids else 0,
        "productions": db.query(Production).filter(Production.farmer_id.in_(farmer_ids)).count()
        if farmer_ids
        else 0,
        "trust_scores": db.query(TrustScore).filter(TrustScore.farmer_id.in_(farmer_ids)).count()
        if farmer_ids
        else 0,
        "attendances": db.query(CooperativeAttendance)
        .filter(CooperativeAttendance.farmer_id.in_(farmer_ids))
        .count()
        if farmer_ids
        else 0,
        "webhook_events": db.query(PaymentWebhookEvent)
        .filter(PaymentWebhookEvent.transaction_id.in_(tx_ids))
        .count()
        if tx_ids
        else 0,
    }

    if dry_run:
        return {"deleted": False, "dry_run": True, **counts}

    if tx_ids:
        db.query(PaymentWebhookEvent).filter(PaymentWebhookEvent.transaction_id.in_(tx_ids)).delete(
            synchronize_session=False
        )
    if farmer_ids:
        db.query(TrustScore).filter(TrustScore.farmer_id.in_(farmer_ids)).delete(synchronize_session=False)
        db.query(CooperativeAttendance).filter(CooperativeAttendance.farmer_id.in_(farmer_ids)).delete(
            synchronize_session=False
        )
        db.query(Transaction).filter(Transaction.farmer_id.in_(farmer_ids)).delete(synchronize_session=False)
        db.query(Loan).filter(Loan.farmer_id.in_(farmer_ids)).delete(synchronize_session=False)
        db.query(Production).filter(Production.farmer_id.in_(farmer_ids)).delete(synchronize_session=False)
        db.query(Farmer).filter(Farmer.cooperative_id == coop.id).delete(synchronize_session=False)

    db.delete(coop)
    db.commit()

    logger.info("Purged demo cooperative %s (%s)", coop_name, coop_id)
    return {"deleted": True, **counts}
