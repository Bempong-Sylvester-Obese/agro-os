"""Enterprise organizations (#237): model, scope rules, switching, consolidated billing."""

from datetime import datetime, timedelta

import jwt
import pytest

from app.config import get_settings
from app.models.models import Cooperative, Organization, PendingCheckout, User
from app.services import entitlements, subscription_lifecycle as lifecycle
from app.services.auth_service import create_access_token, get_password_hash
from app.services.plans import get_plan_limit


@pytest.fixture()
def auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "strong-organizations-test-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-organizations-password")
    get_settings.cache_clear()
    yield
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()


def _admin(db, suffix: str, *, organization_id: int | None = None) -> tuple[Cooperative, User, dict]:
    coop = Cooperative(name=f"Coop {suffix}", currency="GHS", organization_id=organization_id)
    db.add(coop)
    db.flush()
    user = User(
        email=f"admin-{suffix}@example.com",
        hashed_password=get_password_hash("password-123456"),
        role="admin",
        cooperative_id=coop.id,
        organization_id=organization_id,
    )
    db.add(user)
    db.commit()
    headers = {"Authorization": f"Bearer {create_access_token({'sub': user.email})}"}
    return coop, user, headers


# ---------------------------------------------------------------------------
# Billing inheritance (pure model / lifecycle)
# ---------------------------------------------------------------------------


def test_member_cooperative_inherits_live_enterprise_plan():
    org = Organization(name="Union", subscription_plan="enterprise",
                       subscription_status=Organization.STATUS_ACTIVE,
                       subscription_expires_at=datetime.utcnow() + timedelta(days=200))
    coop = Cooperative(name="Member", currency="GHS", subscription_plan="starter", subscription_status="active")
    coop.organization = org
    assert lifecycle.organization_plan_key(coop) == "enterprise"
    assert lifecycle.effective_plan_key(coop) == "enterprise"
    assert entitlements.limit_for(coop, "max_members") == 0  # unlimited
    assert lifecycle.has_paid_access(coop) is True


@pytest.mark.parametrize("status, expires_delta", [
    (Organization.STATUS_PENDING, 200),
    (Organization.STATUS_CANCELLED, 200),
    (Organization.STATUS_EXPIRED, 200),
    (Organization.STATUS_ACTIVE, -1),  # active but past expiry
])
def test_member_falls_back_to_own_plan_when_contract_not_live(status, expires_delta):
    org = Organization(name="Union", subscription_status=status,
                       subscription_expires_at=datetime.utcnow() + timedelta(days=expires_delta))
    coop = Cooperative(name="Member", currency="GHS", subscription_plan="starter", subscription_status="active")
    coop.organization = org
    assert lifecycle.organization_plan_key(coop) is None
    assert lifecycle.effective_plan_key(coop) == "starter"


def test_independent_cooperative_unaffected():
    coop = Cooperative(name="Solo", currency="GHS", subscription_plan="starter", subscription_status="active")
    assert lifecycle.organization_plan_key(coop) is None
    assert lifecycle.effective_plan_key(coop) == "starter"


def test_activate_enterprise_script_apply():
    from scripts.activate_enterprise import apply

    org = Organization(id=7, name="Union")
    now = datetime(2026, 9, 22)
    summary = apply(org, months=12, cancel=False, contract="ENT-1", plan="enterprise", now=now)
    assert org.subscription_status == Organization.STATUS_ACTIVE
    assert org.subscription_expires_at == now + timedelta(days=360)
    assert org.contract_reference == "ENT-1"
    assert "ENT-1" in summary and "active until" in summary

    apply(org, months=0, cancel=True, contract=None, plan="enterprise", now=now)
    assert org.subscription_status == Organization.STATUS_CANCELLED
    assert org.subscription_is_live(now + timedelta(seconds=1)) is False

    with pytest.raises(ValueError):
        apply(Organization(name="x"), months=0, cancel=False, contract=None, plan="enterprise")


# ---------------------------------------------------------------------------
# API: creation and scope rules
# ---------------------------------------------------------------------------


def test_create_organization_from_own_cooperative(client, db, auth_enabled):
    coop, user, headers = _admin(db, "a")
    resp = client.post("/organizations", json={"name": "Ashanti Union", "billing_email": "billing@union.org"}, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["subscription_plan"] == "enterprise"
    assert body["subscription_status"] == "pending"
    assert body["subscription_live"] is False
    assert body["cooperative_count"] == 1

    db.refresh(coop)
    db.refresh(user)
    assert coop.organization_id == body["id"]
    assert user.organization_id == body["id"]

    # Second attempt is rejected: one organization per administrator.
    assert client.post("/organizations", json={"name": "Again"}, headers=headers).status_code == 409

    me = client.get("/organizations/me", headers=headers)
    assert me.status_code == 200
    assert [c["name"] for c in me.json()["cooperatives"]] == ["Coop a"]
    assert me.json()["cooperatives"][0]["is_active_scope"] is True
    assert me.json()["cooperatives"][0]["inherits_organization_plan"] is False


def test_non_org_admin_gets_404_everywhere(client, db, auth_enabled):
    _, _, org_headers = _admin(db, "owner")
    org_id = client.post("/organizations", json={"name": "Union"}, headers=org_headers).json()["id"]

    _, _, outsider = _admin(db, "outsider")
    assert client.get("/organizations/me", headers=outsider).status_code == 404
    assert client.get(f"/organizations/{org_id}/cooperatives", headers=outsider).status_code == 404
    assert client.get(f"/organizations/{org_id}/billing", headers=outsider).status_code == 404
    assert client.post(f"/organizations/{org_id}/cooperatives", json={"name": "Sneak"}, headers=outsider).status_code == 404
    assert client.patch(f"/organizations/{org_id}", json={"name": "Hijack"}, headers=outsider).status_code == 404
    assert client.post(f"/organizations/{org_id}/switch", json={"cooperative_id": 1}, headers=outsider).status_code == 404

    # Anonymous
    assert client.get("/organizations/me").status_code == 401


def test_org_admin_of_other_org_cannot_touch_this_org(client, db, auth_enabled):
    _, _, h1 = _admin(db, "one")
    org1 = client.post("/organizations", json={"name": "One"}, headers=h1).json()["id"]
    _, _, h2 = _admin(db, "two")
    org2 = client.post("/organizations", json={"name": "Two"}, headers=h2).json()["id"]
    assert org1 != org2
    assert client.get(f"/organizations/{org1}/billing", headers=h2).status_code == 404
    assert client.patch(f"/organizations/{org2}", json={"name": "Two Renamed"}, headers=h2).status_code == 200


def test_subscription_fields_cannot_be_set_via_api(client, db, auth_enabled):
    _, _, headers = _admin(db, "b")
    org_id = client.post("/organizations", json={"name": "Union"}, headers=headers).json()["id"]
    resp = client.patch(
        f"/organizations/{org_id}",
        json={"name": "Union", "subscription_status": "active", "subscription_plan": "enterprise"},
        headers=headers,
    )
    assert resp.status_code == 200
    org = db.get(Organization, org_id)
    assert org.subscription_status == Organization.STATUS_PENDING


# ---------------------------------------------------------------------------
# API: multiple cooperatives, switching, inheritance end-to-end
# ---------------------------------------------------------------------------


def test_multiple_cooperatives_switch_scope_and_inherit_plan(client, db, auth_enabled):
    first, user, headers = _admin(db, "hq")
    org_id = client.post("/organizations", json={"name": "Union"}, headers=headers).json()["id"]

    created = client.post(
        f"/organizations/{org_id}/cooperatives",
        json={"name": "Branch North", "location": "Tamale"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    north_id = created.json()["id"]
    assert created.json()["subscription_plan"] == "starter"
    assert created.json()["is_active_scope"] is False

    # Active scope is still the first cooperative: cross-coop reads are 404.
    assert client.get(f"/cooperatives/{north_id}", headers=headers).status_code == 404
    assert client.get(f"/cooperatives/{first.id}", headers=headers).status_code == 200

    # Switch: new token, new scope.
    switched = client.post(f"/organizations/{org_id}/switch", json={"cooperative_id": north_id}, headers=headers)
    assert switched.status_code == 200, switched.text
    token = switched.json()["access_token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["cooperative_id"] == north_id
    assert claims["organization_id"] == org_id
    assert switched.json()["user"]["cooperative_id"] == north_id
    assert switched.json()["user"]["organization_id"] == org_id
    new_headers = {"Authorization": f"Bearer {token}"}

    assert client.get(f"/cooperatives/{north_id}", headers=new_headers).status_code == 200
    assert client.get(f"/cooperatives/{first.id}", headers=new_headers).status_code == 404
    # The old token is also re-scoped because scope is read from the user row.
    assert client.get(f"/cooperatives/{north_id}", headers=headers).status_code == 200

    # Switching to a cooperative outside the organization is refused.
    stranger = Cooperative(name="Stranger", currency="GHS")
    db.add(stranger)
    db.commit()
    assert client.post(f"/organizations/{org_id}/switch", json={"cooperative_id": stranger.id}, headers=new_headers).status_code == 404

    # Contract activation (operator) → both cooperatives inherit Enterprise.
    org = db.get(Organization, org_id)
    org.subscription_status = Organization.STATUS_ACTIVE
    org.subscription_expires_at = datetime.utcnow() + timedelta(days=365)
    db.commit()

    rows = client.get(f"/organizations/{org_id}/cooperatives", headers=new_headers).json()
    assert {r["effective_plan_key"] for r in rows} == {"enterprise"}
    assert all(r["inherits_organization_plan"] for r in rows)
    assert all(r["members"]["unlimited"] for r in rows)

    # Entitlements follow: the north branch (starter on record) can exceed the starter cap.
    starter_cap = get_plan_limit("starter", "max_members")
    for i in range(starter_cap + 1):
        r = client.post(
            "/farmers/",
            json={"name": f"Member {i}", "phone": f"+23355000{i:04d}", "cooperative_id": north_id, "crop_type": "cocoa"},
            headers=new_headers,
        )
        assert r.status_code == 201, r.text
    usage = client.get(f"/cooperatives/{north_id}/usage", headers=new_headers).json()
    assert usage["effective_plan_key"] == "enterprise"
    assert usage["limits"]["members"]["used"] == starter_cap + 1


def test_consolidated_billing(client, db, auth_enabled):
    first, user, headers = _admin(db, "bill")
    org_id = client.post("/organizations", json={"name": "Union"}, headers=headers).json()["id"]
    second_id = client.post(f"/organizations/{org_id}/cooperatives", json={"name": "Second"}, headers=headers).json()["id"]

    db.add_all([
        PendingCheckout(reference="sub_upg_first", kind="upgrade", cooperative_id=first.id, plan_key="growth",
                        band="base", amount=299.0, status="consumed", paid_at=datetime(2026, 9, 1)),
        PendingCheckout(reference="sub_upg_second", kind="upgrade", cooperative_id=second_id, plan_key="growth",
                        band="plus_50", amount=449.0, status="pending"),
        PendingCheckout(reference="sub_upg_unrelated", kind="upgrade", cooperative_id=None, plan_key="growth",
                        band="base", amount=299.0, status="consumed"),
    ])
    db.commit()

    resp = client.get(f"/organizations/{org_id}/billing", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["organization"]["id"] == org_id
    assert [c["name"] for c in body["cooperatives"]] == ["Coop bill", "Second"]
    assert body["totals"]["cooperatives"] == 2
    assert body["totals"]["paid"] == 299.0
    assert {h["reference"] for h in body["history"]} == {"sub_upg_first", "sub_upg_second"}
    paid = next(h for h in body["history"] if h["reference"] == "sub_upg_first")
    assert paid["cooperative_name"] == "Coop bill" and paid["outcome"] == "paid"


def test_login_token_carries_organization_id(client, db, auth_enabled):
    coop, user, headers = _admin(db, "login")
    org_id = client.post("/organizations", json={"name": "Union"}, headers=headers).json()["id"]
    login = client.post("/auth/login", json={"email": user.email, "password": "password-123456"})
    assert login.status_code == 200, login.text
    claims = jwt.decode(login.json()["access_token"], options={"verify_signature": False})
    assert claims["organization_id"] == org_id
    assert login.json()["user"]["organization_id"] == org_id
