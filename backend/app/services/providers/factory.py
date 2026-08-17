"""Provider factory — returns the configured payment/SMS adapters.

To swap providers, change the classes returned here. All consumers
depend on this factory, not on concrete provider implementations.
"""
from app.services.providers.base import PaymentProvider, SmsProvider
from app.services.providers.moolre_adapter import MoolrePaymentAdapter, MoolreSmsAdapter

_payment_provider: PaymentProvider | None = None
_sms_provider: SmsProvider | None = None


def get_payment_provider() -> PaymentProvider:
    global _payment_provider
    if _payment_provider is None:
        _payment_provider = MoolrePaymentAdapter()
    return _payment_provider


def get_sms_provider() -> SmsProvider:
    global _sms_provider
    if _sms_provider is None:
        _sms_provider = MoolreSmsAdapter()
    return _sms_provider


def reset_providers() -> None:
    """Reset singletons (for testing only)."""
    global _payment_provider, _sms_provider
    _payment_provider = None
    _sms_provider = None
