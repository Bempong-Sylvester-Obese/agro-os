"""Provider factory — returns the configured payment/SMS/email adapters.

To swap providers, change the classes returned here. All consumers
depend on this factory, not on concrete provider implementations.
"""
from app.config import get_settings
from app.services.providers.base import EmailProvider, PaymentProvider, SmsProvider
from app.services.providers.email_adapters import LoggingEmailAdapter, SmtpEmailAdapter
from app.services.providers.moolre_adapter import MoolrePaymentAdapter, MoolreSmsAdapter

_payment_provider: PaymentProvider | None = None
_sms_provider: SmsProvider | None = None
_email_provider: EmailProvider | None = None


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


def get_email_provider() -> EmailProvider:
    """Staff email (invites / resets). ``EMAIL_PROVIDER=smtp`` selects the SMTP
    adapter; anything else falls back to the logging adapter (#248)."""
    global _email_provider
    if _email_provider is None:
        if get_settings().email_provider.strip().lower() == "smtp":
            _email_provider = SmtpEmailAdapter()
        else:
            _email_provider = LoggingEmailAdapter()
    return _email_provider


def reset_providers() -> None:
    """Reset singletons (for testing only)."""
    global _payment_provider, _sms_provider, _email_provider
    _payment_provider = None
    _sms_provider = None
    _email_provider = None
