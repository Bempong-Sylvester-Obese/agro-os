"""Subscription lifecycle (#234): trial, active, past_due, expired, cancelled, renewal."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import BackgroundTasks

from app.models.models import Cooperative, PendingCheckout
from app.routes.webhooks import _process_payment_payload
from app.services import subscription_lifecycle as lifecycle
from app.services.plans import get_plan_limit

NOW = datetime(2026, 9, 22, 12, 0, 0)
D = timedelta(days=1)


def _coop(**kwargs) -> Cooperative:
    defaults = dict(name="Lifecycle Coop", currency="GHS", subscription_plan="starter",
                    subscription_status="active", subscription_expires_at=None)
    defaults.update(kwargs)
    return Cooperative(**defaults)


def _paid(status="active", days_left=10, plan="growth", band="base") -> Cooperative:
    return _coop(subscription_plan=plan, subscription_band=band, subscription_status=status,
                 subscription_expires_at=NOW + days_left * D)


# ---------------------------------------------------------------------------
# States and time-based transitions
# ---------------------------------------------------------------------------


def test_free_tier_never_lapses():
    coop = _coop()
    assert lifecycle.reconcile(coop, NOW) is None
    assert lifecycle.effective_plan_key(coop, NOW) == "starter"
    assert lifecycle.reconcile(coop, NOW + 365 * D) is None


def test_trial_grants_growth_then_lapses_to_free_tier():
    coop = _coop()
    lifecycle.start_trial(coop, now=NOW)
    assert coop.subscription_status == "trial"
    assert coop.subscription_plan == "starter"  # nothing purchased yet
    assert lifecycle.effective_plan_key(coop, NOW) == "growth"
    assert get_plan_limit(lifecycle.effective_plan_key(coop, NOW), "max_members") > get_plan_limit("starter", "max_members")

    assert lifecycle.reconcile(coop, NOW + (lifecycle.TRIAL_DAYS - 1) * D) is None
    assert lifecycle.reconcile(coop, NOW + lifecycle.TRIAL_DAYS * D) == "active"
    assert coop.subscription_plan == "starter"
    assert coop.subscription_expires_at is None
    assert lifecycle.effective_plan_key(coop, NOW + lifecycle.TRIAL_DAYS * D) == "starter"


def test_active_paid_plan_moves_to_past_due_then_expired():
    coop = _paid(days_left=1)
    assert lifecycle.reconcile(coop, NOW) is None
    assert lifecycle.effective_plan_key(coop, NOW) == "growth"

    # Period ends → past_due, access retained during grace.
    t_end = NOW + 1 * D
    assert lifecycle.reconcile(coop, t_end) == "past_due"
    assert lifecycle.effective_plan_key(coop, t_end) == "growth"
    assert lifecycle.describe(coop, t_end).in_grace is True

    # Still in grace one day before it ends.
    t_grace = t_end + (lifecycle.GRACE_DAYS - 1) * D
    assert lifecycle.reconcile(coop, t_grace) is None
    assert lifecycle.effective_plan_key(coop, t_grace) == "growth"

    # Grace ends → expired, entitlements fall to the free tier.
    t_exp = t_end + lifecycle.GRACE_DAYS * D
    assert lifecycle.reconcile(coop, t_exp) == "expired"
    assert lifecycle.effective_plan_key(coop, t_exp) == "starter"
    assert coop.subscription_plan == "growth"  # record of what was bought is kept
    assert lifecycle.has_paid_access(coop, t_exp) is False


def test_reconcile_is_idempotent():
    coop = _paid(days_left=-1)
    assert lifecycle.reconcile(coop, NOW) == "past_due"
    assert lifecycle.reconcile(coop, NOW) is None
    assert lifecycle.reconcile(coop, NOW) is None


def test_effective_plan_is_safe_even_if_reconcile_was_skipped():
    coop = _paid(days_left=-(lifecycle.GRACE_DAYS + 1))  # status still says active
    assert lifecycle.effective_plan_key(coop, NOW) == "starter"


# ---------------------------------------------------------------------------
# Renewal
# ---------------------------------------------------------------------------


def test_renewal_before_expiry_extends_from_current_expiry():
    coop = _paid(days_left=10)
    lifecycle.renew(coop, "growth", "base", now=NOW)
    assert coop.subscription_expires_at == NOW + (10 + lifecycle.PERIOD_DAYS) * D
    assert coop.subscription_status == "active"


def test_renewal_after_lapse_starts_fresh_period_from_now():
    coop = _paid(status="expired", days_left=-40)
    lifecycle.renew(coop, "growth", "base", now=NOW)
    assert coop.subscription_expires_at == NOW + lifecycle.PERIOD_DAYS * D
    assert coop.subscription_status == "active"


def test_renewal_during_grace_starts_from_now_not_backdated():
    coop = _paid(status="past_due", days_left=-3)
    lifecycle.renew(coop, "growth", "base", now=NOW)
    assert coop.subscription_expires_at == NOW + lifecycle.PERIOD_DAYS * D


def test_upgrade_to_different_plan_starts_new_period():
    coop = _paid(days_left=10, plan="growth", band="base")
    lifecycle.renew(coop, "growth", "plus_50", now=NOW)  # band change on same plan extends
    assert coop.subscription_band == "plus_50"
    assert coop.subscription_expires_at == NOW + (10 + lifecycle.PERIOD_DAYS) * D

    solo = _paid(days_left=10, plan="growth", band="base")
    lifecycle.renew(solo, "solo", "w20", now=NOW)  # plan change → fresh period
    assert solo.subscription_plan == "solo"
    assert solo.subscription_expires_at == NOW + lifecycle.PERIOD_DAYS * D


def test_trial_converts_to_paid_on_payment():
    coop = _coop()
    lifecycle.start_trial(coop, now=NOW)
    lifecycle.renew(coop, "growth", "base", now=NOW + 3 * D)
    assert coop.subscription_status == "active"
    assert coop.subscription_plan == "growth"
    assert coop.subscription_expires_at == NOW + 3 * D + lifecycle.PERIOD_DAYS * D


def test_renewal_requires_paid_plan():
    coop = _paid()
    with pytest.raises(lifecycle.SubscriptionStateError):
        lifecycle.renew(coop, "starter", None, now=NOW)


# ---------------------------------------------------------------------------
# Cancel / resume / downgrade
# ---------------------------------------------------------------------------


def test_cancel_keeps_access_until_period_end_then_expires():
    coop = _paid(days_left=10)
    lifecycle.cancel(coop, now=NOW)
    assert coop.subscription_status == "cancelled"
    assert coop.subscription_plan == "growth"
    assert lifecycle.effective_plan_key(coop, NOW + 9 * D) == "growth"

    assert lifecycle.reconcile(coop, NOW + 10 * D) == "expired"
    assert lifecycle.effective_plan_key(coop, NOW + 10 * D) == "starter"


def test_cancel_immediately_drops_to_free_tier():
    coop = _paid(days_left=10)
    lifecycle.cancel(coop, immediately=True, now=NOW)
    assert coop.subscription_status == "active"
    assert coop.subscription_plan == "starter"
    assert coop.subscription_band is None
    assert coop.subscription_expires_at is None


def test_cancel_trial_drops_to_free_tier():
    coop = _coop()
    lifecycle.start_trial(coop, now=NOW)
    lifecycle.cancel(coop, now=NOW)
    assert (coop.subscription_status, coop.subscription_plan, coop.subscription_expires_at) == ("active", "starter", None)


def test_resume_before_period_end_restores_active():
    coop = _paid(days_left=10)
    lifecycle.cancel(coop, now=NOW)
    lifecycle.resume(coop, now=NOW + 2 * D)
    assert coop.subscription_status == "active"
    assert coop.subscription_expires_at == NOW + 10 * D


def test_resume_after_period_end_is_rejected():
    coop = _paid(days_left=1)
    lifecycle.cancel(coop, now=NOW)
    with pytest.raises(lifecycle.SubscriptionStateError):
        lifecycle.resume(coop, now=NOW + 2 * D)


def test_resume_requires_cancelled_state():
    with pytest.raises(lifecycle.SubscriptionStateError):
        lifecycle.resume(_paid(), now=NOW)


def test_downgrade_is_immediate():
    coop = _paid(days_left=10)
    lifecycle.downgrade_to_free(coop)
    assert (coop.subscription_plan, coop.subscription_status, coop.subscription_expires_at) == ("starter", "active", None)


# ---------------------------------------------------------------------------
# Integration: signup, webhook, limits, endpoints
# ---------------------------------------------------------------------------


def test_free_signup_starts_trial(client, db):
    resp = client.post(
        "/auth/signup",
        json={"email": "trial-owner@example.com", "password": "strong-password", "cooperative_name": "Trial Coop"},
    )
    assert resp.status_code == 201, resp.text
    coop = db.query(Cooperative).filter(Cooperative.name == "Trial Coop").one()
    assert coop.subscription_plan == "starter"
    assert coop.subscription_status == "trial"
    assert coop.subscription_expires_at is not None
    assert (coop.subscription_expires_at - datetime.utcnow()).days in (lifecycle.TRIAL_DAYS - 1, lifecycle.TRIAL_DAYS)
    assert lifecycle.effective_plan_key(coop) == "growth"


def test_expired_plan_is_enforced_at_free_tier_limits(client, db, cooperative):
    coop = db.get(Cooperative, cooperative["id"])
    coop.subscription_plan = "growth"
    coop.subscription_band = "base"
    coop.subscription_status = "active"
    coop.subscription_expires_at = datetime.utcnow() - timedelta(days=lifecycle.GRACE_DAYS + 1)
    db.commit()

    starter_limit = get_plan_limit("starter", "max_members")
    for i in range(starter_limit):
        r = client.post(
            "/farmers/",
            json={"name": f"Member {i}", "phone": f"+23300000{i:04d}", "cooperative_id": coop.id, "crop_type": "cocoa"},
        )
        assert r.status_code == 201, r.text

    blocked = client.post(
        "/farmers/",
        json={"name": "One too many", "phone": "+233009999999", "cooperative_id": coop.id, "crop_type": "cocoa"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "plan_limit_reached"
    assert blocked.json()["detail"]["plan"] == "starter"
    assert blocked.json()["detail"]["limit"] == starter_limit
    db.refresh(coop)
    assert coop.subscription_status == "expired"  # reconciled on the way through


def test_webhook_renewal_extends_current_period(client, db, cooperative):
    coop = db.get(Cooperative, cooperative["id"])
    coop.subscription_plan = "growth"
    coop.subscription_band = "base"
    coop.subscription_status = "active"
    original_expiry = datetime.utcnow() + timedelta(days=10)
    coop.subscription_expires_at = original_expiry
    db.commit()

    provider = AsyncMock()
    provider.generate_payment_link.return_value = {"success": True, "payment_url": "https://pay/x", "reference": "r"}
    with patch("app.routes.subscriptions.get_payment_provider", return_value=provider):
        renew = client.post("/subscriptions/renew", json={"cooperative_id": coop.id})
    assert renew.status_code == 200, renew.text
    assert renew.json()["plan_key"] == "growth"
    assert renew.json()["amount"] == 299.0

    _process_payment_payload(
        {"status": 1, "data": {"externalref": renew.json()["reference"], "amount": "299.00", "transactionid": "t"}},
        db, BackgroundTasks(), signature_valid=True,
    )
    db.refresh(coop)
    assert coop.subscription_status == "active"
    assert abs((coop.subscription_expires_at - (original_expiry + timedelta(days=lifecycle.PERIOD_DAYS))).total_seconds()) < 5
    intent = db.query(PendingCheckout).filter_by(reference=renew.json()["reference"]).one()
    assert intent.status == PendingCheckout.STATUS_CONSUMED


def test_renew_endpoint_rejects_free_tier(client, db, cooperative):
    resp = client.post("/subscriptions/renew", json={"cooperative_id": cooperative["id"]})
    assert resp.status_code == 400


def test_status_cancel_resume_endpoints(client, db, cooperative):
    coop = db.get(Cooperative, cooperative["id"])
    coop.subscription_plan = "growth"
    coop.subscription_band = "base"
    coop.subscription_status = "active"
    coop.subscription_expires_at = datetime.utcnow() + timedelta(days=12)
    db.commit()

    status = client.get(f"/subscriptions/status?cooperative_id={coop.id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "active" and body["effective_plan_key"] == "growth" and body["paid_access"] is True
    assert body["days_remaining"] in (11, 12)

    cancelled = client.post("/subscriptions/cancel", json={"cooperative_id": coop.id})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["paid_access"] is True  # until period end

    resumed = client.post("/subscriptions/resume", json={"cooperative_id": coop.id})
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "active"

    again = client.post("/subscriptions/resume", json={"cooperative_id": coop.id})
    assert again.status_code == 409

    now_cancel = client.post("/subscriptions/cancel", json={"cooperative_id": coop.id, "immediately": True})
    assert now_cancel.status_code == 200
    assert now_cancel.json()["effective_plan_key"] == "starter"
    assert now_cancel.json()["paid_access"] is False


def test_require_active_subscription_dependency(client, db, monkeypatch):
    """The dependency returns 402 for a lapsed plan and passes for a live one."""
    from fastapi import APIRouter, Depends

    from app.config import get_settings
    from app.models.models import User
    from app.services.auth_service import create_access_token, get_password_hash
    from main import app

    probe = APIRouter()

    @probe.get("/_probe/paid-only")
    def paid_only(_=Depends(lifecycle.require_active_subscription("commerce"))):
        return {"ok": True}

    app.include_router(probe)
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "strong-lifecycle-test-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-lifecycle-password")
    get_settings.cache_clear()
    try:
        coop = _coop(name="Probe Coop", subscription_plan="growth", subscription_band="base",
                     subscription_status="active",
                     subscription_expires_at=datetime.utcnow() - timedelta(days=lifecycle.GRACE_DAYS + 1))
        db.add(coop)
        db.flush()
        user = User(email="probe@example.com", hashed_password=get_password_hash("x" * 12), role="admin",
                    cooperative_id=coop.id)
        db.add(user)
        db.commit()
        headers = {"Authorization": f"Bearer {create_access_token({'sub': user.email})}"}

        denied = client.get("/_probe/paid-only", headers=headers)
        assert denied.status_code == 402
        assert denied.json()["detail"]["code"] == "subscription_required"

        coop.subscription_status = "active"
        coop.subscription_expires_at = datetime.utcnow() + timedelta(days=5)
        db.commit()
        allowed = client.get("/_probe/paid-only", headers=headers)
        assert allowed.status_code == 200
    finally:
        monkeypatch.setenv("AUTH_ENABLED", "false")
        get_settings.cache_clear()
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/_probe/paid-only"]
