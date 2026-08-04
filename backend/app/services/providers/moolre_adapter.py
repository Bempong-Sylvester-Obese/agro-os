"""Moolre adapter implementing PaymentProvider and SmsProvider ports."""
from app.services.moolre_service import MoolreService
from app.services.providers.base import PaymentProvider, SmsProvider


class MoolrePaymentAdapter(PaymentProvider):
    def __init__(self):
        self._service = MoolreService()

    async def initiate_payment(self, **kwargs):
        return await self._service.initiate_payment(
            payer_phone=kwargs["payer_phone"],
            amount=kwargs["amount"],
            currency=kwargs.get("currency", "GHS"),
            channel=kwargs.get("channel", "13"),
            external_ref=kwargs.get("external_ref", ""),
            otpcode=kwargs.get("otpcode"),
            reference=kwargs.get("reference", ""),
            account_number=kwargs.get("account_number"),
        )

    async def initiate_transfer(self, **kwargs):
        return await self._service.initiate_transfer(
            receiver_phone=kwargs["receiver_phone"],
            amount=kwargs["amount"],
            currency=kwargs.get("currency", "GHS"),
            external_ref=kwargs.get("external_ref", ""),
            reference=kwargs.get("reference", ""),
            account_number=kwargs.get("account_number"),
        )

    async def payment_status(self, external_ref, account_number=None, id_type="1"):
        return self._service.payment_status(
            external_ref=external_ref,
            account_number=account_number,
            id_type=id_type,
        )

    async def transfer_status(self, reference, account_number=None, id_type="2"):
        return await self._service.transfer_status(
            reference=reference,
            account_number=account_number,
            id_type=id_type,
        )

    async def create_account(self, **kwargs):
        return await self._service.create_account(account_name=kwargs["account_name"])

    async def internal_transfer(self, **kwargs):
        return await self._service.internal_transfer(
            from_account=kwargs["from_account"],
            to_account=kwargs["to_account"],
            amount=kwargs["amount"],
            reference=kwargs["reference"],
        )

    async def resolve_verified_account(self, cooperative_id=None):
        return await self._service.resolve_verified_account(cooperative_id)

    async def generate_payment_link(self, **kwargs):
        return await self._service.generate_payment_link(
            amount=kwargs["amount"],
            description=kwargs["description"],
            redirect_url=kwargs["redirect_url"],
            external_ref=kwargs["external_ref"],
        )

    async def account_status(self, account_number):
        return await self._service.account_status(account_number)


class MoolreSmsAdapter(SmsProvider):
    def __init__(self):
        self._service = MoolreService()

    async def send_sms(self, **kwargs):
        return await self._service.send_single_sms(
            recipient=kwargs["recipient"],
            message=kwargs["message"],
        )

    async def send_bulk_sms(self, **kwargs):
        return await self._service.send_sms(
            recipients=kwargs["recipients"],
            message=kwargs["message"],
        )

    async def diagnose_sms(self, recipient):
        return await self._service.diagnose_sms(recipient)
