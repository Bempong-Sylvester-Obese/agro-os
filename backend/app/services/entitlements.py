"""Plan entitlements: member / worker caps, SMS quotas, feature flags (#233).

Every check in this module works from the *effective* plan of a cooperative
(see ``subscription_lifecycle.effective_plan_key``), so a lapsed subscription
is enforced at the free tier even if a paid plan is still on record.

Limits are band-aware: when the plan has size bands (Solo ``w20``/``w50``/
``w100``, Growth ``base``/``plus_50``/``plus_100``) the band capacity wins over
the plan-level ceiling. A band with ``capacity: None`` (custom) is unlimited.

Failures raise ``HTTPException(403)`` with a structured ``detail`` object so
the dashboard can render an upgrade prompt:

    {"code": "plan_limit_reached", "limit_key": "max_members", "limit": 10,
     "used": 10, "plan": "starter", "message": "Member limit of 10 reached ..."}
"""

from __future__ import annotations

from datetime import datetime

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import Cooperative, CooperativeMembership, MembershipStatus, User
from app.models.worker import Worker, WorkerStatus
from app.services import subscription_lifecycle as lifecycle
from app.services.auth_service import get_current_user
from app.services.plans import get_band, get_plan, get_plan_limit, has_feature

UNLIMITED = 0  # plans.py convention: 0 means "no cap"

LIMIT_LABELS = {
    "max_members": "Member",
    "max_workers": "Worker",
}

# A limit of 0 only means "unlimited" when the plan actually includes the
# capability; a Starter cooperative has max_workers=0 because it has no
# worker module at all.
LIMIT_FEATURE = {
    "max_members": "members",
    "max_workers": "workers",
}

# Which limit a plan's size bands describe: cooperative bands size members
# ("Up to 50 members"), farmer-track bands size workers ("Up to 20 workers").
BAND_LIMIT_BY_TRACK = {
    "cooperative": "max_members",
    "farmer": "max_workers",
}

# Feature keys the dashboard cares about, with a short label.
FEATURE_LABELS = {
    "members": "Member register",
    "payments": "MoMo payments",
    "dashboard": "Dashboard",
    "loans": "AgroCredit loans",
    "scores": "Trust scores",
    "commerce": "Commerce (intake, aggregation, sales)",
    "ussd": "Member USSD",
    "sms": "Bulk SMS",
    "workers": "Worker management",
    "tasks": "Task management",
    "attendance": "Attendance",
    "payroll": "Wage payroll",
    "farm_production": "Farm production",
    "ussd_worker": "Worker USSD",
}

CODE_LIMIT = "plan_limit_reached"
CODE_QUOTA = "sms_quota_exceeded"
CODE_FEATURE = "feature_not_in_plan"


class EntitlementError(HTTPException):
    """403 with a machine-readable detail payload."""

    def __init__(self, *, code: str, message: str, plan: str, **extra):
        super().__init__(
            status_code=403,
            detail={"code": code, "message": message, "plan": plan, **extra},
        )


# ---------------------------------------------------------------------------
# Plan resolution
# ---------------------------------------------------------------------------


def effective_plan(db: Session, cooperative: Cooperative) -> str:
    """Apply pending lifecycle transitions and return the plan to enforce."""
    lifecycle.reconcile_and_commit(db, cooperative)
    return lifecycle.effective_plan_key(cooperative)


def _band_for(cooperative: Cooperative, plan_key: str) -> dict | None:
    """The band that applies to ``plan_key`` for this cooperative, if any.

    The recorded band only counts when it belongs to the effective plan (a
    Growth ``plus_50`` band means nothing once the account has fallen to the
    free tier, and a trial uses the plan's default band).
    """
    plan = get_plan(plan_key)
    if not plan or not plan.get("bands"):
        return None
    recorded = cooperative.subscription_band if cooperative.subscription_plan == plan_key else None
    return get_band(plan_key, recorded) or get_band(plan_key)


def capability_included(plan_key: str, limit_key: str) -> bool:
    """Whether the plan includes the module the limit applies to."""
    feature = LIMIT_FEATURE.get(limit_key)
    return True if feature is None else has_feature(plan_key, feature)


def limit_for(cooperative: Cooperative, limit_key: str, plan_key: str | None = None) -> int:
    """Band-aware limit. ``0`` means unlimited *when the capability is included*
    (see :func:`capability_included`); otherwise nothing may be created."""
    plan_key = plan_key or lifecycle.effective_plan_key(cooperative)
    plan = get_plan(plan_key) or {}
    band = _band_for(cooperative, plan_key)
    if band is not None and BAND_LIMIT_BY_TRACK.get(plan.get("track")) == limit_key:
        capacity = band.get("capacity")
        return UNLIMITED if capacity is None else int(capacity)
    return get_plan_limit(plan_key, limit_key)


# ---------------------------------------------------------------------------
# Usage counters
# ---------------------------------------------------------------------------


def count_active_members(db: Session, cooperative_id: int) -> int:
    return (
        db.query(CooperativeMembership)
        .filter(
            CooperativeMembership.cooperative_id == cooperative_id,
            CooperativeMembership.membership_status == MembershipStatus.active,
        )
        .count()
    )


def count_workers(db: Session, cooperative_id: int) -> int:
    return (
        db.query(Worker)
        .filter(Worker.cooperative_id == cooperative_id, Worker.status == WorkerStatus.active)
        .count()
    )


def reset_sms_window_if_needed(cooperative: Cooperative, now: datetime | None = None) -> None:
    """Zero the monthly SMS counter when the calendar month has rolled over."""
    now = now or datetime.utcnow()
    marker = cooperative.sms_month_reset
    if not marker or (marker.year, marker.month) != (now.year, now.month):
        cooperative.sms_sent_this_month = 0
        cooperative.sms_month_reset = now


# ---------------------------------------------------------------------------
# Assertions used by route handlers
# ---------------------------------------------------------------------------


def assert_within_limit(
    db: Session,
    cooperative: Cooperative,
    limit_key: str,
    current_count: int | None = None,
    *,
    adding: int = 1,
) -> int:
    """Block when ``current_count + adding`` would exceed the plan cap.

    Returns the applicable limit (``0`` = unlimited). ``current_count`` is
    computed from the database when omitted.
    """
    plan_key = effective_plan(db, cooperative)
    limit = limit_for(cooperative, limit_key, plan_key)
    if current_count is None:
        if limit_key == "max_members":
            current_count = count_active_members(db, cooperative.id)
        elif limit_key == "max_workers":
            current_count = count_workers(db, cooperative.id)
        else:
            current_count = 0
    included = capability_included(plan_key, limit_key)
    if not included or (limit != UNLIMITED and current_count + adding > limit):
        label = LIMIT_LABELS.get(limit_key, "Plan")
        if not included:
            raise EntitlementError(
                code=CODE_FEATURE,
                plan=plan_key,
                feature=LIMIT_FEATURE.get(limit_key),
                limit_key=limit_key,
                limit=0,
                used=current_count,
                message=(
                    f"{FEATURE_LABELS.get(LIMIT_FEATURE.get(limit_key), label)} is not included "
                    f"in the {plan_key} plan. Upgrade to enable it."
                ),
            )
        raise EntitlementError(
            code=CODE_LIMIT,
            plan=plan_key,
            limit_key=limit_key,
            limit=limit,
            used=current_count,
            message=(
                f"{label} limit of {limit} reached for the {plan_key} plan. "
                "Upgrade to add more."
            ),
        )
    return limit


def assert_sms_quota(db: Session, cooperative: Cooperative, recipients: int) -> int:
    """Block when sending ``recipients`` messages would exceed this month's quota.

    Returns the projected total so the caller can persist it after a
    successful send. Resets the window first when the month has rolled over.
    """
    reset_sms_window_if_needed(cooperative)
    plan_key = effective_plan(db, cooperative)
    limit = get_plan_limit(plan_key, "sms_per_month")
    used = cooperative.sms_sent_this_month or 0
    new_total = used + recipients
    if limit != UNLIMITED and new_total > limit:
        raise EntitlementError(
            code=CODE_QUOTA,
            plan=plan_key,
            limit_key="sms_per_month",
            limit=limit,
            used=used,
            requested=recipients,
            message=(
                f"SMS quota of {limit} exceeded for this month. "
                "Upgrade your plan for more."
            ),
        )
    return new_total


def assert_feature(db: Session, cooperative: Cooperative, feature: str) -> str:
    """Block when the effective plan does not include ``feature``."""
    plan_key = effective_plan(db, cooperative)
    if not has_feature(plan_key, feature):
        raise EntitlementError(
            code=CODE_FEATURE,
            plan=plan_key,
            feature=feature,
            message=(
                f"{FEATURE_LABELS.get(feature, feature)} is not included in the "
                f"{plan_key} plan. Upgrade to enable it."
            ),
        )
    return plan_key


def require_feature(feature: str):
    """Dependency: the caller's cooperative must have ``feature`` in its plan.

    No-op when auth is disabled or the user has no cooperative (mirrors
    ``require_roles``), so unauthenticated local/dev flows keep working.
    """

    def _dependency(
        db: Session = Depends(get_db),
        current_user: User | None = Depends(get_current_user),
    ) -> Cooperative | None:
        if current_user is None or not current_user.cooperative_id:
            return None
        cooperative = db.query(Cooperative).filter(Cooperative.id == current_user.cooperative_id).first()
        if cooperative is None:
            return None
        assert_feature(db, cooperative, feature)
        return cooperative

    return _dependency


# ---------------------------------------------------------------------------
# Usage summary for the dashboard
# ---------------------------------------------------------------------------


def _meter(used: int, limit: int, *, included: bool = True) -> dict:
    if not included:
        return {"used": used, "limit": 0, "unlimited": False, "percent": None, "remaining": 0, "included": False}
    unlimited = limit == UNLIMITED
    pct = None if unlimited else round(min(used / limit, 1.0) * 100)
    return {
        "used": used,
        "limit": None if unlimited else limit,
        "unlimited": unlimited,
        "percent": pct,
        "remaining": None if unlimited else max(limit - used, 0),
        "included": True,
    }


def usage_summary(db: Session, cooperative: Cooperative) -> dict:
    """Usage vs limits for the effective plan, plus feature availability."""
    plan_key = effective_plan(db, cooperative)
    reset_sms_window_if_needed(cooperative)
    db.commit()
    state = lifecycle.describe(cooperative)
    band = _band_for(cooperative, plan_key)
    plan = get_plan(plan_key) or {}

    members = count_active_members(db, cooperative.id)
    workers = count_workers(db, cooperative.id)
    features = {key: has_feature(plan_key, key) for key in FEATURE_LABELS}

    return {
        "cooperative_id": cooperative.id,
        "plan_key": cooperative.subscription_plan,
        "effective_plan_key": plan_key,
        "effective_plan_name": plan.get("name"),
        "band": band["key"] if band else None,
        "band_label": band["label"] if band else None,
        "status": state.status,
        "paid_access": state.paid_access,
        "in_grace": state.in_grace,
        "days_remaining": state.days_remaining,
        "expires_at": state.expires_at.isoformat() if state.expires_at else None,
        "limits": {
            "members": _meter(
                members,
                limit_for(cooperative, "max_members", plan_key),
                included=capability_included(plan_key, "max_members"),
            ),
            "workers": _meter(
                workers,
                limit_for(cooperative, "max_workers", plan_key),
                included=capability_included(plan_key, "max_workers"),
            ),
            "sms": {
                **_meter(cooperative.sms_sent_this_month or 0, get_plan_limit(plan_key, "sms_per_month")),
                "period": "month",
                "window_started_at": (
                    cooperative.sms_month_reset.isoformat() if cooperative.sms_month_reset else None
                ),
            },
        },
        "features": features,
        "feature_labels": FEATURE_LABELS,
    }
