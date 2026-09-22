"""Webhook payload normalization — converts provider-specific payloads to PaymentEvent."""
import logging
from typing import Any

from app.domain.payment_event import PaymentEvent

logger = logging.getLogger(__name__)


def _coerce_amount(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_moolre_payload(raw: dict) -> PaymentEvent:
    """Normalize a Moolre webhook payload into a PaymentEvent.

    This is the only place in the codebase that knows the shape of a Moolre
    payment webhook (``status`` code, ``data.externalref``, ``data.transactionid``,
    ``data.amount`` / ``data.value``, ``data.payer``).
    """
    if not isinstance(raw, dict):
        raw = {}
    status_code = raw.get("status", 0)
    data = raw.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    external_ref = data.get("externalref") or raw.get("reference") or ""
    transaction_id = data.get("transactionid")
    amount = _coerce_amount(data.get("amount") or data.get("value", "0"))

    status = "success" if status_code == 1 else "failed"

    return PaymentEvent(
        provider="moolre",
        event_type=f"payment.{status}",
        external_ref=str(external_ref) if external_ref else "",
        amount=amount,
        currency=str(data.get("currency") or "GHS"),
        status=status,
        payer_phone=data.get("payer"),
        provider_transaction_id=str(transaction_id) if transaction_id else None,
        metadata={"raw": raw, "status_code": status_code},
    )


def normalize_fidelity_payload(raw: dict) -> PaymentEvent:
    """Normalize a Fidelity Bank webhook payload into a PaymentEvent."""
    status_str = raw.get("status", "").lower()
    external_ref = raw.get("reference") or raw.get("transaction_id", "")
    amount = _coerce_amount(raw.get("amount", "0"))

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
        provider_transaction_id=raw.get("transaction_id"),
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
