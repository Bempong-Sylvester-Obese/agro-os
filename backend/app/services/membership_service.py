"""Shared cooperative-membership resolution for phone-based channels."""

from sqlalchemy.orm import Session, joinedload

from app.models.models import CooperativeMembership, Farmer, MembershipStatus
from app.utils.phone import normalize_ghana_phone


def memberships_for_phone(
    phone: str,
    db: Session,
    *,
    active_only: bool = True,
) -> list[CooperativeMembership]:
    normalized_phone = normalize_ghana_phone(phone)
    query = (
        db.query(CooperativeMembership)
        .join(Farmer, CooperativeMembership.farmer_id == Farmer.id)
        .options(
            joinedload(CooperativeMembership.farmer),
            joinedload(CooperativeMembership.cooperative),
        )
        .filter(Farmer.phone == normalized_phone)
    )
    if active_only:
        query = query.filter(
            CooperativeMembership.membership_status == MembershipStatus.active
        )
    return query.order_by(CooperativeMembership.id).all()


def resolve_phone_membership(
    phone: str,
    db: Session,
    *,
    membership_id: int | str | None = None,
) -> tuple[CooperativeMembership | None, list[CooperativeMembership]]:
    memberships = memberships_for_phone(phone, db)
    if not memberships:
        return None, []
    if membership_id not in (None, ""):
        try:
            selected_id = int(membership_id)
        except (TypeError, ValueError):
            return None, memberships
        selected = next(
            (membership for membership in memberships if membership.id == selected_id),
            None,
        )
        return selected, memberships
    if len(memberships) == 1:
        return memberships[0], memberships
    return None, memberships


def cooperative_selection_payload(
    memberships: list[CooperativeMembership],
) -> dict:
    return {
        "action": "select_cooperative",
        "requires_cooperative_selection": True,
        "message": "Choose a cooperative to continue.",
        "cooperatives": [
            {
                "membership_id": membership.id,
                "cooperative_id": membership.cooperative_id,
                "name": membership.cooperative.name,
            }
            for membership in memberships
        ],
    }
