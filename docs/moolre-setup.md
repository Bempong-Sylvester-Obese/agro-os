# Moolre setup and credentials guide

This guide explains exactly where each AgroOS Moolre environment variable comes from, what differs between sandbox and live, and how to test webhooks locally.

## 1) Where each env var comes from

Use `backend/.env.example` as your template and fill values from the right source:

| Env var | Where to get it | Notes |
|---|---|---|
| `MOOLRE_API_USER` | Your Moolre login email / API user | Required in sandbox and live requests (`X-API-USER`) |
| `MOOLRE_ACCOUNT_NUMBER` | Moolre Wallet/Account page | Wallet account number used for account status checks |
| `MOOLRE_WEBHOOK_SECRET` | Moolre Wallet/Callback/Webhook settings | Used to verify `X-Moolre-Signature` |
| `MOOLRE_MERCHANT_CODE` | Moolre merchant/wallet settings | Used for USSD dues prompt in AgroOS |
| `MOOLRE_API_KEY` | Moolre Developers portal (live keys) | Private key for live auth |
| `MOOLRE_API_PUBKEY` | Moolre Developers portal (live keys) | Public key for live auth |
| `MOOLRE_API_VASKEY` | Moolre Developers portal (live keys) | Needed for SMS/WhatsApp endpoints |
| `MOOLRE_API_URL` | Environment selection | Sandbox: `https://sandbox.moolre.com`, Live: `https://api.moolre.com` |

## 2) Sandbox vs live headers

AgroOS uses different Moolre auth expectations by environment:

- **Sandbox**: use `X-API-USER` only (`MOOLRE_API_USER`).
- **Live**: include full live credentials/headers from developer keys (`MOOLRE_API_KEY`, `MOOLRE_API_PUBKEY`, and where required `MOOLRE_API_VASKEY`) plus API user.

If wallet/account endpoints return auth failures, double-check that your header set matches the environment.

## 3) Callback URL format

Set your Moolre callback URL exactly as:

```text
{PUBLIC_URL}/webhooks/moolre/payment
```

Examples:
- Local tunnel: `https://abc123.ngrok-free.app/webhooks/moolre/payment`
- Deployed API: `https://api.yourdomain.com/webhooks/moolre/payment`

AgroOS payment webhook route is implemented at `POST /webhooks/moolre/payment`.

## 4) Local development with ngrok

1. Start AgroOS backend locally (default `http://localhost:8000`).
2. In another terminal, expose it:
   ```bash
   ngrok http 8000
   ```
3. Copy the generated HTTPS URL (example: `https://abc123.ngrok-free.app`).
4. In Moolre portal, set callback URL to:
   ```text
   https://abc123.ngrok-free.app/webhooks/moolre/payment
   ```
5. Update `backend/.env`:
   - `MOOLRE_ENV=sandbox`
   - `MOOLRE_API_URL=https://sandbox.moolre.com`
   - `MOOLRE_API_USER=<your moolre login email/api user>`
   - `MOOLRE_ACCOUNT_NUMBER=<wallet account number>`
   - `MOOLRE_WEBHOOK_SECRET=<wallet webhook secret>` (set this for realistic testing; only skip in isolated local-only debugging, never in shared/staging/prod environments)
6. Trigger a sandbox payment and confirm webhook logs in backend output.

## 5) What AgroOS does **not** show in the UI

AgroOS frontend does not display Moolre secrets.

Keep all Moolre secrets in `backend/.env` (server-side), including:
- `MOOLRE_API_KEY`
- `MOOLRE_API_PUBKEY`
- `MOOLRE_API_VASKEY`
- `MOOLRE_WEBHOOK_SECRET`

Do not paste these values into frontend configs or dashboard forms.

## 6) `.env` checklists

### Minimum sandbox checklist (quick integration)

- `MOOLRE_ENV=sandbox`
- `MOOLRE_API_URL=https://sandbox.moolre.com`
- `MOOLRE_API_USER=<sandbox API user/login email>`
- `MOOLRE_ACCOUNT_NUMBER=<sandbox wallet account number>`
- `MOOLRE_MERCHANT_CODE=<sandbox merchant code>`
- `MOOLRE_WEBHOOK_SECRET=<sandbox webhook secret>` (configure before real sandbox testing; only leave empty for isolated local-only debugging)

### Full production/live checklist

- `MOOLRE_ENV=live`
- `MOOLRE_API_URL=https://api.moolre.com`
- `MOOLRE_API_USER=<live API user/login email>`
- `MOOLRE_API_KEY=<live private key>`
- `MOOLRE_API_PUBKEY=<live public key>`
- `MOOLRE_API_VASKEY=<live VAS key>`
- `MOOLRE_ACCOUNT_NUMBER=<live wallet account number>`
- `MOOLRE_MERCHANT_CODE=<live merchant code>`
- `MOOLRE_WEBHOOK_SECRET=<live webhook secret>`

## Troubleshooting

### Wallet balance endpoint returns `401`

Common causes:
- Using live headers against sandbox URL (or vice versa)
- Missing/incorrect `X-API-USER` in sandbox
- Incorrect live developer keys in production
- Wrong `MOOLRE_ACCOUNT_NUMBER`

Verify `MOOLRE_ENV`, `MOOLRE_API_URL`, and credentials are from the same Moolre environment.

### Webhook signature verification skipped in development

In `backend/app/routes/webhooks.py`, AgroOS skips signature checks when `MOOLRE_WEBHOOK_SECRET` is empty (dev convenience). You will see a warning log.

For realistic testing and production safety, always set `MOOLRE_WEBHOOK_SECRET`.

## 7) Sandbox phone OTP verification (TP14)

On **first use** of a payer phone number in the Moolre sandbox, payment push returns response code **`TP14`** (HTTP 200, `status: 1`):

> Please complete the verification process sent to you via SMS and try again.

Moolre sends an OTP SMS directly to the payer phone (not via AgroOS). This is a one-time phone verification step — it does **not** mean you should call `POST /transactions/dues/collect` again. Submit the OTP via `POST /transactions/dues/collect/verify` using the **same** `transaction_id` and `moolre_reference` returned in the TP14 response; AgroOS reuses that reference internally to complete the original payment push.

### Two-step AgroOS API flow

**Step 1 — Initiate collect** (creates a pending transaction):

```http
POST /transactions/dues/collect
Content-Type: application/json

{
  "farmer_id": 1,
  "amount": 1.00,
  "channel": "13",
  "description": "Cooperative dues"
}
```

If TP14, the response includes:

```json
{
  "transaction_id": 42,
  "moolre_reference": "<uuid>",
  "status": "verification_required",
  "outcome": "verification_required",
  "moolre_code": "TP14",
  "message": "Please complete the verification process sent to you via SMS and try again."
}
```

**Step 2 — Submit OTP** (reuse the same `moolre_reference`; do **not** call collect again):

```http
POST /transactions/dues/collect/verify
Content-Type: application/json

{
  "transaction_id": 42,
  "otp_code": "<code-from-moolre-sms>"
}
```

On success (`TR099`), the response has `status: "pending"` and the farmer receives a USSD MoMo approval prompt on their phone.

**Step 3 — Farmer approves on phone** → Moolre sends webhook to `{PUBLIC_URL}/webhooks/moolre/payment` → transaction moves to `completed`, Trust Score recalculates, and a payment confirmation SMS is sent.

### Channel codes

| Code | Network |
|------|---------|
| `13` | MTN Ghana |
| `6` | Telecel |
| `7` | AT |

### Local webhook requirement

Steps 2–3 require a publicly reachable callback URL. Use ngrok as described in section 4 above.

### Outbound cooperative SMS

Dues reminders, broadcasts, and payment confirmations use `POST /open/sms/send` with the `X-API-VASKEY` header. Ensure these env vars are set for sandbox SMS testing:

- `MOOLRE_API_VASKEY`
- `DEFAULT_SMS_SENDER_ID`
- `MOOLRE_MERCHANT_CODE` (included in dues reminder dial string)
