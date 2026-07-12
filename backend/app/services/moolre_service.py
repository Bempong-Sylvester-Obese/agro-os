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

    _shared_client: httpx.AsyncClient | None = None

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.moolre_api_url.rstrip("/")
        self._base_headers = self._build_base_headers()

    @classmethod
    def _http_client(cls) -> httpx.AsyncClient:
        if cls._shared_client is None:
            cls._shared_client = httpx.AsyncClient(timeout=30.0)
        return cls._shared_client

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
        if self.settings.moolre_env.lower() == "live" and self.settings.moolre_api_pubkey:
            headers["X-API-PUBKEY"] = self.settings.moolre_api_pubkey
        return headers

    def _vaskey_headers(self) -> dict:
        """Build headers for SMS/VAS endpoints (USER + VASKEY per Moolre docs)."""
        headers: dict = {
            "Content-Type": "application/json",
            "X-API-USER": self.settings.moolre_api_user,
        }
        if self.settings.moolre_api_vaskey:
            headers["X-API-VASKEY"] = self.settings.moolre_api_vaskey
        if self.settings.moolre_env.lower() == "live":
            if self.settings.moolre_api_key:
                headers["X-API-KEY"] = self.settings.moolre_api_key
            if self.settings.moolre_api_pubkey:
                headers["X-API-PUBKEY"] = self.settings.moolre_api_pubkey
        return headers

    def _pubkey_headers(self) -> dict:
        """Build headers for endpoints requiring public key."""
        headers: dict = {
            "Content-Type": "application/json",
            "X-API-USER": self.settings.moolre_api_user,
        }
        if self.settings.moolre_api_pubkey:
            headers["X-API-PUBKEY"] = self.settings.moolre_api_pubkey
        return headers

    def _normalize_phone(self, phone: str) -> str:
        """Normalize Ghanaian phone numbers to start with 0 and be 10 digits long for Moolre API."""
        phone = phone.strip().replace("+", "").replace(" ", "")
        if phone.startswith("233") and len(phone) == 12:
            return f"0{phone[3:]}"
        return phone

    def resolve_account_number(self, cooperative_account: str | None = None) -> str:
        """Use cooperative wallet when set; otherwise fall back to global settings."""
        if cooperative_account and cooperative_account.strip():
            return cooperative_account.strip()
        return self.settings.moolre_account_number

    def validate_payment_config(self, cooperative_account: str | None = None) -> str | None:
        """Return a user-facing error when Moolre payment credentials are incomplete."""
        if not self.settings.moolre_api_user.strip():
            return (
                "Moolre API user is not configured on the server. "
                "Set MOOLRE_API_USER in the backend environment."
            )
        account = self.resolve_account_number(cooperative_account)
        if not account.strip():
            return (
                "Moolre wallet account is not configured. "
                "Add your Moolre account number in Settings, or set MOOLRE_ACCOUNT_NUMBER on the server."
            )
        if self.settings.moolre_env.lower() == "live":
            if not self.settings.moolre_api_key.strip() or not self.settings.moolre_api_pubkey.strip():
                return (
                    "Moolre live API keys are not configured on the server. "
                    "Set MOOLRE_API_KEY and MOOLRE_API_PUBKEY for production."
                )
        return None

    def resolve_sms_account_number(self) -> str:
        """SMS credits are billed to the platform VAS wallet, not cooperative payment wallets."""
        return self.settings.moolre_account_number.strip()

    def validate_sms_config(self) -> str | None:
        """Return a user-facing error when Moolre SMS credentials are incomplete."""
        if not self.settings.moolre_api_user.strip():
            return (
                "Moolre API user is not configured on the server. "
                "Set MOOLRE_API_USER in the backend environment."
            )
        if not self.settings.moolre_api_vaskey.strip():
            return (
                "Moolre VAS key is not configured on the server. "
                "Set MOOLRE_API_VASKEY for SMS broadcasts (required in production)."
            )
        if not self.resolve_sms_account_number():
            return (
                "Moolre wallet account is not configured. "
                "Set MOOLRE_ACCOUNT_NUMBER on the server for SMS billing."
            )
        if self.settings.moolre_env.lower() == "live":
            if not self.settings.moolre_api_key.strip() or not self.settings.moolre_api_pubkey.strip():
                return (
                    "Moolre live API keys are not configured on the server. "
                    "Set MOOLRE_API_KEY and MOOLRE_API_PUBKEY for production."
                )
        return None

    @staticmethod
    def _http_error_payload(exc: httpx.HTTPStatusError) -> dict:
        try:
            body = exc.response.json()
            if isinstance(body, dict):
                message = body.get("message") or body.get("error") or str(exc)
                return {
                    **body,
                    "status": body.get("status", 0),
                    "code": body.get("code", ""),
                    "message": message,
                    "success": False,
                    "status_code": exc.response.status_code,
                }
        except Exception:
            pass
        return {
            "status": 0,
            "code": "",
            "message": str(exc),
            "success": False,
            "status_code": exc.response.status_code,
        }

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    async def _post(self, path: str, payload: dict, headers: dict | None = None) -> dict:
        h = headers or self._base_headers
        client = self._http_client()
        for attempt in range(3):
            try:
                resp = await client.post(f"{self.base_url}{path}", json=payload, headers=h)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < 2:
                    continue
                return self._http_error_payload(exc)
            except httpx.RequestError as exc:
                if attempt < 2:
                    continue
                return {"success": False, "error": str(exc)}
        return {"success": False, "error": "max retries exceeded"}

    async def _get(self, path: str, params: dict | None = None, headers: dict | None = None) -> dict:
        h = headers or self._base_headers
        client = self._http_client()
        for attempt in range(3):
            try:
                resp = await client.get(f"{self.base_url}{path}", params=params, headers=h)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < 2:
                    continue
                return self._http_error_payload(exc)
            except httpx.RequestError as exc:
                if attempt < 2:
                    continue
                return {"success": False, "error": str(exc)}
        return {"success": False, "error": "max retries exceeded"}

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
        otpcode: str | None = None,
        reference: str = "Cooperative dues",
        account_number: str | None = None,
    ) -> dict[str, Any]:
        """
        Trigger a USSD payment prompt on the payer's phone.

        channel codes: 13=MTN Ghana, 6=Telecel, 7=AT
        Returns a normalised dict with ``success``, ``moolre_reference``, ``message``.
        """
        ext_ref = external_ref or str(uuid.uuid4())
        acc = self.resolve_account_number(account_number)
        config_error = self.validate_payment_config(account_number)
        if config_error:
            return {
                "success": False,
                "verification_required": False,
                "outcome": "failed",
                "moolre_code": None,
                "moolre_reference": ext_ref,
                "external_ref": ext_ref,
                "message": config_error,
                "raw": {},
            }
        normalized_phone = self._normalize_phone(payer_phone)

        payload = {
            "type": 1,
            "channel": channel,
            "currency": currency,
            "payer": normalized_phone,
            "amount": str(amount),
            "externalref": ext_ref,
            "reference": reference,
            "accountnumber": acc,
        }
        if otpcode:
            payload["otpcode"] = otpcode

        raw = await self._post("/open/transact/payment", payload)

        code = raw.get("code", "")
        verification_required = code == "TP14"
        success = code == "TR099" or (
            raw.get("status") in (1, "1") and not verification_required
        )
        if verification_required:
            outcome = "verification_required"
        elif success:
            outcome = "push_sent"
        else:
            outcome = "failed"

        return {
            "success": success,
            "verification_required": verification_required,
            "outcome": outcome,
            "moolre_code": code or None,
            "moolre_reference": raw.get("data") or ext_ref,
            "external_ref": ext_ref,
            "message": raw.get("message") or raw.get("error", ""),
            "raw": raw,
        }

    async def payment_status(
        self,
        external_ref: str,
        account_number: str | None = None,
    ) -> dict[str, Any]:
        """Check the status of a previously initiated payment."""
        acc = self.resolve_account_number(account_number)
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
        acc = self.resolve_account_number(account_number)
        normalized_phone = self._normalize_phone(receiver_phone)

        payload = {
            "type": 1,
            "channel": channel,
            "currency": currency,
            "amount": str(amount),
            "receiver": normalized_phone,
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
        acc = self.resolve_account_number(account_number)
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
        acc = self.resolve_account_number(account_number)
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
        acc = self.resolve_account_number(account_number)
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

        SMS billing uses the platform ``MOOLRE_ACCOUNT_NUMBER`` tied to ``MOOLRE_API_VASKEY``,
        not per-cooperative payment wallets.
        """
        config_error = self.validate_sms_config()
        if config_error:
            return {
                "success": False,
                "code": None,
                "message": config_error,
                "raw": {},
            }

        sid = sender_id or self.settings.default_sms_sender_id
        acc = self.resolve_sms_account_number()
        messages = []
        for entry in recipients:
            item = dict(entry)
            item["recipient"] = self._normalize_phone(str(entry.get("recipient", "")))
            messages.append(item)
        payload = {
            "type": 1,
            "senderid": sid,
            "accountnumber": acc,
            "messages": messages,
        }
        raw = await self._post("/open/sms/send", payload, headers=self._vaskey_headers())
        moolre_ref = None
        data = raw.get("data")
        if isinstance(data, str):
            moolre_ref = data
        elif isinstance(data, dict):
            moolre_ref = data.get("reference") or data.get("id")
        return {
            "success": raw.get("status") in (1, "1"),
            "code": raw.get("code"),
            "message": raw.get("message", ""),
            "moolre_ref": moolre_ref,
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
        acc = self.resolve_account_number(account_number)
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

        raw = await self._post("/embed/link", payload, headers=self._pubkey_headers())
        link_data = raw.get("data", {}) or {}
        return {
            "success": raw.get("status") in (1, "1"),
            "payment_url": link_data.get("authorization_url"),
            "reference": link_data.get("reference", ext_ref),
            "raw": raw,
        }
