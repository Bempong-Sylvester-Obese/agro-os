"""Fail-closed authentication and cooperative isolation tests."""

import pytest

from app.config import get_settings
from app.models.models import Cooperative, CooperativeMembership, Farmer, User
from app.services.auth_service import create_access_token, get_password_hash


@pytest.fixture()
def auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "test-rbac-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-rbac-admin-password")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _tenant(db, suffix: str, role: str = "admin"):
    cooperative = Cooperative(name=f"Cooperative {suffix}", currency="GHS")
    db.add(cooperative)
    db.flush()
    user = User(
        email=f"{role}-{suffix}@example.com",
        hashed_password=get_password_hash("password"),
        role=role,
        cooperative_id=cooperative.id,
    )
    farmer = Farmer(
        name=f"Farmer {suffix}",
        phone=f"02400000{suffix.zfill(2)}",
    )
    db.add_all([user, farmer])
    db.flush()
    membership = CooperativeMembership(
        farmer_id=farmer.id,
        cooperative_id=cooperative.id,
    )
    db.add(membership)
    db.commit()
    db.refresh(user)
    db.refresh(membership)
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "cooperative_id": cooperative.id,
            "role": role,
        }
    )
    return cooperative, user, membership, {"Authorization": f"Bearer {token}"}


def test_sensitive_get_fails_closed_without_token(client, auth_enabled):
    response = client.get("/farmers/")
    assert response.status_code == 401

    assert client.get("/health").status_code == 200
    assert client.post("/webhooks/moolre/payment", content=b"{}").status_code != 401


def test_cross_cooperative_detail_is_not_visible(client, db, auth_enabled):
    _, _, _, first_headers = _tenant(db, "1")
    _, _, other_farmer, _ = _tenant(db, "2")

    response = client.get(f"/farmers/{other_farmer.id}", headers=first_headers)

    assert response.status_code == 404


def test_authenticated_scope_overrides_farmer_body(client, db, auth_enabled):
    own_coop, _, _, headers = _tenant(db, "3")
    other_coop, _, _, _ = _tenant(db, "4")

    response = client.post(
        "/farmers/",
        headers=headers,
        json={
            "name": "Scoped Farmer",
            "phone": "0249999999",
            "cooperative_id": other_coop.id,
        },
    )

    assert response.status_code == 201
    assert response.json()["cooperative_id"] == own_coop.id


def test_finance_officer_cannot_mutate_admin_resource(client, db, auth_enabled):
    _, _, farmer, headers = _tenant(db, "5", role="finance_officer")

    response = client.post(
        "/production/",
        headers=headers,
        json={
            "farmer_id": farmer.id,
            "crop_type": "Maize",
            "expected_kg": 100,
            "quantity_kg": 80,
            "harvest_date": "2026-07-12",
        },
    )

    assert response.status_code == 403


def test_staff_only_decide_farmer_originated_loans(client, db, auth_enabled):
    _, admin, membership, headers = _tenant(db, "11")
    created = client.post(
        "/ussdk/loan-request",
        json={
            "input": {},
            "props": {
                "session": {"msisdn": membership.phone},
                "values": {"amount": "300", "purpose": "Seed"},
            },
        },
    )
    assert created.status_code == 200
    loan_id = created.json()["loan_id"]

    staff_create = client.post(
        "/loans/",
        headers=headers,
        json={"farmer_id": membership.id, "amount": 300, "purpose": "Seed"},
    )
    assert staff_create.status_code == 403

    approved = client.post(f"/loans/{loan_id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["approved_by"] == str(admin.id)


def test_admin_manages_only_own_cooperative_users(client, db, auth_enabled):
    _, admin, _, headers = _tenant(db, "6")
    _, other_admin, _, _ = _tenant(db, "7")
    created = client.post(
        "/auth/register",
        headers=headers,
        json={
            "email": "finance-6@example.com",
            "password": "strong-password",
            "role": "finance_officer",
        },
    )
    assert created.status_code == 200

    listed = client.get("/auth/users", headers=headers)
    assert listed.status_code == 200
    assert {row["email"] for row in listed.json()} == {
        admin.email,
        "finance-6@example.com",
    }
    assert other_admin.email not in {row["email"] for row in listed.json()}
    audit = client.get("/admin/audit", headers=headers)
    assert audit.status_code == 200
    assert any(row["action"] == "user.created" for row in audit.json())

    updated = client.patch(
        f"/auth/users/{created.json()['id']}",
        headers=headers,
        json={"is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    login = client.post(
        "/auth/login",
        json={"email": "finance-6@example.com", "password": "strong-password"},
    )
    assert login.status_code == 401


def test_admin_cannot_deactivate_self(client, db, auth_enabled):
    _, admin, _, headers = _tenant(db, "8")
    response = client.patch(
        f"/auth/users/{admin.id}",
        headers=headers,
        json={"is_active": False},
    )
    assert response.status_code == 409


def test_agro_ai_ignores_cross_tenant_scope_request(client, db, auth_enabled):
    own_coop, _, own_farmer, headers = _tenant(db, "9")
    other_coop, _, other_farmer, _ = _tenant(db, "10")

    response = client.get(
        f"/api/farmers?cooperative_id={other_coop.id}",
        headers=headers,
    )

    assert response.status_code == 200
    own_code = f"GH-{own_farmer.id:04d}"
    other_code = f"GH-{other_farmer.id:04d}"
    assert {item["farmer_id"] for item in response.json()} == {own_code}
    assert other_code not in {item["farmer_id"] for item in response.json()}
    assert own_coop.id != other_coop.id


def test_required_password_change_blocks_api_until_completed(
    client, db, auth_enabled
):
    _, _, _, admin_headers = _tenant(db, "12")
    created = client.post(
        "/auth/register",
        headers=admin_headers,
        json={
            "email": "manager-12@example.com",
            "password": "temporary-password",
            "role": "farm_manager",
        },
    )
    assert created.status_code == 200

    login = client.post(
        "/auth/login",
        json={
            "email": "manager-12@example.com",
            "password": "temporary-password",
        },
    )
    assert login.status_code == 200
    assert login.json()["password_change_required"] is True
    forced_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    assert client.get("/farmers/", headers=forced_headers).status_code == 403
    changed = client.post(
        "/auth/change-password",
        headers=forced_headers,
        json={"new_password": "permanent-password"},
    )
    assert changed.status_code == 200
    assert client.get("/farmers/", headers=forced_headers).status_code == 200

    assert client.post(
        "/auth/login",
        json={
            "email": "manager-12@example.com",
            "password": "temporary-password",
        },
    ).status_code == 401
    relogin = client.post(
        "/auth/login",
        json={
            "email": "manager-12@example.com",
            "password": "permanent-password",
        },
    )
    assert relogin.status_code == 200
    assert relogin.json()["password_change_required"] is False


def test_cooperative_staff_records_only_own_attendance(
    client, db, auth_enabled
):
    own_coop, _, own_member, headers = _tenant(db, "13", role="farm_manager")
    _, _, other_member, _ = _tenant(db, "14")
    payload = {
        "farmer_id": own_member.id,
        "event_name": "Monthly meeting",
        "event_date": "2026-08-17T10:00:00",
        "attended": True,
    }

    created = client.post(
        f"/farmers/{own_member.id}/attendance",
        headers=headers,
        json=payload,
    )
    assert created.status_code == 201
    assert created.json()["farmer_id"] == own_member.id

    cross_tenant = client.post(
        f"/farmers/{other_member.id}/attendance",
        headers=headers,
        json={**payload, "farmer_id": other_member.id},
    )
    assert cross_tenant.status_code == 404
    assert own_member.cooperative_id == own_coop.id

