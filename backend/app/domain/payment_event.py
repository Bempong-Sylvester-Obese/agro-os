"""Domain-level payment event, normalized from provider-specific webhook payloads."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PaymentEvent:
    provider: str  # "moolre"
    event_type: str  # "payment.success", "payment.failed", "ussd.callback"
    external_ref: str  # provider's transaction reference
    amount: float | None = None
    currency: str = "GHS"
    status: str = "unknown"  # "success", "failed", "pending"
    payer_phone: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
