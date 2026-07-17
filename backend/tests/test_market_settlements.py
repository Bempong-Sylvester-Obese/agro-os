"""Focused cooperative market and settlement workflow coverage."""

from decimal import Decimal

import pytest

from app.config import get_settings
from app.models.models import (
    Cooperative,
    CooperativeMembership,
    Farmer,
    Transaction,
    User,
)
from app.services.auth_service import create_access_token, get_password_hash
from app.services.communications_service import CommunicationsService
from app.services.moolre_service import MoolreService


def _add_farmer(client, cooperative_id: int, name: str, phone: str):
    response = client.post(
        "/farmers/",
        json={
            "name": name,
            "phone": phone,
            "cooperative_id": cooperative_id,
            "crop_type": "Cocoa",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _market(client, cooperative, farmer):
    second = _add_farmer(
        client, cooperative["id"], "Ama Owusu", "+233551000099"
    )
    intake_ids = []
    for membership_id, quantity in (
        (farmer["id"], "60.000"),
        (second["id"], "40.000"),
    ):
        response = client.post(
            "/intakes/",
            json={
                "cooperative_id": cooperative["id"],
                "membership_id": membership_id,
                "crop_type": "Cocoa",
                "quantity_kg": quantity,
            },
        )
        assert response.status_code == 201, response.text
        intake_id = response.json()["id"]
        review = client.post(
            f"/intakes/{intake_id}/accept",
            params={"cooperative_id": cooperative["id"]},
            json={"net_quantity_kg": quantity, "quality_grade": "A"},
        )
        assert review.status_code == 200, review.text
        intake_ids.append(intake_id)
    batch = client.post(
        "/aggregation-batches/",
        json={
            "cooperative_id": cooperative["id"],
            "code": "COCOA-001",
            "crop_type": "Cocoa",
        },
    ).json()
    assert client.post(
        f"/aggregation-batches/{batch['id']}/intakes",
        params={"cooperative_id": cooperative["id"]},
        json={"intake_ids": intake_ids},
    ).status_code == 200
    assert client.post(
        f"/aggregation-batches/{batch['id']}/close",
        params={"cooperative_id": cooperative["id"]},
    ).status_code == 200
    buyer = client.post(
        "/buyers/",
        json={
            "cooperative_id": cooperative["id"],
            "name": "Golden Cocoa Ltd",
            "phone": "0244000000",
        },
    ).json()
    sale_response = client.post(
        "/sales/",
        json={
            "cooperative_id": cooperative["id"],
            "aggregation_batch_id": batch["id"],
            "buyer_id": buyer["id"],
            "quantity_kg": "100.000",
            "unit_price": "2.00",
        },
    )
    assert sale_response.status_code == 201, sale_response.text
    sale = sale_response.json()
    assert client.post(
        f"/sales/{sale['id']}/confirm",
        params={"cooperative_id": cooperative["id"]},
    ).status_code == 200
    return second, sale


def _fund_sale(client, cooperative_id: int, sale_id: int):
    receipt = client.post(
        f"/sales/{sale_id}/receipts",
        params={"cooperative_id": cooperative_id},
        json={"amount": "200.00", "reference": f"BUYER-{sale_id}"},
    )
    assert receipt.status_code == 201, receipt.text
    verified = client.post(
        f"/sales/{sale_id}/receipts/{receipt.json()['id']}/verify",
        params={"cooperative_id": cooperative_id},
    )
    assert verified.status_code == 200, verified.text


def _calculate(client, cooperative_id: int, sale_id: int):
    response = client.post(
        f"/settlements/sales/{sale_id}/calculate",
        params={"cooperative_id": cooperative_id},
        json={
            "cooperative_fee_percent": "10",
            "transport_total": "10.00",
            "quality_total": "5.00",
            "manual_deductions": [],
            "deduct_outstanding_loans": False,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_crop_intake_rejects_animal_only_member(client, cooperative):
    member = client.post(
        "/farmers/",
        json={
            "name": "Animal Only",
            "phone": "+233551000088",
            "cooperative_id": cooperative["id"],
            "production_focus": "animal",
            "animal_type": "Cattle",
        },
    ).json()

    response = client.post(
        "/intakes/",
        json={
            "cooperative_id": cooperative["id"],
            "membership_id": member["id"],
            "crop_type": "Maize",
            "quantity_kg": "10.000",
        },
    )

    assert response.status_code == 409
    assert "crop-only" in response.json()["detail"]


def test_states_verified_funds_gate_and_exact_arithmetic(
    client, cooperative, farmer
):
    _, sale = _market(client, cooperative, farmer)
    blocked = client.post(
        f"/settlements/sales/{sale['id']}/calculate",
        params={"cooperative_id": cooperative["id"]},
        json={},
    )
    assert blocked.status_code == 409

    _fund_sale(client, cooperative["id"], sale["id"])
    settlement = _calculate(client, cooperative["id"], sale["id"])

    assert Decimal(settlement["gross_total"]) == Decimal("200.00")
    assert Decimal(settlement["deductions_total"]) == Decimal("35.00")
    assert Decimal(settlement["net_total"]) == Decimal("165.00")
    assert sum(
        Decimal(line["net_amount"]) for line in settlement["lines"]
    ) == Decimal("165.00")
    assert client.post(
        f"/settlements/{settlement['id']}/submit",
        params={"cooperative_id": cooperative["id"]},
    ).json()["status"] == "pending_approval"
    assert client.post(
        f"/settlements/{settlement['id']}/approve",
        params={"cooperative_id": cooperative["id"]},
    ).json()["status"] == "approved"
    for report in (
        "intake",
        "aggregation",
        "buyers",
        "sales",
        "settlements",
        "payout-exceptions",
    ):
        exported = client.get(
            f"/reports/{report}.csv",
            params={"cooperative_id": cooperative["id"]},
        )
        assert exported.status_code == 200, exported.text
        assert exported.headers["content-type"].startswith("text/csv")


@pytest.fixture()
def auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "market-test-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "market-test-password")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _staff(db, cooperative, suffix: str, role: str = "admin"):
    user = User(
        email=f"{role}-{suffix}@example.com",
        hashed_password=get_password_hash("password"),
        role=role,
        cooperative_id=cooperative.id,
    )
    db.add(user)
    db.commit()
    token = create_access_token({"sub": user.email})
    return user, {"Authorization": f"Bearer {token}"}


def test_maker_checker_and_tenant_scope(client, db, auth_enabled):
    first = Cooperative(name="First Coop")
    second = Cooperative(name="Second Coop")
    db.add_all([first, second])
    db.flush()
    maker, maker_headers = _staff(db, first, "maker")
    _, checker_headers = _staff(db, first, "checker", role="finance_officer")
    _, other_headers = _staff(db, second, "other")
    identity = Farmer(name="Scoped Farmer", phone="0249876500")
    db.add(identity)
    db.flush()
    member = CooperativeMembership(
        farmer_id=identity.id,
        cooperative_id=first.id,
    )
    db.add(member)
    db.commit()

    intake = client.post(
        "/intakes/",
        headers=maker_headers,
        json={
            "cooperative_id": second.id,
            "membership_id": member.id,
            "crop_type": "Maize",
            "quantity_kg": "10",
        },
    )
    assert intake.status_code == 201
    assert intake.json()["cooperative_id"] == first.id
    assert client.get(
        "/intakes/", headers=other_headers
    ).json() == []

    # Direct receipt records isolate the maker-checker rule from setup noise.
    from app.models.models import (
        AggregationBatch,
        Buyer,
        BuyerPaymentReceipt,
        ProduceSale,
        ProduceSaleStatus,
    )

    batch = AggregationBatch(
        cooperative_id=first.id,
        code="MC-1",
        crop_type="Maize",
        status="sold",
        total_quantity_kg=10,
        created_by=str(maker.id),
    )
    buyer = Buyer(
        cooperative_id=first.id,
        name="Maker Checker Buyer",
        created_by=str(maker.id),
    )
    db.add_all([batch, buyer])
    db.flush()
    sale = ProduceSale(
        cooperative_id=first.id,
        aggregation_batch_id=batch.id,
        buyer_id=buyer.id,
        quantity_kg=10,
        unit_price=2,
        gross_amount=20,
        status=ProduceSaleStatus.confirmed,
        created_by=str(maker.id),
    )
    db.add(sale)
    db.flush()
    receipt = BuyerPaymentReceipt(
        cooperative_id=first.id,
        sale_id=sale.id,
        amount=20,
        reference="MC-RECEIPT",
        submitted_by=str(maker.id),
    )
    db.add(receipt)
    db.commit()
    own = client.post(
        f"/sales/{sale.id}/receipts/{receipt.id}/verify",
        headers=maker_headers,
    )
    assert own.status_code == 409
    checked = client.post(
        f"/sales/{sale.id}/receipts/{receipt.id}/verify",
        headers=checker_headers,
    )
    assert checked.status_code == 200


def test_payout_is_durable_idempotent_and_retries_failed_only(
    client, db, cooperative, farmer, monkeypatch
):
    _, sale = _market(client, cooperative, farmer)
    _fund_sale(client, cooperative["id"], sale["id"])
    settlement = _calculate(client, cooperative["id"], sale["id"])
    client.post(
        f"/settlements/{settlement['id']}/submit",
        params={"cooperative_id": cooperative["id"]},
    )
    client.post(
        f"/settlements/{settlement['id']}/approve",
        params={"cooperative_id": cooperative["id"]},
    )

    async def wallet(_self, _account=None):
        return "TEST-ACCOUNT-001", None

    calls = []
    amounts_by_reference = {}

    async def transfer(_self, **kwargs):
        calls.append(kwargs["external_ref"])
        amounts_by_reference[kwargs["external_ref"]] = str(kwargs["amount"])
        if len(calls) == 1:
            return {
                "success": False,
                "moolre_transfer_ref": kwargs["external_ref"],
                "message": "temporary failure",
            }
        return {
            "success": True,
            "moolre_transfer_ref": kwargs["external_ref"],
            "message": "accepted",
        }

    async def status(_self, reference, **_kwargs):
        return {
            "status": "completed",
            "amount": amounts_by_reference[reference],
        }

    async def sms(_self, **_kwargs):
        return {"success": True}

    monkeypatch.setattr(MoolreService, "resolve_verified_account", wallet)
    monkeypatch.setattr(MoolreService, "initiate_transfer", transfer)
    monkeypatch.setattr(MoolreService, "transfer_status", status)
    monkeypatch.setattr(
        CommunicationsService, "send_settlement_statement", sms
    )

    first = client.post(
        f"/settlements/{settlement['id']}/disburse",
        params={"cooperative_id": cooperative["id"]},
    )
    assert first.status_code == 200, first.text
    assert len(first.json()["attempted_line_ids"]) == 2
    duplicate = client.post(
        f"/settlements/{settlement['id']}/disburse",
        params={"cooperative_id": cooperative["id"]},
    )
    assert duplicate.status_code == 409

    retry = client.post(
        f"/settlements/{settlement['id']}/retry-failed",
        params={"cooperative_id": cooperative["id"]},
    )
    assert retry.status_code == 200, retry.text
    assert len(retry.json()["attempted_line_ids"]) == 1
    transactions = (
        db.query(Transaction)
        .filter(Transaction.settlement_line_id.is_not(None))
        .all()
    )
    assert len(transactions) == 3
    assert len({tx.moolre_transfer_ref for tx in transactions}) == 3
    reconciled = client.post(
        f"/settlements/{settlement['id']}/reconcile",
        params={"cooperative_id": cooperative["id"]},
    )
    assert reconciled.status_code == 200, reconciled.text
    assert reconciled.json()["settlement"]["status"] == "completed"
