"""Pricing catalog tests."""

from app.models.models import PendingCheckout
from app.plans import PLANS, get_plan, resolve_amount


def test_plans_catalog_has_two_tracks():
    tracks = {plan["track"] for plan in PLANS.values()}
    assert tracks == {"cooperative", "farmer"}


def test_get_plan_is_case_insensitive():
    assert get_plan("GROWTH")["key"] == "growth"
    assert get_plan("nope") is None


def test_resolve_amount_for_growth_bands():
    assert resolve_amount("growth", "base") == 299.0
    assert resolve_amount("growth", "plus_50") == 449.0
    assert resolve_amount("growth", "plus_100") == 599.0
    assert resolve_amount("growth", "not-a-band") is None


def test_resolve_amount_for_solo_bands():
    assert resolve_amount("solo", "w20") == 99.0
    assert resolve_amount("solo", "w50") == 199.0
    assert resolve_amount("solo", "w100") == 349.0
    assert resolve_amount("solo", "custom") is None


def test_resolve_amount_is_none_for_free_and_custom_plans():
    assert resolve_amount("starter") is None
    assert resolve_amount("enterprise") is None
    assert resolve_amount("unknown") is None


def test_plans_endpoint_returns_all_plans(client):
    resp = client.get("/plans")
    assert resp.status_code == 200
    keys = {p["key"] for p in resp.json()["plans"]}
    assert keys == {"starter", "growth", "solo", "enterprise"}


def test_pending_checkout_is_persisted(client, db):
    checkout = PendingCheckout(
        reference="sub_pre_test123",
        plan_key="growth",
        band="base",
        amount=299.0,
        organisation="Ashanti Farmers Cooperative",
        status="pending",
    )
    db.add(checkout)
    db.commit()

    saved = db.query(PendingCheckout).filter(PendingCheckout.reference == "sub_pre_test123").one()
    assert saved.plan_key == "growth"
    assert saved.band == "base"
    assert saved.amount == 299.0
    assert saved.status == "pending"
