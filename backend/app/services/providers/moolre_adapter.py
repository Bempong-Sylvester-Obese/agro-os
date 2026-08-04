"""Moolre adapter implementing PaymentProvider and SmsProvider ports."""
from app.services.moolre_service import MoolreService
from app.services.providers.base import PaymentProvider, SmsProvider

class MoolrePaymentAdapter(PaymentProvider):
    def __init__(self):
        self._service = MoolreService()
    
    async def initiate_payment(self, **kwargs):
        return await self._service.initiate_payment(
            payer_phone=kwargs['payer_phone'],
            amount=kwargs['amount'],
            reference=kwargs['reference'],
            channel=kwargs.get('channel', '13'),
            otp_code=kwargs.get('otp_code'),
        )
    
    async def payment_status(self, external_ref):
        return self._service.payment_status(external_ref)
    
    async def initiate_transfer(self, **kwargs):
        return await self._service.initiate_transfer(
            receiver_phone=kwargs['receiver_phone'],
            amount=kwargs['amount'],
            reference=kwargs['reference'],
        )
    
    async def create_account(self, **kwargs):
        return await self._service.create_account(account_name=kwargs['account_name'])
    
    async def internal_transfer(self, **kwargs):
        return await self._service.internal_transfer(
            from_account=kwargs['from_account'],
            to_account=kwargs['to_account'],
            amount=kwargs['amount'],
            reference=kwargs['reference'],
        )

class MoolreSmsAdapter(SmsProvider):
    def __init__(self):
        self._service = MoolreService()
    
    async def send_sms(self, **kwargs):
        return await self._service.send_single_sms(
            recipient=kwargs['recipient'],
            message=kwargs['message'],
        )
    
    async def send_bulk_sms(self, **kwargs):
        return await self._service.send_sms(
            recipients=kwargs['recipients'],
            message=kwargs['message'],
        )
