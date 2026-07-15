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

Moolre sends the OTP directly to the registered payer phone (not via AgroOS).
Cooperative staff must never ask the member to relay that OTP or enter it in
the dashboard. AgroOS persists the original payment reference as an
`otp` customer action and tells the member to complete it through USSD.

### Farmer-action flow

**Step 1 — Farmer starts payment:** the member dials `AGROOS_USSD_CODE` and
chooses **Pay Dues** or **Repay Loan**. Signed USSDK menus call
`POST /ussdk/pay-dues` or `POST /ussdk/loan-repayment`. Dashboard collection
and payment-link endpoints are disabled in production.

**Step 2 — Farmer completes the pending payment on their phone:**

1. The member dials the configured `AGROOS_USSD_CODE` (currently
   `*919*4020#`).
2. They continue in the same dues or loan-repayment flow.
3. AgroOS resolves the action from the caller's registered phone.
4. The member enters the Moolre OTP in that USSD session.
5. AgroOS reuses the original `moolre_reference`; no second payment starts.

If the session is interrupted, **Complete Pending Payment** and
`POST /ussdk/pending-payment` provide a recovery path.
Calling it without `transaction_id` lists phone-scoped actions; calling it with
the selected `transaction_id` first requests and then submits `otp_code`.
The old admin endpoint `/transactions/dues/collect/verify` no longer exists.

**Step 3 — Farmer approves on phone** → Moolre sends webhook to `{PUBLIC_URL}/webhooks/moolre/payment` → transaction moves to `completed`, Trust Score recalculates, and a payment confirmation SMS is sent.

Pending OTP or approval actions expire after 15 minutes. OTP values are passed
directly to Moolre and are never persisted or written to USSD logs.

### Channel codes

| Code | Network |
|------|---------|
| `13` | MTN Ghana |
| `6` | Telecel |
| `7` | AT |

### Local webhook requirement

Steps 2–3 require a publicly reachable callback URL. Use ngrok as described in section 4 above.

### Outbound cooperative SMS

Dues reminders, broadcasts, and payment confirmations use `POST /open/sms/send` with **`X-API-USER` and `X-API-VASKEY` headers only**. Do not send wallet keys (`X-API-KEY` / `X-API-PUBKEY`) or `accountnumber` on SMS requests — that triggers Moolre auth error `APY00`.

Required env vars:

- `MOOLRE_API_VASKEY` — live SMS VAS key from the Moolre **developer portal** (regenerate if broadcasts return `AIN01` / `Authentication Error`)
- `MOOLRE_API_USER` — same API user as payments
- `DEFAULT_SMS_SENDER_ID` — must be approved in [app.moolre.com](https://app.moolre.com)
- `AGROOS_USSD_CODE` — complete approved AgroOS menu dial string used in
  farmer-facing payment instructions
- `MOOLRE_MERCHANT_CODE` — bare Moolre merchant identifier only; do not include
  `*203*` or `#`

Payments/USSD continue to use `MOOLRE_API_KEY`, `MOOLRE_API_PUBKEY`, and `MOOLRE_ACCOUNT_NUMBER`.

Check SMS auth without sending: `GET /communications/sms/diagnostics` (authenticated).
