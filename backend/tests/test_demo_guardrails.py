"""Tests for demo data guardrails and purge tooling."""

from app.database.demo_constants import DEMO_COOPERATIVE_NAME
from app.database.purge_demo import purge_demo_cooperative
from app.database.seed import seed_golden_path


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
