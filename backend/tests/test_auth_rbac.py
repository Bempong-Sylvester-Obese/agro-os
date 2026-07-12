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

