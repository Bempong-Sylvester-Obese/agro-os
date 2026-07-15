"""Remove Golden Path demo cooperative data from a database."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.database.demo_constants import DEMO_COOPERATIVE_NAME
from app.models.models import (
    AgroAiPredictionLog,
    CommunicationLog,
    Cooperative,
    CooperativeAttendance,
    CooperativeMembership,
    Farmer,
    Loan,
    PaymentWebhookEvent,
    Production,
    Transaction,
    TrustScore,
    UssdSession,
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

    farmers = (
        db.query(CooperativeMembership)
        .filter(CooperativeMembership.cooperative_id == coop.id)
        .all()
    )
    farmer_ids = [f.id for f in farmers]
    profile_ids = [f.farmer_id for f in farmers]

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
        db.query(CooperativeMembership).filter(
            CooperativeMembership.cooperative_id == coop.id
        ).delete(synchronize_session=False)
        for profile_id in profile_ids:
            has_other_membership = (
                db.query(CooperativeMembership)
                .filter(CooperativeMembership.farmer_id == profile_id)
                .first()
            )
            if not has_other_membership:
                db.query(Farmer).filter(Farmer.id == profile_id).delete(
                    synchronize_session=False
                )

    db.delete(coop)
    db.commit()

    logger.info("Purged demo cooperative %s (%s)", coop_name, coop_id)
    return {"deleted": True, **counts}


def reset_demo_workspace(
    db: Session,
    *,
    dry_run: bool = False,
    commit: bool = True,
    cooperative_id: int | None = None,
) -> dict:
    """Clear demo operational data while preserving its cooperative and users."""
    query = db.query(Cooperative).filter(Cooperative.name == DEMO_COOPERATIVE_NAME)
    if cooperative_id is not None:
        query = query.filter(Cooperative.id == cooperative_id)
    coop = query.first()
    if not coop:
        return {"reset": False, "reason": "demo cooperative not found"}

    memberships = (
        db.query(CooperativeMembership)
        .filter(CooperativeMembership.cooperative_id == coop.id)
        .all()
    )
    membership_ids = [membership.id for membership in memberships]
    profile_ids = [membership.farmer_id for membership in memberships]
    tx_ids = (
        [
            row.id
            for row in db.query(Transaction.id)
            .filter(Transaction.farmer_id.in_(membership_ids))
            .all()
        ]
        if membership_ids
        else []
    )
    counts = {
        "cooperative_id": coop.id,
        "cooperative_name": coop.name,
        "memberships": len(membership_ids),
        "transactions": len(tx_ids),
        "loans": db.query(Loan).filter(Loan.farmer_id.in_(membership_ids)).count()
        if membership_ids
        else 0,
        "productions": db.query(Production).filter(Production.farmer_id.in_(membership_ids)).count()
        if membership_ids
        else 0,
        "trust_scores": db.query(TrustScore).filter(TrustScore.farmer_id.in_(membership_ids)).count()
        if membership_ids
        else 0,
        "attendances": db.query(CooperativeAttendance)
        .filter(CooperativeAttendance.farmer_id.in_(membership_ids))
        .count()
        if membership_ids
        else 0,
        "webhook_events": db.query(PaymentWebhookEvent)
        .filter(PaymentWebhookEvent.transaction_id.in_(tx_ids))
        .count()
        if tx_ids
        else 0,
        "communications": db.query(CommunicationLog)
        .filter(CommunicationLog.cooperative_id == coop.id)
        .count(),
        "ussd_sessions": db.query(UssdSession)
        .filter(UssdSession.farmer_id.in_(membership_ids))
        .count()
        if membership_ids
        else 0,
        "ai_predictions": db.query(AgroAiPredictionLog)
        .filter(AgroAiPredictionLog.cooperative_id == str(coop.id))
        .count(),
    }
    if dry_run:
        return {"reset": False, "dry_run": True, **counts}

    if tx_ids:
        db.query(PaymentWebhookEvent).filter(
            PaymentWebhookEvent.transaction_id.in_(tx_ids)
        ).delete(synchronize_session=False)
    db.query(CommunicationLog).filter(CommunicationLog.cooperative_id == coop.id).delete(
        synchronize_session=False
    )
    db.query(AgroAiPredictionLog).filter(
        AgroAiPredictionLog.cooperative_id == str(coop.id)
    ).delete(synchronize_session=False)
    if membership_ids:
        db.query(UssdSession).filter(UssdSession.farmer_id.in_(membership_ids)).delete(
            synchronize_session=False
        )
        db.query(TrustScore).filter(TrustScore.farmer_id.in_(membership_ids)).delete(
            synchronize_session=False
        )
        db.query(CooperativeAttendance).filter(
            CooperativeAttendance.farmer_id.in_(membership_ids)
        ).delete(synchronize_session=False)
        db.query(Transaction).filter(Transaction.farmer_id.in_(membership_ids)).delete(
            synchronize_session=False
        )
        db.query(Loan).filter(Loan.farmer_id.in_(membership_ids)).delete(
            synchronize_session=False
        )
        db.query(Production).filter(Production.farmer_id.in_(membership_ids)).delete(
            synchronize_session=False
        )
        db.query(CooperativeMembership).filter(
            CooperativeMembership.cooperative_id == coop.id
        ).delete(synchronize_session=False)
        for profile_id in profile_ids:
            has_other_membership = (
                db.query(CooperativeMembership)
                .filter(CooperativeMembership.farmer_id == profile_id)
                .first()
            )
            if not has_other_membership:
                db.query(Farmer).filter(Farmer.id == profile_id).delete(
                    synchronize_session=False
                )
    if commit:
        db.commit()
    else:
        db.flush()
    logger.info("Reset demo workspace %s (%s)", coop.name, coop.id)
    return {"reset": True, **counts}
