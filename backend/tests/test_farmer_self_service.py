import asyncio
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.models import (
    CooperativeMembership as Farmer,
)
from app.models.models import (
    Loan,
    LoanReminder,
    LoanStatus,
    Transaction,
    TransactionType,
)
from app.services.communications_service import CommunicationsService


def _ussdk_payload(phone, **values):
    return {
        "input": {},
        "props": {
            "session": {"msisdn": phone, "network": "mtn"},
            "values": values,
        },
    }


def _moolre_ussd_payload(session_id, phone, message="", *, new=False):
    return {
        "sessionId": session_id,
        "new": new,
        "msisdn": phone,
        "network": 3,
        "message": message,
        "extension": "109",
        "data": "",
    }


def test_farmer_starts_loan_repayment_from_ussdk(client, farmer, db):
    loan = Loan(
        farmer_id=farmer["id"],
        amount=250,
        purpose="Inputs",
        status=LoanStatus.disbursed,
        expected_repayment_date=date.today() + timedelta(days=7),
        request_channel="ussdk",
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    with patch(
        "app.routes.loans.MoolreService.initiate_payment",
        new_callable=AsyncMock,
        return_value={
            "success": False,
            "verification_required": True,
            "outcome": "verification_required",
            "moolre_reference": "repay-self-service",
            "external_ref": "repay-self-service",
            "message": "OTP required",
        },
    ):
        response = client.post(
            "/ussdk/loan-repayment",
            json=_ussdk_payload(farmer["phone"], loan_id=loan.id),
        )

    assert response.status_code == 200
    assert response.json()["action"] == "request_otp"
    tx = (
        db.query(Transaction)
        .filter(
            Transaction.loan_id == loan.id,
            Transaction.transaction_type == TransactionType.repayment,
        )
        .one()
    )
    assert tx.initiation_channel == "ussdk"
    assert tx.customer_action == "otp"


def test_staff_debit_routes_are_disabled_outside_tests(client, farmer, monkeypatch):
    from app.routes import loans, transactions

    production = SimpleNamespace(app_env="production")
    monkeypatch.setattr(transactions, "get_settings", lambda: production)
    monkeypatch.setattr(loans, "get_settings", lambda: production)

    dues = client.post(
        "/transactions/dues/collect",
        json={"farmer_id": farmer["id"], "amount": 10, "channel": "13"},
    )
    repayment = client.post("/loans/999/repay")

    assert dues.status_code == 403
    assert repayment.status_code == 403


def test_direct_ussd_menu_starts_farmer_loan_repayment(client, farmer, db):
    loan = Loan(
        farmer_id=farmer["id"],
        amount=175,
        status=LoanStatus.disbursed,
        expected_repayment_date=date.today() + timedelta(days=3),
        request_channel="moolre_ussd",
    )
    db.add(loan)
    db.commit()

    client.post(
        "/webhooks/moolre/ussd",
        json=_moolre_ussd_payload("repay-direct", farmer["phone"], new=True),
    )
    selected = client.post(
        "/webhooks/moolre/ussd",
        json=_moolre_ussd_payload("repay-direct", farmer["phone"], "6"),
    )
    assert "Confirm" in selected.json()["message"]

    with patch(
        "app.routes.loans.MoolreService.initiate_payment",
        new_callable=AsyncMock,
        return_value={
            "success": False,
            "verification_required": True,
            "outcome": "verification_required",
            "moolre_reference": "repay-direct-ref",
            "external_ref": "repay-direct-ref",
            "message": "OTP required",
        },
    ):
        started = client.post(
            "/webhooks/moolre/ussd",
            json=_moolre_ussd_payload("repay-direct", farmer["phone"], "1"),
        )

    assert started.json()["reply"] is True
    assert "OTP Moolre sent" in started.json()["message"]


def test_loan_reminder_is_idempotent_and_never_creates_payment(db, farmer):
    membership = db.query(Farmer).filter(Farmer.id == farmer["id"]).one()
    loan = Loan(
        farmer_id=membership.id,
        amount=100,
        status=LoanStatus.disbursed,
        expected_repayment_date=date.today() + timedelta(days=3),
        request_channel="ussdk",
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    service = CommunicationsService()

    with patch.object(
        service.moolre,
        "send_single_sms",
        new_callable=AsyncMock,
        return_value={"success": True, "message": "sent", "raw": {"data": "sms-1"}},
    ) as send:
        first = asyncio.run(
            service.send_loan_repayment_reminder(
                loan=loan,
                farmer=membership,
                reminder_kind="due_in_3_days",
                scheduled_for=date.today(),
                db=db,
            )
        )
        second = asyncio.run(
            service.send_loan_repayment_reminder(
                loan=loan,
                farmer=membership,
                reminder_kind="due_in_3_days",
                scheduled_for=date.today(),
                db=db,
            )
        )

    assert first.id == second.id
    assert send.await_count == 1
    assert db.query(LoanReminder).count() == 1
    assert db.query(Transaction).count() == 0
