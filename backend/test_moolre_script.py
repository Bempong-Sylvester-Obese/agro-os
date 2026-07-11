import asyncio
from pprint import pprint

from app.services.moolre_service import MoolreService
from app.config import get_settings

async def test_moolre():
    settings = get_settings()
    print("--- Moolre Configuration ---")
    print(f"API URL: {settings.moolre_api_url}")
    print(f"API USER: {settings.moolre_api_user}")
    print(f"ACCOUNT NUMBER: {settings.moolre_account_number}")
    print("----------------------------\n")
    
    moolre = MoolreService()
    
    print("1. Testing Wallet Balance...")
    balance_result = await moolre.account_status()
    pprint(balance_result)
    print("\n")
    
    print("2. Testing Payment Push (Dues Collect)...")
    payment_result = await moolre.initiate_payment(
        payer_phone="0551234567",  # Dummy test number
        amount=1.00,
        currency="GHS",
        channel="13",  # MTN
        reference="Test Payment Push"
    )
    pprint(payment_result)
    print("\n")

    if payment_result.get("verification_required"):
        otp = input("Enter the OTP received on the phone: ")
        print(f"Retrying payment push with OTP: {otp}...")
        retry_result = await moolre.initiate_payment(
            payer_phone="0551234567",
            amount=1.00,
            currency="GHS",
            channel="13",
            reference="Test Payment Push",
            external_ref=payment_result.get("external_ref"),
            otpcode=otp,
        )
        pprint(retry_result)
        print("\n")

if __name__ == "__main__":
    asyncio.run(test_moolre())
