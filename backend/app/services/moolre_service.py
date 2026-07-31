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
        """SMS/VAS endpoints authenticate with USER + VASKEY only (Moolre docs)."""
        headers: dict = {
            "Content-Type": "application/json",
            "X-API-USER": self.settings.moolre_api_user,
        }
        if self.settings.moolre_api_vaskey:
            headers["X-API-VASKEY"] = self.settings.moolre_api_vaskey
        return headers

    @staticmethod
    def format_sms_error(
        code: str | None,
        message: str | None,
        sender_id: str | None = None,
    ) -> str:
        """Turn Moolre SMS error codes into actionable dashboard messages."""
        base = (message or "Moolre SMS send failed").strip()
        sid = sender_id or "your sender ID"
        hints = {
            "AIN01": (
                "Moolre rejected the SMS VAS key. In the Moolre developer portal, "
                "regenerate the live SMS VAS key and update MOOLRE_API_VASKEY on Render."
            ),
            "AIN11": (
                "Moolre rejected the SMS VAS key. Regenerate MOOLRE_API_VASKEY from the "
                "Moolre developer portal (live environment) and redeploy."
            ),
            "APY00": (
                "Moolre SMS auth failed. SMS uses MOOLRE_API_VASKEY only — regenerate the "
                "live VAS key in the Moolre developer portal and ensure SMS is enabled."
            ),
            "ASMS07": (
                f"Sender ID is not approved. Log in to app.moolre.com and approve sender ID '{sid}'."
            ),
        }
        if code in hints:
            return f"{base} {hints[code]}"
        return base

    def _private_key_headers(self) -> dict:
        """Transfer/payment write endpoints require USER + private API key (no PUBKEY)."""
        headers: dict = {
            "Content-Type": "application/json",
            "X-API-USER": self.settings.moolre_api_user,
        }
        if self.settings.moolre_api_key:
            headers["X-API-KEY"] = self.settings.moolre_api_key
        return headers

    @staticmethod
    def detect_transfer_channel(phone: str) -> str:
        """Map Ghana MSISDN prefix to Moolre transfer channel (1=MTN, 6=Telecel, 7=AT)."""
        normalized = phone.strip().replace("+", "").replace(" ", "")
        if normalized.startswith("233") and len(normalized) >= 12:
            normalized = normalized[3:]
        if normalized.startswith("0"):
            normalized = normalized[1:]
        prefix = normalized[:2]
        if prefix in {"20", "50"}:
            return "6"
        if prefix in {"26", "27", "56", "57"}:
            return "7"
        return "1"

    @staticmethod
    def format_transfer_error(code: str | None, message: str | None) -> str:
        base = (message or "Moolre transfer failed").strip()
        if isinstance(base, list):
            base = " ".join(str(part) for part in base)
        hints = {
            "AIN01": (
                "Moolre rejected transfer credentials. Confirm MOOLRE_API_KEY is your live "
                "private key (not the public key) and that payout/transfer access is enabled."
            ),
            "AIN11": (
                "Moolre rejected the API key. Regenerate your live private key in the Moolre "
                "developer portal and update MOOLRE_API_KEY on Render."
            ),
        }
        if code in hints:
            return f"{base} {hints[code]}"
        if "authentication" in base.lower() and "not activated" in base.lower():
            return (
                f"{base} Enable transfer/payout API access for your Moolre merchant account "
                "in app.moolre.com, then retry."
            )
        return base

    async def resolve_verified_account(self, cooperative_account: str | None = None) -> tuple[str, str | None]:
        """Return a Moolre wallet that responds to account/status, or an error message."""
        config_error = self.validate_payment_config(cooperative_account)
        if config_error:
            return "", config_error

        preferred = self.resolve_account_number(cooperative_account)
        preferred_status = await self.account_status(account_number=preferred)
        if preferred_status.get("success"):
            return preferred, None

        platform = self.settings.moolre_account_number.strip()
        coop = (cooperative_account or "").strip()
        if platform and platform != preferred:
            platform_status = await self.account_status(account_number=platform)
            if platform_status.get("success"):
                return platform, None

        raw = preferred_status.get("raw") or {}
        code = raw.get("code")
        message = raw.get("message") or "Could not access Moolre wallet for disbursement."
        if coop and platform and coop != platform:
            message = (
                f"Moolre rejected cooperative wallet {coop}. "
                "Update the Moolre account in Settings to match your live wallet, "
                "or clear it to use the platform MOOLRE_ACCOUNT_NUMBER."
            )
        return preferred, self.format_transfer_error(code, message)

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

    def _transfer_receiver(self, phone: str) -> str:
        """Format payout receiver as the local 0XXXXXXXXX form required by Moolre."""
        return self._normalize_phone(phone)

    @staticmethod
    def _format_transfer_amount(amount: float) -> str:
        return f"{float(amount):.2f}"

    async def validate_transfer_recipient(
        self,
        receiver_phone: str,
        account_number: str | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        """Confirm MoMo recipient via Moolre validate-name before payout."""
        receiver = self._transfer_receiver(receiver_phone)
        ch = channel or self.detect_transfer_channel(receiver_phone)
        acc = self.resolve_account_number(account_number)
        payload = {
            "type": 1,
            "receiver": receiver,
            "channel": ch,
            "currency": "GHS",
            "accountnumber": acc,
        }
        raw = await self._post("/open/transact/validate", payload, headers=self._private_key_headers())
        code = raw.get("code")
        success = raw.get("status") in (1, "1") or code == "AVD01"
        return {
            "success": success,
            "channel": ch,
            "receiver": receiver,
            "receiver_name": raw.get("data"),
            "message": raw.get("message") or raw.get("error", ""),
            "code": code,
            "raw": raw,
        }

    async def resolve_momo_transfer_channel(
        self,
        receiver_phone: str,
        account_number: str | None = None,
    ) -> tuple[str, str, str | None]:
        """Return (channel, receiver, error) after validating the MoMo wallet."""
        candidates = []
        detected = self.detect_transfer_channel(receiver_phone)
        for ch in (detected, "1", "6", "7"):
            if ch not in candidates:
                candidates.append(ch)

        last_message = "Could not validate the member mobile money wallet."
        for ch in candidates:
            result = await self.validate_transfer_recipient(
                receiver_phone,
                account_number=account_number,
                channel=ch,
            )
            if result["success"]:
                return result["channel"], result["receiver"], None
            last_message = str(result.get("message") or last_message)

        return detected, self._transfer_receiver(receiver_phone), last_message

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
        if not (self.settings.default_sms_sender_id or "").strip():
            return (
                "SMS sender ID is not configured. "
                "Set DEFAULT_SMS_SENDER_ID to your Moolre-approved sender ID."
            )
        return None

    async def diagnose_sms(self) -> dict[str, Any]:
        """Probe Moolre SMS auth without sending a message."""
        config_error = self.validate_sms_config()
        if config_error:
            return {"ok": False, "stage": "config", "message": config_error}

        wallet = await self._post(
            "/open/account/status",
            {"type": 1, "accountnumber": self.settings.moolre_account_number},
        )
        wallet_ok = wallet.get("code") == "SW01"

        balance = await self._post(
            "/open/sms/status",
            {"type": 2},
            headers=self._vaskey_headers(),
        )
        balance_ok = balance.get("code") == "ASMQ03"

        senders = await self._post(
            "/open/sms/query",
            {"type": 5},
            headers=self._vaskey_headers(),
        )
        senders_ok = senders.get("status") in (1, "1")
        probe_code = senders.get("code") if not senders_ok else "SMS01"
        probe_message = senders.get("message")

        if probe_code == "SMS01":
            return {
                "ok": True,
                "stage": "sms",
                "message": "Moolre SMS credentials accepted.",
                "wallet_ok": wallet_ok,
                "balance_ok": balance_ok,
            }

        return {
            "ok": False,
            "stage": "sms",
            "wallet_ok": wallet_ok,
            "balance_ok": balance_ok,
            "code": probe_code,
            "message": self.format_sms_error(
                probe_code,
                probe_message,
                sender_id=self.settings.default_sms_sender_id,
            ),
        }

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
            "moolre_reference": (raw.get("data") if not verification_required else None) or ext_ref,
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
        channel: str | None = None,
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
        config_error = self.validate_payment_config(account_number)
        if config_error:
            return {
                "success": False,
                "moolre_transfer_ref": ext_ref,
                "external_ref": ext_ref,
                "message": config_error,
                "raw": {},
            }
        transfer_channel = channel
        transfer_receiver = self._transfer_receiver(receiver_phone)
        if channel is None:
            transfer_channel, transfer_receiver, validate_error = await self.resolve_momo_transfer_channel(
                receiver_phone,
                account_number=account_number,
            )
            if validate_error:
                return {
                    "success": False,
                    "moolre_transfer_ref": ext_ref,
                    "external_ref": ext_ref,
                    "message": validate_error,
                    "raw": {},
                }

        payload = {
            "type": 1,
            "channel": transfer_channel,
            "currency": currency,
            "amount": self._format_transfer_amount(amount),
            "receiver": transfer_receiver,
            "externalref": ext_ref,
            "reference": reference,
            "accountnumber": acc,
        }

        raw = await self._post("/open/transact/transfer", payload, headers=self._private_key_headers())
        code = raw.get("code")
        success = raw.get("status") in (1, "1") or str(code or "").startswith("OBGH")
        tx_data = raw.get("data", {}) or {}
        message = raw.get("message") or raw.get("error", "")
        if isinstance(message, list):
            message = " ".join(str(part) for part in message)
        if not success:
            message = self.format_transfer_error(code, message)
        return {
            "success": success,
            "moolre_transfer_ref": tx_data.get("transactionid") or ext_ref,
            "external_ref": ext_ref,
            "message": message,
            "raw": raw,
        }

    async def transfer_status(
        self,
        reference: str,
        account_number: str | None = None,
        id_type: str = "1",
    ) -> dict[str, Any]:
        """Check the status of a transfer."""
        acc = self.resolve_account_number(account_number)
        payload = {
            "type": 1,
            "idtype": id_type,
            "id": reference,
            "accountnumber": acc,
        }
        raw = await self._post("/open/transact/status", payload, headers=self._private_key_headers())
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

    async def internal_transfer(
        self,
        receiver_account: str,
        amount: float,
        currency: str = "GHS",
        external_ref: str | None = None,
        reference: str = "Internal Transfer",
        from_account_number: str | None = None,
    ) -> dict[str, Any]:
        """Initiate an internal transfer between Moolre wallets."""
        ext_ref = external_ref or str(uuid.uuid4())
        acc = self.resolve_account_number(from_account_number)
        
        payload = {
            "type": 1,
            "currency": currency,
            "amount": self._format_transfer_amount(amount),
            "receiver": receiver_account,
            "externalref": ext_ref,
            "reference": reference,
            "accountnumber": acc,
        }
        
        raw = await self._post("/open/transact/internal", payload, headers=self._private_key_headers())
        code = raw.get("code")
        success = raw.get("status") in (1, "1") or str(code or "") == "TR099"
        
        return {
            "success": success,
            "external_ref": ext_ref,
            "message": raw.get("message") or raw.get("error", ""),
            "raw": raw,
        }

    # ------------------------------------------------------------------
    # Account / Wallet
    # ------------------------------------------------------------------

    async def create_account(
        self,
        account_name: str,
        currency: str = "GHS",
        api: int = 1,
        callback: str | None = None,
    ) -> dict[str, Any]:
        """Create a new business wallet (sub-account)."""
        # Moolre requires a settlement object and callback if API is enabled
        payload = {
            "type": 1,
            "accountname": account_name,
            "currency": currency,
            "api": api,
            "callback": callback or "https://api.agroos.company/webhooks/moolre/payment",
            "settlement": {
                "currency": currency,
                "frequency": "1",
                "channel": "1",
                "recipient": "0240000000" # default placeholder
            }
        }

        # Uses USER + API_KEY according to docs
        headers = self._private_key_headers()
        raw = await self._post("/open/account/create", payload, headers=headers)
        
        acc_data = raw.get("data", {})
        if not isinstance(acc_data, dict):
            acc_data = {}
            
        return {
            "success": raw.get("status") in (1, "1"),
            "account_number": acc_data.get("accountnumber"),
            "secret": acc_data.get("secret"),
            "raw": raw,
        }

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

        SMS billing is authenticated via ``MOOLRE_API_VASKEY`` (not wallet API keys).
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
        messages = []
        for entry in recipients:
            item = dict(entry)
            item["recipient"] = self._normalize_phone(str(entry.get("recipient", "")))
            messages.append(item)
        payload = {
            "type": 1,
            "senderid": sid,
            "messages": messages,
        }
        raw = await self._post("/open/sms/send", payload, headers=self._vaskey_headers())
        moolre_ref = None
        data = raw.get("data")
        if isinstance(data, str):
            moolre_ref = data
        elif isinstance(data, dict):
            moolre_ref = data.get("reference") or data.get("id")
        code = raw.get("code")
        sid = sender_id or self.settings.default_sms_sender_id
        message = self.format_sms_error(code, raw.get("message", ""), sender_id=sid)
        return {
            "success": raw.get("status") in (1, "1"),
            "code": code,
            "message": message,
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
