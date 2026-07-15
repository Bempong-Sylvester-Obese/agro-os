"""Regression coverage for persisted conversion intent."""

from datetime import date, timedelta

from app.models.models import Cooperative, DemoBooking, User


def test_signup_persists_subscription_and_business_role(client, db):
    response = client.post(
        "/auth/signup",
        json={
            "email": "growth-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Growth Cooperative",
            "location": "Kumasi",
            "member_count": 240,
            "subscription_plan": "growth",
            "onboarding_role": "Operations director",
        },
    )

    assert response.status_code == 201
    assert response.json()["subscription_plan"] == "growth"
    assert response.json()["onboarding_role"] == "Operations director"
    cooperative = (
        db.query(Cooperative).filter(Cooperative.name == "Growth Cooperative").one()
    )
    user = db.query(User).filter(User.email == "growth-owner@example.com").one()
    assert cooperative.subscription_plan == "growth"
    assert user.onboarding_role == "Operations director"


def test_signup_defaults_to_starter_without_onboarding_context(client, db):
    response = client.post(
        "/auth/signup",
        json={
            "email": "starter-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Starter Cooperative",
        },
    )

    assert response.status_code == 201
    assert response.json()["subscription_plan"] == "starter"
    cooperative = (
        db.query(Cooperative).filter(Cooperative.name == "Starter Cooperative").one()
    )
    assert cooperative.subscription_plan == "starter"


def test_demo_bookings_are_persisted_with_unique_server_references(client, db):
    request = {
        "name": "Ama Mensah",
        "email": "ama@example.com",
        "phone": "+233200000000",
        "cooperative": "Ama Growers",
        "size": "201–500 members",
        "topic": "Enterprise implementation",
        "notes": "Discuss rollout.",
        "selected_date": (date.today() + timedelta(days=7)).isoformat(),
        "selected_time": "10:00",
        "is_enterprise": True,
    }

    first = client.post("/marketing/demo-bookings", json=request)
    second = client.post("/marketing/demo-bookings", json=request)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["reference"].startswith("AGO-DEMO-")
    assert first.json()["reference"] != second.json()["reference"]
    assert (
        db.query(DemoBooking).filter(DemoBooking.email == request["email"]).count() == 2
    )


def test_demo_booking_rejects_non_future_date(client):
    response = client.post(
        "/marketing/demo-bookings",
        json={
            "name": "Ama Mensah",
            "email": "ama@example.com",
            "cooperative": "Ama Growers",
            "size": "1–50 members",
            "topic": "Full platform evaluation",
            "selected_date": date.today().isoformat(),
            "selected_time": "09:00",
        },
    )

    assert response.status_code == 422
