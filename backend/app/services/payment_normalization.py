"""Webhook payload normalization — converts provider-specific payloads to PaymentEvent."""
import logging
from typing import Any

from app.domain.payment_event import PaymentEvent

logger = logging.getLogger(__name__)


def normalize_moolre_payload(raw: dict) -> PaymentEvent:
    """Normalize a Moolre webhook payload into a PaymentEvent."""
    status_code = raw.get("status", 0)
    data = raw.get("data") or {}

    external_ref = data.get("externalref") or raw.get("reference")
    transaction_id = data.get("transactionid")
    amount_raw = data.get("amount") or data.get("value", "0")

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0.0

    status = "success" if status_code == 1 else "failed"
    event_type = f"payment.{status}"

    return PaymentEvent(
        provider="moolre",
        event_type=event_type,
        external_ref=external_ref or str(transaction_id) if transaction_id else "",
        amount=amount,
        currency="GHS",
        status=status,
        payer_phone=data.get("payer"),
        metadata={"raw": raw, "status_code": status_code},
    )


def normalize_fidelity_payload(raw: dict) -> PaymentEvent:
    """Normalize a Fidelity Bank webhook payload into a PaymentEvent."""
    status_str = raw.get("status", "").lower()
    external_ref = raw.get("reference") or raw.get("transaction_id", "")
    amount_raw = raw.get("amount", "0")

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0.0

    status = "success" if status_str in ("success", "completed", "successful") else "failed"
    event_type = f"payment.{status}"

    return PaymentEvent(
        provider="fidelity",
        event_type=event_type,
        external_ref=external_ref,
        amount=amount,
        currency=raw.get("currency", "GHS"),
        status=status,
        payer_phone=raw.get("payer_phone") or raw.get("phone"),
        metadata={"raw": raw},
    )


def normalize_payload(provider: str, raw: dict) -> PaymentEvent:
    """Route to the correct normalizer based on provider."""
    normalizers = {
        "moolre": normalize_moolre_payload,
        "fidelity": normalize_fidelity_payload,
    }
    normalizer = normalizers.get(provider)
    if not normalizer:
        raise ValueError(f"Unknown payment provider: {provider}")
    return normalizer(raw)
