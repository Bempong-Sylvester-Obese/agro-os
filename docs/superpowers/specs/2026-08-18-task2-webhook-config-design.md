# Design: Configurable Webhook Callback Path

## Goal
Extract hardcoded webhook URL paths from service code and rate-limiter config into a settings-driven value, and remove Moolre branding from the app description.

## Changes

1. **config.py** — Add `webhook_callback_path: str = "/webhooks/payment"` after `agroos_base_url`.
2. **moolre_service.py** — Replace hardcoded `/webhooks/moolre/payment` with `{settings.webhook_callback_path}`.
3. **rate_limit.py** — Include `settings.webhook_callback_path` in the webhook-path set alongside the legacy hardcoded paths.
4. **main.py** — Remove "Powered by Moolre" from `app.description`.
5. **.env.example** — Add `WEBHOOK_CALLBACK_PATH=/webhooks/payment`.

## Backward Compatibility
Legacy hardcoded paths (`/webhooks/moolre/payment`, `/webhooks/moolre/ussd`) are retained in rate-limit and public-path sets so existing webhooks continue to work.

## Verification
- App boots (`from main import app`)
- Backend tests pass (`npm run test:backend`)
