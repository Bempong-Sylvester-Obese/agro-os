"""
Moolre API Integration Service

Covers all MVP-relevant Moolre endpoints:
  - Initiate Payment (USSD push / dues collection)
  - Payment Status
  - Initiate Transfer (loan disbursement / payout)
  - Transfer Status
  - List Account Transactions
  - Account Status (wallet balance)
  - Send SMS (bulk / single)
  - Generate Payment Link
"""

import uuid
from typing import Any

import httpx

from app.config import get_settings


class MoolreService:
    """Handle all server-side Moolre API communications."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.moolre_api_url.rstrip("/")
        self._base_headers = self._build_base_headers()

    # ------------------------------------------------------------------
    # Header helpers
    # ------------------------------------------------------------------

    def _build_base_headers(self) -> dict:
        """Build headers that every request needs."""
        headers: dict = {
            "Content-Type": "application/json",
            "X-API-USER": self.settings.moolre_api_user,
        }
        if self.settings.moolre_api_key:
            headers["X-API-KEY"] = self.settings.moolre_api_key
        if self.settings.moolre_env == "live" and self.settings.moolre_api_pubkey:
            headers["X-API-PUBKEY"] = self.settings.moolre_api_pubkey
        return headers

    def _vaskey_headers(self) -> dict:
        """Build headers specifically for VAS endpoints like SMS."""
        headers = self._build_base_headers()
        if self.settings.moolre_api_vaskey:
            headers["X-API-VASKEY"] = self.settings.moolre_api_vaskey
        return headers



    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    async def _post(self, path: str, payload: dict, headers: dict | None = None) -> dict:
        h = headers or self._base_headers
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(f"{self.base_url}{path}", json=payload, headers=h)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                return {
                    "success": False,
                    "error": str(exc),
                    "status_code": exc.response.status_code,
                }
            except httpx.RequestError as exc:
                return {"success": False, "error": str(exc)}

    async def _get(self, path: str, params: dict | None = None, headers: dict | None = None) -> dict:
        h = headers or self._base_headers
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(f"{self.base_url}{path}", params=params, headers=h)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                return {
                    "success": False,
                    "error": str(exc),
                    "status_code": exc.response.status_code,
                }
            except httpx.RequestError as exc:
                return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Payments — collect dues via USSD push
    # ------------------------------------------------------------------

    async def initiate_payment(
        self,
        payer_phone: str,
        amount: float,
        currency: str = "GHS",
        channel: str = "13",
        external_ref: str | None = None,
        reference: str = "Cooperative dues",
        account_number: str | None = None,
        otp_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Trigger a USSD payment prompt on the payer's phone.

        channel codes: 13=MTN Ghana, 6=Telecel, 7=AT
        Returns a normalised dict with ``success``, ``outcome``, ``moolre_code``,
        ``moolre_reference``, and ``message``.

        Moolre codes:
          - TR099: USSD push sent (success)
          - TP14: OTP SMS sent; retry with same externalref + otpcode
        """
        ext_ref = external_ref or str(uuid.uuid4())
        acc = account_number or self.settings.moolre_account_number

        payload = {
            "type": 1,
            "channel": channel,
            "currency": currency,
            "payer": payer_phone,
            "amount": str(amount),
            "externalref": ext_ref,
            "reference": reference,
            "accountnumber": acc,
        }
        if otp_code:
            payload["otpcode"] = otp_code

        raw = await self._post("/open/transact/payment", payload)

        if raw.get("success") is False:
            return {
                "success": False,
                "outcome": "failed",
                "moolre_code": None,
                "moolre_reference": ext_ref,
                "external_ref": ext_ref,
                "message": raw.get("error", "Moolre request failed"),
                "raw": raw,
            }

        code = raw.get("code", "")
        if code == "TR099":
            outcome = "push_sent"
        elif code == "TP14":
            outcome = "verification_required"
        else:
            outcome = "failed"

        success = outcome == "push_sent"
        message = raw.get("message") or raw.get("error", "")
        if isinstance(message, list):
            message = " ".join(message)

        return {
            "success": success,
            "outcome": outcome,
            "moolre_code": code or None,
            "moolre_reference": raw.get("data") or ext_ref,
            "external_ref": ext_ref,
            "message": str(message),
            "raw": raw,
        }

    async def payment_status(
        self,
        external_ref: str,
        account_number: str | None = None,
    ) -> dict[str, Any]:
        """Check the status of a previously initiated payment."""
        acc = account_number or self.settings.moolre_account_number
        payload = {
            "type": 1,
            "idtype": "1",  # 1 = externalref
            "id": external_ref,
            "accountnumber": acc,
        }
        raw = await self._post("/open/transact/status", payload)
        tx_data = raw.get("data", {}) or {}
        # txstatus: 1=Success, 0=Pending, 2=Failed
        tx_status_map = {1: "completed", 0: "pending", 2: "failed"}
        tx_status = tx_status_map.get(tx_data.get("txstatus"), "pending")
        return {
            "success": tx_data.get("txstatus") == 1,
            "status": tx_status,
            "transaction_id": tx_data.get("transactionid"),
            "amount": tx_data.get("amount"),
            "raw": raw,
        }

    # ------------------------------------------------------------------
    # Transfers — loan disbursement / payout
    # ------------------------------------------------------------------

    async def initiate_transfer(
        self,
        receiver_phone: str,
        amount: float,
        currency: str = "GHS",
        channel: str = "1",
        external_ref: str | None = None,
        reference: str = "Loan disbursement",
        account_number: str | None = None,
    ) -> dict[str, Any]:
        """
        Send money to a mobile money account (bulk disbursement).

        channel codes: 1=MTN, 6=Telecel, 7=AT, 2=Instant Bank Transfer
        """
        ext_ref = external_ref or str(uuid.uuid4())
        acc = account_number or self.settings.moolre_account_number

        payload = {
            "type": 1,
            "channel": channel,
            "currency": currency,
            "amount": str(amount),
            "receiver": receiver_phone,
            "externalref": ext_ref,
            "reference": reference,
            "accountnumber": acc,
        }

        raw = await self._post("/open/transact/transfer", payload)
        success = raw.get("status") in (1, "1") or raw.get("code", "").startswith("OBGH")
        tx_data = raw.get("data", {}) or {}
        return {
            "success": success,
            "moolre_transfer_ref": tx_data.get("transactionid") or ext_ref,
            "external_ref": ext_ref,
            "message": (
                " ".join(raw["message"]) if isinstance(raw.get("message"), list) else str(raw.get("message", ""))
            ),
            "raw": raw,
        }

    async def transfer_status(
        self,
        external_ref: str,
        account_number: str | None = None,
    ) -> dict[str, Any]:
        """Check the status of a transfer."""
        acc = account_number or self.settings.moolre_account_number
        payload = {
            "type": 1,
            "idtype": "1",
            "id": external_ref,
            "accountnumber": acc,
        }
        raw = await self._post("/open/transact/status", payload)
        tx_data = raw.get("data", {}) or {}
        tx_status_map = {1: "completed", 0: "pending", 2: "failed"}
        tx_status = tx_status_map.get(tx_data.get("txstatus"), "pending")
        return {
            "success": tx_data.get("txstatus") == 1,
            "status": tx_status,
            "transaction_id": tx_data.get("transactionid"),
            "amount": tx_data.get("amount"),
            "raw": raw,
        }

    # ------------------------------------------------------------------
    # Account / Wallet
    # ------------------------------------------------------------------

    async def account_status(self, account_number: str | None = None) -> dict[str, Any]:
        """Check wallet balance."""
        acc = account_number or self.settings.moolre_account_number
        payload = {"type": 1, "accountnumber": acc}
        raw = await self._post("/open/account/status", payload)
        wallet_data = raw.get("data", {})
        if not isinstance(wallet_data, dict):
            wallet_data = {}
        return {
            "success": raw.get("status") in (1, "1"),
            "balance": wallet_data.get("balance"),
            "account_name": wallet_data.get("accountname"),
            "raw": raw,
        }

    async def list_transactions(
        self,
        account_number: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List account transactions from Moolre (for finance dashboard sync)."""
        acc = account_number or self.settings.moolre_account_number
        payload: dict = {"type": 2, "accountnumber": acc, "limit": str(limit)}
        if start_date:
            payload["startdate"] = start_date
        if end_date:
            payload["enddate"] = end_date
        if status is not None:
            payload["status"] = status
        raw = await self._post("/open/account/status", payload)
        tx_data = raw.get("data", {}) or {}
        return {
            "success": raw.get("status") in (1, "1"),
            "tx_count": tx_data.get("txcount", 0),
            "transactions": tx_data.get("transactions", []),
            "raw": raw,
        }

    # ------------------------------------------------------------------
    # SMS
    # ------------------------------------------------------------------

    async def send_sms(
        self,
        recipients: list[dict],
        sender_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send bulk or single SMS.

        ``recipients`` is a list of ``{"recipient": "<phone>", "message": "<text>"}``
        dicts, optionally including ``"ref": "<unique-ref>"``.
        """
        sid = sender_id or self.settings.default_sms_sender_id
        payload = {
            "type": 1,
            "senderid": sid,
            "messages": recipients,
        }
        raw = await self._post("/open/sms/send", payload, headers=self._vaskey_headers())
        return {
            "success": raw.get("status") in (1, "1"),
            "code": raw.get("code"),
            "message": raw.get("message", ""),
            "raw": raw,
        }

    async def send_single_sms(
        self,
        phone: str,
        message: str,
        sender_id: str | None = None,
        ref: str | None = None,
    ) -> dict[str, Any]:
        """Convenience wrapper for a single recipient SMS."""
        entry: dict = {"recipient": phone, "message": message}
        if ref:
            entry["ref"] = ref
        return await self.send_sms([entry], sender_id=sender_id)

    # ------------------------------------------------------------------
    # Payment Link
    # ------------------------------------------------------------------

    async def generate_payment_link(
        self,
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
    ) -> dict[str, Any]:
        """Generate a hosted Moolre payment page URL."""
        ext_ref = external_ref or str(uuid.uuid4())
        acc = account_number or self.settings.moolre_account_number
        payload: dict = {
            "type": 1,
            "amount": str(amount),
            "email": email,
            "externalref": ext_ref,
            "reusable": "1" if reusable else "0",
            "expiration_time": expiration_minutes,
            "currency": currency,
            "accountnumber": acc,
        }
        if callback_url:
            payload["callback"] = callback_url
        if redirect_url:
            payload["redirect"] = redirect_url
        if metadata:
            payload["metadata"] = metadata

        raw = await self._post("/embed/link", payload)
        link_data = raw.get("data", {}) or {}
        return {
            "success": raw.get("status") in (1, "1"),
            "payment_url": link_data.get("authorization_url"),
            "reference": link_data.get("reference", ext_ref),
            "raw": raw,
        }
