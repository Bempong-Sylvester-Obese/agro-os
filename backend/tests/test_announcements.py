from unittest.mock import AsyncMock, patch

import pytest

from app.config import get_settings
from app.models.models import (
    Announcement,
    Cooperative,
    CooperativeMembership,
    Farmer,
    User,
)
from app.services.auth_service import create_access_token, get_password_hash


@pytest.fixture()
def auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "test-announcements-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-announcements-admin-password")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _user_headers(db, cooperative, suffix, role):
    user = User(
        email=f"{role}-{suffix}@example.com",
        hashed_password=get_password_hash("password"),
        role=role,
        cooperative_id=cooperative.id,
    )
    db.add(user)
    db.commit()
    token = create_access_token({"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def _member(db, cooperative, suffix, *, sms_consent):
    farmer = Farmer(name=f"Member {suffix}", phone=f"02410000{suffix.zfill(2)}")
    db.add(farmer)
    db.flush()
    membership = CooperativeMembership(
        farmer_id=farmer.id,
        cooperative_id=cooperative.id,
        sms_consent=sms_consent,
    )
    db.add(membership)
    db.commit()
    return membership


def test_announcements_are_scoped_role_guarded_and_consent_aware(
    client, db, auth_enabled
):
    own_coop = Cooperative(name="Announcement Cooperative", currency="GHS")
    other_coop = Cooperative(name="Other Cooperative", currency="GHS")
    db.add_all([own_coop, other_coop])
    db.commit()
    finance_headers = _user_headers(db, own_coop, "1", "finance_officer")
    manager_headers = _user_headers(db, own_coop, "2", "farm_manager")
    admin_headers = _user_headers(db, own_coop, "3", "admin")
    consenting = _member(db, own_coop, "1", sms_consent=True)
    _member(db, own_coop, "2", sms_consent=False)

    with patch(
        "app.services.communications_service.CommunicationsService.send_single_sms",
        new_callable=AsyncMock,
        return_value={"success": True},
    ) as send_sms:
        created = client.post(
            f"/announcements/?cooperative_id={own_coop.id}",
            headers=finance_headers,
            json={
                "title": "Meeting",
                "body": "The monthly meeting starts at 10.",
                "send_sms": True,
            },
        )

    assert created.status_code == 201
    send_sms.assert_awaited_once()
    assert send_sms.await_args.kwargs["recipient"] == consenting.phone

    listed = client.get(
        f"/announcements/?cooperative_id={own_coop.id}",
        headers=manager_headers,
    )
    assert listed.status_code == 200
    assert [row["title"] for row in listed.json()] == ["Meeting"]

    assert client.post(
        f"/announcements/?cooperative_id={own_coop.id}",
        headers=manager_headers,
        json={"title": "Denied", "body": "Not allowed", "send_sms": False},
    ).status_code == 403
    assert client.get(
        f"/announcements/?cooperative_id={other_coop.id}",
        headers=finance_headers,
    ).status_code == 404
    assert client.delete(
        f"/announcements/{created.json()['id']}?cooperative_id={own_coop.id}",
        headers=finance_headers,
    ).status_code == 403

    deleted = client.delete(
        f"/announcements/{created.json()['id']}?cooperative_id={own_coop.id}",
        headers=admin_headers,
    )
    assert deleted.status_code == 204
    db.expire_all()
    assert db.query(Announcement).filter_by(id=created.json()["id"]).one().deleted_at
    assert client.get(
        f"/announcements/?cooperative_id={own_coop.id}",
        headers=manager_headers,
    ).json() == []
