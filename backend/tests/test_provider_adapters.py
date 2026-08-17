import inspect
from unittest.mock import AsyncMock

import pytest

from app.services.providers.moolre_adapter import (
    MoolrePaymentAdapter,
    MoolreSmsAdapter,
)
from app.services.providers.base import PaymentProvider, SmsProvider


def test_adapter_signatures_match_provider_ports() -> None:
    for method_name in PaymentProvider.__abstractmethods__:
        assert inspect.signature(
            getattr(MoolrePaymentAdapter, method_name)
        ) == inspect.signature(getattr(PaymentProvider, method_name))
    for method_name in SmsProvider.__abstractmethods__:
        assert inspect.signature(
            getattr(MoolreSmsAdapter, method_name)
        ) == inspect.signature(getattr(SmsProvider, method_name))


@pytest.mark.asyncio
async def test_payment_adapter_forwards_typed_contract() -> None:
    adapter = MoolrePaymentAdapter()
    adapter._service.payment_status = AsyncMock(return_value={"status": "completed"})
    adapter._service.create_account = AsyncMock(return_value={"success": True})
    adapter._service.internal_transfer = AsyncMock(return_value={"success": True})

    status = await adapter.payment_status("payment-ref", "COOP-1")
    await adapter.create_account(account_name="Farm", currency="USD")
    await adapter.internal_transfer(
        receiver_account="MASTER",
        from_account_number="COOP-1",
        amount=2.5,
        currency="GHS",
        reference="fee",
    )

    assert status == {"status": "completed"}
    adapter._service.payment_status.assert_awaited_once_with(
        external_ref="payment-ref",
        account_number="COOP-1",
    )
    adapter._service.create_account.assert_awaited_once_with(
        account_name="Farm",
        currency="USD",
        api=1,
        callback=None,
    )
    adapter._service.internal_transfer.assert_awaited_once_with(
        receiver_account="MASTER",
        amount=2.5,
        currency="GHS",
        external_ref=None,
        reference="fee",
        from_account_number="COOP-1",
    )


@pytest.mark.asyncio
async def test_sms_adapter_translates_bulk_and_diagnostics_contracts() -> None:
    adapter = MoolreSmsAdapter()
    adapter._service.send_sms = AsyncMock(return_value={"success": True})
    adapter._service.diagnose_sms = AsyncMock(return_value={"ok": True})

    await adapter.send_bulk_sms(
        recipients=["+233200000001", "+233200000002"],
        message="Harvest ready",
    )
    diagnostics = await adapter.diagnose_sms()

    adapter._service.send_sms.assert_awaited_once_with(
        recipients=[
            {"recipient": "+233200000001", "message": "Harvest ready"},
            {"recipient": "+233200000002", "message": "Harvest ready"},
        ]
    )
    adapter._service.diagnose_sms.assert_awaited_once_with()
    assert diagnostics == {"ok": True}
