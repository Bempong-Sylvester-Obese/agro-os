"""Domain-level payment event, normalized from provider-specific webhook payloads."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PaymentEvent:
    provider: str  # "moolre"
    event_type: str  # "payment.success", "payment.failed", "ussd.callback"
    external_ref: str  # our reference echoed back by the provider
    amount: float | None = None
    currency: str = "GHS"
    status: str = "unknown"  # "success", "failed", "pending"
    payer_phone: str | None = None
    provider_transaction_id: str | None = None  # provider-side transaction id, if any
    signature_valid: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def reference(self) -> str:
        """Best available reference for ledger lookups (ours first, provider's second)."""
        return self.external_ref or (self.provider_transaction_id or "")

    @property
    def idempotency_key(self) -> str:
        """Stable key identifying this payment across duplicate deliveries."""
        return f"{self.provider}:{self.reference}"
