"""SMS consent: explicit, timestamped, enforced on every member-addressed send path (#247)."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

from app.models.models import AdminAuditLog, CommunicationLog, CooperativeMembership, Loan, LoanStatus
from app.services.communications_service import (
    NO_CONSENT_STATUS,
    CommunicationsService,
    has_sms_consent,
)
from app.services.ussd_application import (
    SMS_OPT_IN_MSG,
    SMS_OPT_OUT_MSG,
    SMS_PREFS_OFF,
    SMS_PREFS_ON,
    USSD_MAIN_MENU,
)


def _membership(db, farmer):
    return db.query(CooperativeMembership).filter(CooperativeMembership.id == farmer["id"]).one()


def _provider(success=True):
    sms = AsyncMock()
    sms.send_sms = AsyncMock(return_value={"success": success, "message": "queued", "raw": {"data": "ref"}})
    sms.send_bulk_sms = AsyncMock(return_value={"success": success, "message": "queued", "provider_ref": "bulk"})
    return sms


# ---------------------------------------------------------------------------
# Schema / defaults
# ---------------------------------------------------------------------------


def test_new_members_default_to_no_consent_and_record_timestamps(client, cooperative):
    silent = client.post(
        "/farmers/",
        json={"name": "No Consent", "phone": "+233551000101", "cooperative_id": cooperative["id"]},
    )
    assert silent.status_code == 201, silent.text
    assert silent.json()["sms_consent"] is False
    assert silent.json()["sms_consent_at"] is None
    assert silent.json()["sms_opt_out_at"] is not None  # explicit "no" is stamped too

    consenting = client.post(
        "/farmers/",
        json={"name": "Consenting", "phone": "+233551000102", "cooperative_id": cooperative["id"], "sms_consent": True},
    )
    assert consenting.status_code == 201, consenting.text
    assert consenting.json()["sms_consent"] is True
    assert consenting.json()["sms_consent_at"] is not None
    assert consenting.json()["sms_opt_out_at"] is None


def test_patch_consent_stamps_and_audits(client, db, cooperative, farmer):
    withdrawn = client.put(f"/farmers/{farmer['id']}", json={"sms_consent": False})
    assert withdrawn.status_code == 200, withdrawn.text
    body = withdrawn.json()
    assert body["sms_consent"] is False
    assert body["sms_opt_out_at"] is not None
    assert body["sms_consent_at"] is not None  # granted at creation, still on record

    regranted = client.put(f"/farmers/{farmer['id']}", json={"sms_consent": True})
    assert regranted.status_code == 200
    assert regranted.json()["sms_consent"] is True
    assert regranted.json()["sms_consent_at"] >= body["sms_consent_at"]


def test_set_sms_consent_is_idempotent_once_stamped(db, farmer):
    membership = _membership(db, farmer)
    assert membership.sms_consent is True
    assert membership.set_sms_consent(True) is False  # already granted and stamped
    assert membership.set_sms_consent(False) is True
    assert membership.sms_opt_out_at is not None
    assert has_sms_consent(membership) is False
    assert has_sms_consent(None) is False


# ---------------------------------------------------------------------------
# Send paths
# ---------------------------------------------------------------------------


def test_single_recipient_paths_skip_opted_out_members_and_log_it(db, farmer):
    membership = _membership(db, farmer)
    membership.set_sms_consent(False)
    db.commit()

    provider = _provider()
    service = CommunicationsService(sms_provider=provider)

    dues = asyncio.run(service.send_dues_reminder(membership, 50.0, "30 June", db, sent_by="admin"))
    confirm = asyncio.run(service.send_payment_confirmation(membership, 50.0, "ref-1", db))
    action = asyncio.run(service.send_payment_action_required(membership, 50.0, "ref-2", db))

    for result in (dues, confirm, action):
        assert result["success"] is False
        assert result["skipped"] is True
        assert result["log_id"] is not None

    provider.send_sms.assert_not_awaited()
    skipped_logs = db.query(CommunicationLog).filter(CommunicationLog.status == NO_CONSENT_STATUS).all()
    assert len(skipped_logs) == 3
    assert all(log.recipients_count == 0 for log in skipped_logs)


def test_loan_rejection_and_reminder_respect_consent(db, farmer):
    membership = _membership(db, farmer)
    membership.set_sms_consent(False)
    loan = Loan(
        farmer_id=membership.id,
        amount=300.0,
        purpose="Inputs",
        status=LoanStatus.disbursed,
        expected_repayment_date=datetime.utcnow(),
    )
    db.add(loan)
    db.commit()

    provider = _provider()
    service = CommunicationsService(sms_provider=provider)

    rejection = asyncio.run(service.send_loan_rejection(loan=loan, farmer=membership, reason="Score too low", db=db))
    assert rejection["skipped"] is True

    reminder = asyncio.run(
        service.send_loan_repayment_reminder(
            loan=loan,
            farmer=membership,
            reminder_kind="due_today",
            scheduled_for=datetime.utcnow().date(),
            db=db,
        )
    )
    assert reminder.status == NO_CONSENT_STATUS
    assert reminder.attempts == 0
    provider.send_sms.assert_not_awaited()


def test_consenting_member_still_receives_sms(db, farmer):
    membership = _membership(db, farmer)
    assert membership.sms_consent is True
    provider = _provider()
    service = CommunicationsService(sms_provider=provider)
    result = asyncio.run(service.send_dues_reminder(membership, 50.0, "30 June", db))
    assert result["success"] is True
    provider.send_sms.assert_awaited_once()


def test_broadcast_excludes_opted_out_members(client, db, cooperative, farmer):
    silent = client.post(
        "/farmers/",
        json={"name": "Silent", "phone": "+233551000103", "cooperative_id": cooperative["id"], "sms_consent": False},
    )
    assert silent.status_code == 201
    provider = _provider()
    service = CommunicationsService(sms_provider=provider)
    result = asyncio.run(service.broadcast_to_cooperative(cooperative["id"], "Meeting", db))
    assert result["recipients_count"] == 1
    recipients = provider.send_bulk_sms.await_args.kwargs["recipients"]
    assert recipients == [farmer["phone"]]


# ---------------------------------------------------------------------------
# USSD self-service
# ---------------------------------------------------------------------------


def _ussd(client, session_id, phone, message, new):
    body = {"sessionId": session_id, "new": new, "msisdn": phone, "network": 3, "message": message, "extension": "109", "data": ""}
    return client.post("/webhooks/moolre/ussd", json=body).json()


def test_ussd_menu_lets_member_opt_out_and_back_in(client, db, cooperative, farmer, growth_plan):
    phone = farmer["phone"]
    assert "8. SMS Alerts" in USSD_MAIN_MENU

    first = _ussd(client, "s-247-1", phone, "", True)
    assert first["message"] == USSD_MAIN_MENU
    prefs = _ussd(client, "s-247-1", phone, "8", False)
    assert prefs["message"] == SMS_PREFS_ON
    done = _ussd(client, "s-247-1", phone, "1", False)
    assert done["message"] == SMS_OPT_OUT_MSG
    assert done["reply"] is False

    membership = _membership(db, farmer)
    db.refresh(membership)
    assert membership.sms_consent is False
    assert membership.sms_opt_out_at is not None
    audit = (
        db.query(AdminAuditLog)
        .filter(AdminAuditLog.action == "member.sms_consent_withdrawn", AdminAuditLog.resource_id == str(membership.id))
        .one()
    )
    assert audit.actor_id == f"ussd:{phone}"

    _ussd(client, "s-247-2", phone, "", True)
    prefs_off = _ussd(client, "s-247-2", phone, "8", False)
    assert prefs_off["message"] == SMS_PREFS_OFF
    back = _ussd(client, "s-247-2", phone, "1", False)
    assert back["message"] == SMS_OPT_IN_MSG
    db.refresh(membership)
    assert membership.sms_consent is True
