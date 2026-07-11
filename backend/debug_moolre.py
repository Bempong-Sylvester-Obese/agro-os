import asyncio
from pprint import pprint

from app.services.moolre_service import MoolreService

async def test_moolre():
    moolre = MoolreService()
    
    payload = {"type": 1, "accountnumber": moolre.settings.moolre_account_number}
    print("Testing payload:", payload)
    raw = await moolre._post("/open/account/status", payload)
    print("\n--- RAW RESPONSE FROM MOOLRE ---")
    pprint(raw)
    print("--------------------------------\n")

if __name__ == "__main__":
    asyncio.run(test_moolre())
