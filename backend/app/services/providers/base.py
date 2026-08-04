"""Abstract provider ports for payment and SMS operations."""
from abc import ABC, abstractmethod
from typing import Any

class PaymentProvider(ABC):
    """Port for payment operations (collections, disbursements, transfers)."""
    
    @abstractmethod
    async def initiate_payment(self, *, payer_phone: str, amount: str, reference: str, channel: str = "13", otp_code: str | None = None) -> dict:
        """Initiate a mobile money payment push. Returns dict with outcome field."""
        ...
    
    @abstractmethod
    async def payment_status(self, external_ref: str) -> dict:
        """Check status of a previously initiated payment."""
        ...
    
    @abstractmethod
    async def initiate_transfer(self, *, receiver_phone: str, amount: float, reference: str) -> dict:
        """Disburse funds to a mobile money wallet."""
        ...
    
    @abstractmethod
    async def create_account(self, *, account_name: str) -> dict:
        """Create a sub-wallet/account. Returns dict with success + account_number."""
        ...
    
    @abstractmethod
    async def internal_transfer(self, *, from_account: str, to_account: str, amount: float, reference: str) -> dict:
        """Internal wallet-to-wallet transfer."""
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
