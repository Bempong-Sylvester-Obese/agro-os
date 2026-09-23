"""Plan entitlements (#233): band-aware caps, SMS quota, feature gates, usage endpoint."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.models import Cooperative, User
from app.services import entitlements, subscription_lifecycle as lifecycle
from app.services.auth_service import create_access_token, get_password_hash


def _coop(plan="starter", band=None, status="active", days_left=None, **kw) -> Cooperative:
    return Cooperative(
        name=kw.pop("name", "Entitlement Coop"),
        currency="GHS",
        subscription_plan=plan,
        subscription_band=band,
        subscription_status=status,
        subscription_expires_at=None if days_left is None else datetime.utcnow() + timedelta(days=days_left),
        **kw,
    )


def _member_payload(coop_id: int, i: int) -> dict:
    return {"name": f"Member {i}", "phone": f"+2332000{i:05d}", "cooperative_id": coop_id, "crop_type": "cocoa"}


# ---------------------------------------------------------------------------
# limit_for: band awareness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "plan, band, expected_members, expected_workers",
    [
        ("starter", None, 10, 0),
        ("growth", None, 50, 0),          # default band
        ("growth", "base", 50, 0),
        ("growth", "plus_50", 100, 0),
        ("growth", "plus_100", 200, 0),
        ("solo", None, 0, 20),            # default band
        ("solo", "w50", 0, 50),
        ("solo", "w100", 0, 100),
        ("solo", "custom", 0, 0),         # custom capacity = unlimited
        ("enterprise", None, 0, 0),       # unlimited
    ],
)
def test_limit_for_is_band_aware(plan, band, expected_members, expected_workers):
    coop = _coop(plan=plan, band=band, days_left=None if plan == "starter" else 10)
    assert entitlements.limit_for(coop, "max_members") == expected_members
    assert entitlements.limit_for(coop, "max_workers") == expected_workers


def test_recorded_band_is_ignored_once_plan_lapses():
    coop = _coop(plan="growth", band="plus_100", status="expired", days_left=-40)
    assert lifecycle.effective_plan_key(coop) == "starter"
    assert entitlements.limit_for(coop, "max_members") == 10


def test_trial_uses_default_growth_band():
    coop = _coop()
    lifecycle.start_trial(coop)
    assert entitlements.limit_for(coop, "max_members") == 50


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------


def test_assert_within_limit_blocks_at_cap(db):
    coop = _coop()
    db.add(coop)
    db.commit()
    assert entitlements.assert_within_limit(db, coop, "max_members", current_count=9) == 10
    with pytest.raises(HTTPException) as exc:
        entitlements.assert_within_limit(db, coop, "max_members", current_count=10)
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert detail["code"] == "plan_limit_reached"
    assert (detail["limit_key"], detail["limit"], detail["used"], detail["plan"]) == ("max_members", 10, 10, "starter")
    assert "Upgrade" in detail["message"]


def test_assert_within_limit_unlimited_never_blocks(db):
    coop = _coop(plan="enterprise", days_left=10)
    db.add(coop)
    db.commit()
    assert entitlements.assert_within_limit(db, coop, "max_members", current_count=10_000) == 0


def test_assert_within_limit_blocks_module_not_in_plan(db):
    coop = _coop()  # starter: no worker module, max_workers=0 is *not* unlimited
    db.add(coop)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        entitlements.assert_within_limit(db, coop, "max_workers", current_count=0)
    assert exc.value.detail["code"] == "feature_not_in_plan"
    assert exc.value.detail["feature"] == "workers"


def test_assert_sms_quota_counts_recipients_and_resets_monthly(db):
    coop = _coop()
    coop.sms_sent_this_month = 95
    coop.sms_month_reset = datetime.utcnow()
    db.add(coop)
    db.commit()

    assert entitlements.assert_sms_quota(db, coop, 5) == 100
    with pytest.raises(HTTPException) as exc:
        entitlements.assert_sms_quota(db, coop, 6)
    assert exc.value.detail["code"] == "sms_quota_exceeded"
    assert exc.value.detail["used"] == 95
    assert exc.value.detail["requested"] == 6

    # Previous month's window → counter resets before checking.
    coop.sms_month_reset = datetime.utcnow().replace(day=1) - timedelta(days=1)
    assert entitlements.assert_sms_quota(db, coop, 6) == 6
    assert coop.sms_sent_this_month == 0


def test_assert_feature(db):
    coop = _coop()
    db.add(coop)
    db.commit()
    assert entitlements.assert_feature(db, coop, "members") == "starter"
    with pytest.raises(HTTPException) as exc:
        entitlements.assert_feature(db, coop, "loans")
    assert exc.value.detail["code"] == "feature_not_in_plan"
    assert exc.value.detail["feature"] == "loans"

    lifecycle.start_trial(coop)
    assert entitlements.assert_feature(db, coop, "loans") == "growth"


# ---------------------------------------------------------------------------
# Route integration
# ---------------------------------------------------------------------------


def test_member_cap_enforced_with_structured_error(client, db, cooperative):
    coop_id = cooperative["id"]
    for i in range(10):
        assert client.post("/farmers/", json=_member_payload(coop_id, i)).status_code == 201
    blocked = client.post("/farmers/", json=_member_payload(coop_id, 99))
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "plan_limit_reached"
    assert blocked.json()["detail"]["limit"] == 10


def test_member_cap_follows_growth_band(client, db, cooperative, growth_plan):
    growth_plan.subscription_band = "base"  # 50
    db.commit()
    coop_id = cooperative["id"]
    for i in range(12):  # past the starter cap of 10
        assert client.post("/farmers/", json=_member_payload(coop_id, i)).status_code == 201, i
    usage = client.get(f"/cooperatives/{coop_id}/usage").json()
    assert usage["limits"]["members"] == {
        "used": 12, "limit": 50, "unlimited": False, "percent": 24, "remaining": 38, "included": True,
    }


@patch(
    "app.services.providers.moolre_adapter.MoolreSmsAdapter.send_bulk_sms",
    new_callable=AsyncMock,
    return_value={"success": True, "message": "SMS queued", "raw": {}},
)
def test_sms_broadcast_respects_quota(mock_send, client, db, cooperative, farmer):
    coop = db.get(Cooperative, cooperative["id"])
    coop.sms_sent_this_month = 100
    coop.sms_month_reset = datetime.utcnow()
    db.commit()

    blocked = client.post(
        "/communications/sms/broadcast",
        json={"cooperative_id": coop.id, "message": "Hello"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "sms_quota_exceeded"
    mock_send.assert_not_awaited()

    coop.sms_sent_this_month = 99
    db.commit()
    ok = client.post("/communications/sms/broadcast", json={"cooperative_id": coop.id, "message": "Hello"})
    assert ok.status_code == 200, ok.text
    db.refresh(coop)
    assert coop.sms_sent_this_month == 100


def test_ussd_loan_request_blocked_on_starter(client, farmer):
    from app.services.loan_request_service import LOANS_NOT_IN_PLAN_MSG

    resp = client.post(
        "/ussdk/loan-request",
        json={
            "input": {},
            "props": {
                "session": {"msisdn": farmer["phone"], "network": "mtn"},
                "values": {"amount": "100", "purpose": "Inputs"},
            },
        },
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "end"
    assert resp.json()["message"] == LOANS_NOT_IN_PLAN_MSG


def test_usage_endpoint_shape(client, db, cooperative, farmer):
    coop = db.get(Cooperative, cooperative["id"])
    coop.sms_sent_this_month = 40
    coop.sms_month_reset = datetime.utcnow()
    db.commit()

    resp = client.get(f"/cooperatives/{coop.id}/usage")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["effective_plan_key"] == "starter"
    assert body["effective_plan_name"] == "Starter"
    assert body["status"] == "active"
    assert body["limits"]["members"]["used"] == 1
    assert body["limits"]["members"]["limit"] == 10
    assert body["limits"]["sms"]["used"] == 40
    assert body["limits"]["sms"]["limit"] == 100
    assert body["limits"]["sms"]["percent"] == 40
    assert body["limits"]["workers"] == {
        "used": 0, "limit": 0, "unlimited": False, "percent": None, "remaining": 0, "included": False,
    }
    assert body["features"]["members"] is True
    assert body["features"]["loans"] is False
    assert body["features"]["scores"] is False
    assert body["feature_labels"]["loans"] == "AgroCredit loans"


def test_usage_endpoint_for_trial_shows_growth_entitlements(client, db):
    signup = client.post(
        "/auth/signup",
        json={"email": "usage-trial@example.com", "password": "strong-password", "cooperative_name": "Usage Trial"},
    )
    assert signup.status_code == 201
    coop = db.query(Cooperative).filter(Cooperative.name == "Usage Trial").one()
    body = client.get(f"/cooperatives/{coop.id}/usage").json()
    assert body["plan_key"] == "starter"
    assert body["effective_plan_key"] == "growth"
    assert body["status"] == "trial"
    assert body["band"] == "base"
    assert body["limits"]["members"]["limit"] == 50
    assert body["features"]["loans"] is True
    assert body["days_remaining"] in (lifecycle.TRIAL_DAYS - 1, lifecycle.TRIAL_DAYS)


def test_feature_gate_on_loans_and_scores_with_auth(client, db, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "strong-entitlements-test-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-entitlements-password")
    get_settings.cache_clear()
    try:
        coop = _coop(name="Gate Coop")
        db.add(coop)
        db.flush()
        user = User(email="gate@example.com", hashed_password=get_password_hash("x" * 12), role="admin",
                    cooperative_id=coop.id)
        db.add(user)
        db.commit()
        headers = {"Authorization": f"Bearer {create_access_token({'sub': user.email})}"}

        loans = client.get("/loans/", headers=headers)
        assert loans.status_code == 403
        assert loans.json()["detail"]["code"] == "feature_not_in_plan"
        assert loans.json()["detail"]["feature"] == "loans"

        scores = client.get("/api/farmers", headers=headers)
        assert scores.status_code == 403
        assert scores.json()["detail"]["feature"] == "scores"

        # Growth plan unlocks both.
        lifecycle.renew(coop, "growth", "base")
        db.commit()
        assert client.get("/loans/", headers=headers).status_code == 200
        assert client.get("/api/farmers", headers=headers).status_code == 200

        # Lapsed Growth plan falls back to Starter and is gated again.
        coop.subscription_expires_at = datetime.utcnow() - timedelta(days=lifecycle.GRACE_DAYS + 1)
        db.commit()
        assert client.get("/loans/", headers=headers).status_code == 403
    finally:
        monkeypatch.setenv("AUTH_ENABLED", "false")
        get_settings.cache_clear()
