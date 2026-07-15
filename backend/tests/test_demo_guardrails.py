"""Tests for demo data guardrails and purge tooling."""

from app.database.demo_constants import DEMO_COOPERATIVE_NAME
from app.database.purge_demo import purge_demo_cooperative, reset_demo_workspace
from app.database.seed import seed_golden_path
from app.models.models import AdminAuditLog, Cooperative, CooperativeMembership, User
from app.services.auth_service import create_access_token, get_password_hash


def test_payment_simulation_endpoint_does_not_exist(client):
    resp = client.post(
        "/webhooks/moolre/payment/simulate",
        json={"transaction_id": 1},
    )
    assert resp.status_code == 404


def test_list_transactions_requires_cooperative_scope(client):
    resp = client.get("/transactions/")
    assert resp.status_code == 400


def test_list_loans_requires_cooperative_scope(client):
    resp = client.get("/loans/")
    assert resp.status_code == 400


def test_seed_skips_when_demo_flag_disabled(db, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_DATA", "false")
    from app.config import get_settings

    get_settings.cache_clear()
    result = seed_golden_path(db)
    get_settings.cache_clear()
    assert result["seeded"] is False


def test_purge_demo_dry_run_reports_demo_cooperative(db, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    seed_golden_path(db)
    get_settings.cache_clear()
    result = purge_demo_cooperative(db, dry_run=True)
    assert result["dry_run"] is True
    assert result["cooperative_name"] == DEMO_COOPERATIVE_NAME
    assert result["farmers"] >= 1


def test_purge_demo_deletes_demo_cooperative(db, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    seed_golden_path(db)
    get_settings.cache_clear()
    result = purge_demo_cooperative(db, dry_run=False)
    assert result["deleted"] is True
    second = purge_demo_cooperative(db, dry_run=True)
    assert second["reason"] == "demo cooperative not found"


def test_reset_demo_workspace_preserves_cooperative_and_user(db, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    seed_golden_path(db)
    get_settings.cache_clear()
    cooperative = db.query(Cooperative).filter(Cooperative.name == DEMO_COOPERATIVE_NAME).one()
    user = User(
        email="reset-admin@example.com",
        hashed_password=get_password_hash("strong-password"),
        role="admin",
        cooperative_id=cooperative.id,
    )
    db.add(user)
    db.commit()

    result = reset_demo_workspace(db)

    assert result["reset"] is True
    assert db.query(Cooperative).filter(Cooperative.id == cooperative.id).one()
    assert db.query(User).filter(User.id == user.id).one()
    assert (
        db.query(CooperativeMembership)
        .filter(CooperativeMembership.cooperative_id == cooperative.id)
        .count()
        == 0
    )


def test_demo_reset_endpoint_requires_preview_confirmation(client, db, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "strong-demo-reset-test-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-demo-reset-password")
    from app.config import get_settings

    get_settings.cache_clear()
    seed_golden_path(db)
    cooperative = db.query(Cooperative).filter(Cooperative.name == DEMO_COOPERATIVE_NAME).one()
    user = User(
        email="reset-api-admin@example.com",
        hashed_password=get_password_hash("strong-password"),
        role="admin",
        cooperative_id=cooperative.id,
    )
    db.add(user)
    db.commit()
    token = create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    preview = client.get("/admin/demo-reset/preview", headers=headers)
    assert preview.status_code == 200
    assert preview.json()["dry_run"] is True

    reset = client.post(
        "/admin/demo-reset/confirm",
        headers=headers,
        json={
            "confirmation_token": preview.json()["confirmation_token"],
            "confirmation_phrase": "RESET DEMO",
        },
    )
    assert reset.status_code == 200
    assert reset.json()["reset"] is True
    assert (
        db.query(AdminAuditLog)
        .filter(
            AdminAuditLog.cooperative_id == cooperative.id,
            AdminAuditLog.action == "demo_workspace.reset",
        )
        .count()
        == 1
    )
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()


def test_demo_reset_is_hidden_in_production(client, db, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "strong-production-reset-test-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-admin-password")
    from app.config import get_settings

    get_settings.cache_clear()
    cooperative = Cooperative(name=DEMO_COOPERATIVE_NAME, currency="GHS")
    db.add(cooperative)
    db.flush()
    user = User(
        email="production-admin@example.com",
        hashed_password=get_password_hash("strong-password"),
        role="admin",
        cooperative_id=cooperative.id,
    )
    db.add(user)
    db.commit()
    token = create_access_token({"sub": user.email})

    response = client.get(
        "/admin/demo-reset/preview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()
