"""Abstract provider ports for payment and SMS operations."""
from abc import ABC, abstractmethod
from typing import Any


class PaymentProvider(ABC):
    """Port for payment operations (collections, disbursements, transfers)."""

    @abstractmethod
    async def initiate_payment(self, *, payer_phone: str, amount: str, currency: str = "GHS", channel: str = "13", external_ref: str = "", otpcode: str | None = None, reference: str = "", account_number: str | None = None) -> dict:
        """Initiate a mobile money payment push. Returns dict with success/outcome."""
        ...

    @abstractmethod
    async def initiate_transfer(self, *, receiver_phone: str, amount: float, currency: str = "GHS", external_ref: str = "", reference: str = "", account_number: str | None = None) -> dict:
        """Disburse funds to a mobile money wallet."""
        ...

    @abstractmethod
    async def payment_status(self, external_ref: str, account_number: str | None = None, id_type: str = "1") -> dict:
        """Check status of a previously initiated payment."""
        ...

    @abstractmethod
    async def transfer_status(self, reference: str, account_number: str | None = None, id_type: str = "2") -> dict:
        """Check status of a transfer/disbursement."""
        ...

    @abstractmethod
    async def create_account(self, *, account_name: str) -> dict:
        """Create a sub-wallet/account."""
        ...

    @abstractmethod
    async def internal_transfer(self, *, from_account: str, to_account: str, amount: float, reference: str) -> dict:
        """Internal wallet-to-wallet transfer."""
        ...

    @abstractmethod
    async def resolve_verified_account(self, cooperative_id: int | None = None) -> tuple[str | None, str | None]:
        """Resolve a verified payout account number. Returns (account_number_or_None, error_message_or_None)."""
        ...

    @abstractmethod
    async def generate_payment_link(self, *, amount: float, description: str, redirect_url: str, external_ref: str) -> dict:
        """Generate a hosted payment link. Returns dict with url."""
        ...

    @abstractmethod
    async def account_status(self, account_number: str) -> dict:
        """Get wallet/account balance and status."""
        ...

    @abstractmethod
    def resolve_account_number(self, cooperative_account: str | None = None) -> str:
        """Resolve the account number to use (cooperative wallet or global fallback)."""
        ...

    @abstractmethod
    async def list_transactions(self, account_number: str | None = None, start_date: str | None = None, end_date: str | None = None, limit: int = 50, status: str | None = None) -> dict:
        """List account transactions from the provider."""
        ...


class SmsProvider(ABC):
    """Port for SMS operations."""

    @abstractmethod
    async def send_sms(self, *, recipient: str, message: str) -> dict:
        """Send a single SMS."""
        ...

    @abstractmethod
    async def send_bulk_sms(self, *, recipients: list[str], message: str) -> dict:
        """Send SMS to multiple recipients."""
        ...

    @abstractmethod
    async def diagnose_sms(self, recipient: str) -> dict:
        """Run SMS connectivity diagnostics for a recipient."""
        ...
