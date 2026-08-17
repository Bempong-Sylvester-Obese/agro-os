"""Moolre adapter implementing PaymentProvider and SmsProvider ports."""
from app.services.moolre_service import MoolreService
from app.services.providers.base import PaymentProvider, SmsProvider


class MoolrePaymentAdapter(PaymentProvider):
    def __init__(self):
        self._service = MoolreService()

    async def initiate_payment(
        self,
        *,
        payer_phone: str,
        amount: float,
        currency: str = "GHS",
        channel: str = "13",
        external_ref: str | None = None,
        otpcode: str | None = None,
        reference: str = "Cooperative dues",
        account_number: str | None = None,
    ) -> dict:
        return await self._service.initiate_payment(
            payer_phone=payer_phone,
            amount=amount,
            currency=currency,
            channel=channel,
            external_ref=external_ref,
            otpcode=otpcode,
            reference=reference,
            account_number=account_number,
        )

    async def initiate_transfer(
        self,
        *,
        receiver_phone: str,
        amount: float,
        currency: str = "GHS",
        channel: str | None = None,
        external_ref: str | None = None,
        reference: str = "Loan disbursement",
        account_number: str | None = None,
    ) -> dict:
        return await self._service.initiate_transfer(
            receiver_phone=receiver_phone,
            amount=amount,
            currency=currency,
            channel=channel,
            external_ref=external_ref,
            reference=reference,
            account_number=account_number,
        )

    async def payment_status(
        self, external_ref: str, account_number: str | None = None
    ) -> dict:
        return await self._service.payment_status(
            external_ref=external_ref,
            account_number=account_number,
        )

    async def transfer_status(
        self,
        reference: str,
        account_number: str | None = None,
        id_type: str = "1",
    ) -> dict:
        return await self._service.transfer_status(
            reference=reference,
            account_number=account_number,
            id_type=id_type,
        )

    async def create_account(
        self,
        *,
        account_name: str,
        currency: str = "GHS",
        api: int = 1,
        callback: str | None = None,
    ) -> dict:
        return await self._service.create_account(
            account_name=account_name,
            currency=currency,
            api=api,
            callback=callback,
        )

    async def internal_transfer(
        self,
        *,
        receiver_account: str,
        amount: float,
        currency: str = "GHS",
        external_ref: str | None = None,
        reference: str = "Internal Transfer",
        from_account_number: str | None = None,
    ) -> dict:
        return await self._service.internal_transfer(
            receiver_account=receiver_account,
            amount=amount,
            currency=currency,
            external_ref=external_ref,
            reference=reference,
            from_account_number=from_account_number,
        )

    async def resolve_verified_account(
        self, cooperative_id: int | None = None
    ) -> tuple[str | None, str | None]:
        return await self._service.resolve_verified_account(cooperative_id)

    async def generate_payment_link(
        self,
        *,
        amount: float,
        email: str,
        currency: str = "GHS",
        external_ref: str | None = None,
        callback_url: str | None = None,
        redirect_url: str | None = None,
        reusable: bool = False,
        expiration_minutes: int = 60,
        account_number: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        return await self._service.generate_payment_link(
            amount=amount,
            email=email,
            currency=currency,
            external_ref=external_ref,
            callback_url=callback_url,
            redirect_url=redirect_url,
            reusable=reusable,
            expiration_minutes=expiration_minutes,
            account_number=account_number,
            metadata=metadata,
        )

    async def account_status(self, account_number: str | None = None) -> dict:
        return await self._service.account_status(account_number)

    def resolve_account_number(self, cooperative_account: str | None = None) -> str:
        return self._service.resolve_account_number(cooperative_account)

    async def list_transactions(
        self,
        account_number: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        status: str | None = None,
    ) -> dict:
        return await self._service.list_transactions(
            account_number=account_number,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            status=status,
        )


class MoolreSmsAdapter(SmsProvider):
    def __init__(self):
        self._service = MoolreService()

    async def send_sms(self, *, recipient: str, message: str) -> dict:
        return await self._service.send_single_sms(
            phone=recipient,
            message=message,
        )

    async def send_bulk_sms(
        self, *, recipients: list[str], message: str
    ) -> dict:
        return await self._service.send_sms(
            recipients=[
                {"recipient": recipient, "message": message}
                for recipient in recipients
            ],
        )

    async def diagnose_sms(self) -> dict:
        return await self._service.diagnose_sms()
