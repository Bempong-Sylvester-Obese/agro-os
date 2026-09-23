"""Subscription lifecycle — states, transitions, and the plan that entitlements use.

States (``Cooperative.subscription_status``)::

    trial ──(lapses)──► active on starter (free tier, no expiry)
    trial ──(payment)─► active on paid plan
    active (paid) ──(period ends)──► past_due ──(grace ends)──► expired
    active/past_due/expired ──(payment)──► active (renewal extends the period)
    active (paid) ──(cancel)──► cancelled (access until period end) ──► expired
    cancelled ──(resume before period end)──► active
    anything ──(downgrade)──► active on starter

Two plan notions matter:

* ``subscription_plan`` is what the customer *bought*. It is never changed by
  the passage of time except when a trial lapses or a cancellation completes.
* :func:`effective_plan_key` is what entitlements must use. It returns the
  Growth plan during a live trial, the paid plan while the period (plus grace)
  is running, and ``starter`` once access has lapsed.

Callers that gate anything on a plan must call :func:`reconcile` first (or use
:func:`require_active_subscription`) so time-based transitions are applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import Cooperative, User
from app.services.auth_service import get_current_user
from app.services.plans import get_plan, has_feature

FREE_PLAN = "starter"
TRIAL_PLAN = "growth"

TRIAL_DAYS = 14
PERIOD_DAYS = 30
GRACE_DAYS = 7

STATUS_TRIAL = "trial"
STATUS_ACTIVE = "active"
STATUS_PAST_DUE = "past_due"
STATUS_EXPIRED = "expired"
STATUS_CANCELLED = "cancelled"

VALID_STATUSES = frozenset(
    {STATUS_TRIAL, STATUS_ACTIVE, STATUS_PAST_DUE, STATUS_EXPIRED, STATUS_CANCELLED}
)

# Which statuses may move to which via an explicit action (not time).
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_TRIAL: frozenset({STATUS_ACTIVE}),
    STATUS_ACTIVE: frozenset({STATUS_ACTIVE, STATUS_CANCELLED}),
    STATUS_PAST_DUE: frozenset({STATUS_ACTIVE, STATUS_CANCELLED}),
    STATUS_EXPIRED: frozenset({STATUS_ACTIVE}),
    STATUS_CANCELLED: frozenset({STATUS_ACTIVE}),
}


class SubscriptionStateError(ValueError):
    """Raised when an explicit transition is not allowed from the current state."""


def _now() -> datetime:
    return datetime.utcnow()


def is_free_plan(plan_key: str | None) -> bool:
    plan = get_plan(plan_key or "")
    return plan is None or float(plan.get("price") or 0) <= 0


def _assert_transition(cooperative: Cooperative, target: str) -> None:
    current = cooperative.subscription_status or STATUS_ACTIVE
    if current not in VALID_STATUSES:
        raise SubscriptionStateError(f"unknown subscription status {current!r}")
    if target not in _ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise SubscriptionStateError(f"cannot move subscription from {current} to {target}")


# ---------------------------------------------------------------------------
# Time-based reconciliation
# ---------------------------------------------------------------------------


def reconcile(cooperative: Cooperative, now: datetime | None = None) -> str | None:
    """Apply any time-based transition that is due. Returns the new status or None.

    Idempotent: calling it repeatedly at the same instant changes nothing.
    """
    now = now or _now()
    status = cooperative.subscription_status or STATUS_ACTIVE
    expires = cooperative.subscription_expires_at

    if status == STATUS_TRIAL:
        if expires is None or now >= expires:
            _drop_to_free(cooperative)
            return STATUS_ACTIVE
        return None

    if status == STATUS_ACTIVE:
        if expires is not None and now >= expires and not is_free_plan(cooperative.subscription_plan):
            cooperative.subscription_status = STATUS_PAST_DUE
            return STATUS_PAST_DUE
        return None

    if status == STATUS_PAST_DUE:
        if expires is None or now >= expires + timedelta(days=GRACE_DAYS):
            cooperative.subscription_status = STATUS_EXPIRED
            return STATUS_EXPIRED
        return None

    if status == STATUS_CANCELLED:
        if expires is None or now >= expires:
            cooperative.subscription_status = STATUS_EXPIRED
            return STATUS_EXPIRED
        return None

    return None


def effective_plan_key(cooperative: Cooperative, now: datetime | None = None) -> str:
    """Plan whose limits and features apply right now (call :func:`reconcile` first)."""
    now = now or _now()
    status = cooperative.subscription_status or STATUS_ACTIVE
    plan = cooperative.subscription_plan or FREE_PLAN
    expires = cooperative.subscription_expires_at

    if status == STATUS_TRIAL:
        return TRIAL_PLAN if expires and now < expires else FREE_PLAN

    if is_free_plan(plan):
        return FREE_PLAN

    if status == STATUS_ACTIVE:
        if expires is None or now < expires:
            return plan
        # Period ended but reconcile has not run: treat as past_due grace.
        return plan if now < expires + timedelta(days=GRACE_DAYS) else FREE_PLAN

    if status == STATUS_PAST_DUE:
        return plan if expires and now < expires + timedelta(days=GRACE_DAYS) else FREE_PLAN

    if status == STATUS_CANCELLED:
        return plan if expires and now < expires else FREE_PLAN

    return FREE_PLAN


def has_paid_access(cooperative: Cooperative, now: datetime | None = None) -> bool:
    return effective_plan_key(cooperative, now) != FREE_PLAN


def days_remaining(cooperative: Cooperative, now: datetime | None = None) -> int | None:
    expires = cooperative.subscription_expires_at
    if expires is None:
        return None
    return max(0, (expires - (now or _now())).days)


# ---------------------------------------------------------------------------
# Explicit transitions
# ---------------------------------------------------------------------------


def start_trial(cooperative: Cooperative, days: int = TRIAL_DAYS, now: datetime | None = None) -> None:
    """Put a new free-tier cooperative on a time-boxed Growth trial."""
    now = now or _now()
    cooperative.subscription_plan = FREE_PLAN
    cooperative.subscription_band = None
    cooperative.subscription_status = STATUS_TRIAL
    cooperative.subscription_expires_at = now + timedelta(days=days)


def renew(
    cooperative: Cooperative,
    plan_key: str,
    band_key: str | None = None,
    days: int = PERIOD_DAYS,
    now: datetime | None = None,
) -> None:
    """Activate or extend a paid plan after a verified payment.

    Extends from the current expiry when the period is still running (early
    renewal, or a cancelled plan being resumed by paying), otherwise starts a
    fresh period from now. Late renewals therefore do not back-date access to
    the missed period.
    """
    now = now or _now()
    _assert_transition(cooperative, STATUS_ACTIVE)
    if is_free_plan(plan_key):
        raise SubscriptionStateError("renewal requires a paid plan")

    same_plan = cooperative.subscription_plan == plan_key
    expires = cooperative.subscription_expires_at
    period_running = (
        expires is not None
        and expires > now
        and cooperative.subscription_status in (STATUS_ACTIVE, STATUS_CANCELLED, STATUS_PAST_DUE)
        and same_plan
    )
    cooperative.subscription_expires_at = (
        expires + timedelta(days=days) if period_running else now + timedelta(days=days)
    )
    cooperative.subscription_plan = plan_key
    cooperative.subscription_band = band_key
    cooperative.subscription_status = STATUS_ACTIVE


def cancel(cooperative: Cooperative, *, immediately: bool = False, now: datetime | None = None) -> None:
    """Cancel a paid plan.

    Default: access continues until the current period ends, then the
    cooperative drops to the free tier (``cancelled`` → ``expired`` →
    entitlements on starter). ``immediately=True`` drops to starter now.
    Free-tier and trial cooperatives are always dropped immediately.
    """
    now = now or _now()
    if is_free_plan(cooperative.subscription_plan) or cooperative.subscription_status == STATUS_TRIAL:
        _drop_to_free(cooperative)
        return
    _assert_transition(cooperative, STATUS_CANCELLED)
    if immediately or not cooperative.subscription_expires_at or cooperative.subscription_expires_at <= now:
        _drop_to_free(cooperative)
        return
    cooperative.subscription_status = STATUS_CANCELLED


def resume(cooperative: Cooperative, now: datetime | None = None) -> None:
    """Undo a pending cancellation while the paid period is still running."""
    now = now or _now()
    if cooperative.subscription_status != STATUS_CANCELLED:
        raise SubscriptionStateError("only a cancelled subscription can be resumed")
    if not cooperative.subscription_expires_at or cooperative.subscription_expires_at <= now:
        raise SubscriptionStateError("the paid period has already ended; renew instead")
    cooperative.subscription_status = STATUS_ACTIVE


def downgrade_to_free(cooperative: Cooperative) -> None:
    """Immediate move to the free tier (admin-initiated downgrade)."""
    _drop_to_free(cooperative)


def _drop_to_free(cooperative: Cooperative) -> None:
    cooperative.subscription_plan = FREE_PLAN
    cooperative.subscription_band = None
    cooperative.subscription_status = STATUS_ACTIVE
    cooperative.subscription_expires_at = None


# ---------------------------------------------------------------------------
# Read model + FastAPI dependency
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubscriptionState:
    plan_key: str
    band: str | None
    status: str
    effective_plan_key: str
    expires_at: datetime | None
    days_remaining: int | None
    in_grace: bool
    paid_access: bool

    def as_dict(self) -> dict:
        return {
            "plan_key": self.plan_key,
            "band": self.band,
            "status": self.status,
            "effective_plan_key": self.effective_plan_key,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "days_remaining": self.days_remaining,
            "in_grace": self.in_grace,
            "paid_access": self.paid_access,
            "trial_days": TRIAL_DAYS,
            "grace_days": GRACE_DAYS,
        }


def describe(cooperative: Cooperative, now: datetime | None = None) -> SubscriptionState:
    now = now or _now()
    effective = effective_plan_key(cooperative, now)
    status = cooperative.subscription_status or STATUS_ACTIVE
    expires = cooperative.subscription_expires_at
    in_grace = status == STATUS_PAST_DUE and effective != FREE_PLAN
    return SubscriptionState(
        plan_key=cooperative.subscription_plan or FREE_PLAN,
        band=cooperative.subscription_band,
        status=status,
        effective_plan_key=effective,
        expires_at=expires,
        days_remaining=days_remaining(cooperative, now),
        in_grace=in_grace,
        paid_access=effective != FREE_PLAN,
    )


def reconcile_and_commit(db: Session, cooperative: Cooperative) -> None:
    if reconcile(cooperative) is not None:
        db.commit()


def require_active_subscription(feature: str | None = None):
    """Dependency factory: the caller's cooperative must have paid access.

    * Reconciles time-based transitions first.
    * With ``feature`` set, checks the *effective* plan includes it; otherwise
      requires any paid (non-starter) access.
    * Fails with HTTP 402 so clients can route to the billing page.
    * When auth is disabled (local dev/tests) or the user has no cooperative,
      the dependency is a no-op.
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
        reconcile_and_commit(db, cooperative)
        effective = effective_plan_key(cooperative)
        allowed = has_feature(effective, feature) if feature else effective != FREE_PLAN
        if not allowed:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "subscription_required",
                    "feature": feature,
                    "status": cooperative.subscription_status,
                    "effective_plan": effective,
                    "message": "This feature requires an active paid subscription.",
                },
            )
        return cooperative

    return _dependency
