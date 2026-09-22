"""Unit tests for provider payload -> PaymentEvent normalization."""
import pytest

from app.domain.payment_event import PaymentEvent
from app.services.payment_normalization import (
    normalize_fidelity_payload,
    normalize_moolre_payload,
    normalize_payload,
)


def _moolre(status=1, **data):
    return {"status": status, "code": "P01", "message": "ok", "data": data}


def test_moolre_success_payload_is_normalized():
    event = normalize_moolre_payload(
        _moolre(externalref="dues-123", transactionid="MOOLRE-999", amount="25.50", payer="233551300186")
    )

    assert isinstance(event, PaymentEvent)
    assert event.provider == "moolre"
    assert event.status == "success"
    assert event.is_success
    assert event.event_type == "payment.success"
    assert event.external_ref == "dues-123"
    assert event.provider_transaction_id == "MOOLRE-999"
    assert event.amount == pytest.approx(25.5)
    assert event.currency == "GHS"
    assert event.payer_phone == "233551300186"
    assert event.metadata["status_code"] == 1
    assert event.metadata["raw"]["data"]["externalref"] == "dues-123"


def test_moolre_non_success_status_maps_to_failed():
    event = normalize_moolre_payload(_moolre(status=0, externalref="dues-1", amount="10"))
    assert event.status == "failed"
    assert not event.is_success
    assert event.event_type == "payment.failed"


def test_moolre_keeps_external_ref_when_transaction_id_is_absent():
    event = normalize_moolre_payload(_moolre(externalref="only-our-ref", amount="5"))
    assert event.external_ref == "only-our-ref"
    assert event.provider_transaction_id is None
    assert event.reference == "only-our-ref"


def test_moolre_falls_back_to_provider_transaction_id_for_reference():
    event = normalize_moolre_payload(_moolre(transactionid=4242, amount="5"))
    assert event.external_ref == ""
    assert event.provider_transaction_id == "4242"
    assert event.reference == "4242"


def test_moolre_uses_value_when_amount_missing_and_tolerates_bad_numbers():
    assert normalize_moolre_payload(_moolre(externalref="a", value="12.25")).amount == pytest.approx(12.25)
    assert normalize_moolre_payload(_moolre(externalref="a", amount="not-a-number")).amount == 0.0
    assert normalize_moolre_payload(_moolre(externalref="a")).amount == 0.0


@pytest.mark.parametrize("payload", [{}, {"status": 1}, {"status": 1, "data": None}, {"data": "junk"}, None])
def test_moolre_malformed_payloads_do_not_raise(payload):
    event = normalize_moolre_payload(payload)
    assert event.external_ref == ""
    assert event.status in {"success", "failed"}
    assert event.amount == 0.0


def test_idempotency_key_is_stable_across_duplicate_deliveries():
    first = normalize_moolre_payload(_moolre(externalref="dues-77", transactionid="T1", amount="10"))
    second = normalize_moolre_payload(_moolre(externalref="dues-77", transactionid="T1", amount="10"))
    assert first.idempotency_key == second.idempotency_key == "moolre:dues-77"


def test_idempotency_key_prefers_our_reference_over_provider_id():
    ours = normalize_moolre_payload(_moolre(externalref="ours", transactionid="theirs"))
    theirs_only = normalize_moolre_payload(_moolre(transactionid="theirs"))
    assert ours.idempotency_key == "moolre:ours"
    assert theirs_only.idempotency_key == "moolre:theirs"


def test_fidelity_payload_is_normalized():
    event = normalize_fidelity_payload(
        {"status": "COMPLETED", "reference": "ref-1", "transaction_id": "FID-1", "amount": "40", "currency": "GHS", "phone": "233200000000"}
    )
    assert event.provider == "fidelity"
    assert event.is_success
    assert event.external_ref == "ref-1"
    assert event.provider_transaction_id == "FID-1"
    assert event.amount == 40.0
    assert event.payer_phone == "233200000000"


def test_normalize_payload_routes_by_provider_and_rejects_unknown():
    event = normalize_payload("moolre", _moolre(externalref="x", amount="1"))
    assert event.provider == "moolre"
    with pytest.raises(ValueError):
        normalize_payload("unknown-bank", {})
