"""Bridge operational DB farmer records into Agro-AI assessments."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agro_ai.farmer_features import extract_features_from_farmer
from app.agro_ai.model import AgroAiCreditModel
from app.agro_ai.synthetic_data import DEMO_FARMERS
from app.models.models import (
    CooperativeMembership as Farmer,
)
from app.models.models import (
    Transaction,
    TransactionStatus,
    TransactionType,
)


def format_member_code(farmer_id: int) -> str:
    return f"GH-{farmer_id:04d}"


def _dues_status(farmer: Farmer, db: Session) -> str:
    pending = (
        db.query(Transaction)
        .filter(
            Transaction.farmer_id == farmer.id,
            Transaction.transaction_type == TransactionType.dues,
            Transaction.status == TransactionStatus.pending,
        )
        .count()
    )
    if pending:
        return "Pending"
    return "Paid"


def _production_label(farmer: Farmer) -> str:
    """Return a unified production label through the legacy `crop` field."""
    raw_focus = getattr(farmer, "production_focus", "")
    focus = str(getattr(raw_focus, "value", raw_focus) or "").lower()
    crop = farmer.crop_type
    animal = getattr(farmer, "animal_type", None)
    if focus == "animal":
        return animal or "Animal production"
    if focus == "mixed":
        products = [value for value in (crop, animal) if value]
        return " + ".join(products) or "Mixed production"
    return crop or animal or "Mixed production"


def farmer_to_assessment_input(farmer: Farmer, db: Session) -> dict[str, Any]:
    features = extract_features_from_farmer(farmer, db)
    return {
        "farmer_id": format_member_code(farmer.id),
        "db_id": farmer.id,
        "name": farmer.name,
        "phone": farmer.phone,
        "region": farmer.location or "Ghana",
        # `crop` is retained because the v1 assessment response contract is
        # consumed by the current dashboard; its value now describes any focus.
        "crop": _production_label(farmer),
        "dues_status": _dues_status(farmer, db),
        "requested_credit_amount": 3500,
        "previous_score": int(round(farmer.trust_score or 0)),
        "features": features,
    }


def list_assessments_from_db(
    db: Session,
    model: AgroAiCreditModel,
    *,
    cooperative_id: int,
) -> list[dict[str, Any]]:
    farmers = (
        db.query(Farmer)
        .filter(Farmer.cooperative_id == cooperative_id)
        .order_by(Farmer.id)
        .all()
    )
    return [model.assess_farmer(farmer_to_assessment_input(farmer, db)) for farmer in farmers]


def get_assessment_from_db(
    farmer_id: str,
    db: Session,
    model: AgroAiCreditModel,
    *,
    cooperative_id: int,
    allow_demo: bool = False,
) -> dict[str, Any] | None:
    if farmer_id.startswith("GH-"):
        try:
            db_id = int(farmer_id.replace("GH-", ""))
        except ValueError:
            db_id = None
    else:
        db_id = int(farmer_id) if farmer_id.isdigit() else None

    farmer = None
    if db_id is not None:
        farmer = (
            db.query(Farmer)
            .filter(
                Farmer.id == db_id,
                Farmer.cooperative_id == cooperative_id,
            )
            .first()
        )

    if farmer:
        return model.assess_farmer(farmer_to_assessment_input(farmer, db))

    if allow_demo:
        for demo_farmer in DEMO_FARMERS:
            if demo_farmer["farmer_id"] == farmer_id:
                return model.assess_farmer(demo_farmer)
    return None
