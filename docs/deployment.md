# AgroOS Deployment Runbook

> **Status:** Hackathon Reference Doc — Moolre Startup Cup (July 2026)
> **Maintainer:** AgroOS Core Team
> **Last updated:** 2026-06
>
> This runbook covers frontend and backend deployment, environment
> variables, Moolre webhook registration, local webhook testing with
> ngrok, and post-deploy smoke tests.

---

## 1. Architecture Overview

```
Browser / USSD
     │
     ▼
Vercel (Frontend)          ← Vite + React dashboard
     │  VITE_API_URL
     ▼
Render (Backend)           ← FastAPI 
     │  DATABASE_URL
     ▼
Supabase (PostgreSQL)      ← farmer records, transactions, scores

Moolre ──webhook──▶ Render /webhooks/moolre/payment
```

---

## 2. Environment Variables

### 2.1 Backend (`backend/.env`)

Copy from `backend/.env.example` before running locally or deploying.

| Variable | Description | Example |
|---|---|---|
| `APP_ENV` | Runtime environment | `development` / `production` |
| `DEBUG` | Enable uvicorn reload and debug logging | `true` / `false` |
| `DATABASE_URL` | Supabase PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `DEFAULT_CURRENCY` | Platform currency | `GHS` |
| `MOOLRE_API_URL` | Moolre base API URL | `https://api.moolre.com` |
| `MOOLRE_API_KEY` | Moolre API key | `mk_live_...` |
| `MOOLRE_API_PUBKEY` | Moolre live public key (required for live API calls) | `mpk_live_...` |
| `MOOLRE_WEBHOOK_SECRET` | Secret for verifying webhook signatures | `whsec_...` |
| `AGROOS_USSD_CODE` | Complete approved AgroOS menu dial string | `*919*4020#` |
| `USSDK_HOOK_SECRET` | HMAC secret shared with USSDK hooks | `ussdk_...` |
| `DEFAULT_SMS_SENDER_ID` | Approved SMS sender ID | `AgroOS` |
| `SENTRY_DSN` | Optional Sentry DSN for backend error tracking | `https://...@sentry.io/...` |
| `AGRO_AI_REQUIRE_ARTIFACT` | Fail health check when synthetic model is used | `true` / `false` |
| `RATE_LIMIT_ENABLED` | Enable route-specific abuse protection | `true` |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | Per-client login attempts | `10` |
| `RATE_LIMIT_WEBHOOK_PER_MINUTE` | Per-client Moolre/USSDK callbacks | `120` |
| `RATE_LIMIT_SMS_PER_MINUTE` | Per-client SMS send requests | `5` |
| `RATE_LIMIT_DUES_PER_MINUTE` | Per-client dues collection requests | `10` |

> ⚠️ Never commit `.env` to the repository. It is in `.gitignore`.
> Use Render's environment variable dashboard for production secrets.

### 2.2 Frontend (`frontend/.env`)

Copy from `frontend/.env.example` before running locally or deploying.

| Variable | Description | Example |
|---|---|---|
| `VITE_API_URL` | Backend API base URL | `https://agro-os-api.onrender.com` |
| `VITE_COOPERATIVE_ID` | Default cooperative ID for dashboard API calls | `1` |

For local development:
```
VITE_API_URL=http://localhost:8000
```

For production (set in Vercel dashboard):
```
VITE_API_URL=https://agro-os-api.onrender.com
VITE_COOPERATIVE_ID=1
```

> `NEXT_PUBLIC_API_URL` is deprecated — do not use it. This is a Vite
> frontend; only `VITE_` prefixed variables are exposed to the browser.

---

## 3. CORS Configuration

CORS is configured in `backend/main.py`:

```python
_origins = ["*"] if settings.app_env == "development" else [
    "https://agro-os.vercel.app",  # production frontend
]
```

**In development** (`APP_ENV=development`): all origins are allowed (`*`).
This covers `localhost:5173` and any preview URL automatically.

**In production** (`APP_ENV=production`): only `https://agro-os.vercel.app`
is allowed by default.

### Adding a new preview or staging URL

If Vercel generates a preview URL (e.g. `https://agro-os-git-feat-xyz.vercel.app`)
that needs to hit the production backend, update the `_origins` list in
`backend/main.py`:

```python
_origins = ["*"] if settings.app_env == "development" else [
    "https://agro-os.vercel.app",
    "https://agro-os-git-feat-xyz.vercel.app",  # add preview URL here
]
```

Then redeploy the backend on Render. Alternatively, move the allowed origins
list to an environment variable to avoid code changes per preview:

```python
# backend/app/config.py (future improvement)
CORS_ORIGINS: list[str] = ["https://agro-os.vercel.app"]
```

```
# backend/.env (production)
CORS_ORIGINS=https://agro-os.vercel.app,https://agro-os-git-feat-xyz.vercel.app
```

---

## 4. Frontend Deployment (Vercel)

1. Connect the `agro-os` GitHub repository to a Vercel project
2. Set the **root directory** to `frontend/`
3. Set the **build command** to `npm run build`
4. Set the **output directory** to `dist`
5. Add environment variable in Vercel dashboard:
   - `VITE_API_URL` → `https://agro-os-api.onrender.com`
6. Deploy — Vercel auto-deploys on every push to `main`

### Preview deployments
Vercel creates a unique URL for every PR branch. These preview deployments
use the same `VITE_API_URL` unless overridden. If pointing a preview at
the production backend, add the preview origin to CORS (see Section 3).

---

## 5. Backend Deployment (Render)

1. Connect the `agro-os` GitHub repository to a Render Web Service
2. Set the **root directory** to `backend/`
3. Set the **build command**:
   ```
   pip install -r requirements.txt
   ```
4. Set the **start command**:
   ```
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
5. Add all environment variables from Section 2.1 in the Render dashboard
6. Set `APP_ENV=production` and `DEBUG=false`
7. Deploy — Render auto-deploys on every push to `main`

### Render public URL
After first deploy, Render assigns a URL like:
```
https://agro-os-api.onrender.com
```
Copy this URL — you need it for:
- `VITE_API_URL` in Vercel
- Moolre webhook callback URL (Section 6)

---

## 6. Moolre Webhook Registration

Moolre fires a `POST` request to your backend when a payment completes.
The backend uses this to record the transaction and recalculate the
farmer's Trust Score.

### Webhook endpoint
```
POST /webhooks/moolre/payment
```

### Full callback URL (production)
```
https://agro-os-api.onrender.com/webhooks/moolre/payment
```

### Steps to register in the Moolre portal
1. Log in to the Moolre merchant/developer portal
2. Navigate to **Webhooks** or **Developer Settings**
3. Add a new webhook endpoint:
   - **URL:** `https://agro-os-api.onrender.com/webhooks/moolre/payment`
   - **Events:** payment completed, transfer completed (select all relevant)
4. Copy the webhook secret provided by Moolre
5. Set `MOOLRE_WEBHOOK_SECRET` in the Render environment variable dashboard
6. Save and test using Moolre's "Send test event" feature

> ⚠️ The webhook URL must be a public HTTPS URL. `localhost` will not work
> with Moolre. Use ngrok for local testing (Section 7).

### USSDK menu mapping

Set `USSDK_HOOK_SECRET` in Render and configure the same value in USSDK.
Map the production menu screens to these signed hooks:

| Screen | Hook |
|---|---|
| Check Loan Balance | `POST /ussdk/loan-balance` |
| Pay Dues | `POST /ussdk/pay-dues` |
| Request Loan | `POST /ussdk/loan-request` |
| Complete Pending Payment | `POST /ussdk/pending-payment` |
| Announcements | `POST /ussdk/announcements` |

The loan request screen sends `amount`, `purpose`, and, when needed,
`membership_id`. The pending-payment screen first stores the returned
`transaction_id`, then sends `otp_code` only from the farmer's USSD session.
Never add an OTP field to the dashboard.

---

## 7. Local Webhook Testing with ngrok

When developing locally, Moolre cannot reach `localhost:8000`. Use ngrok
to expose your local backend over a public HTTPS URL.

### Setup
```bash
# Install ngrok (if not already installed)
# https://ngrok.com/download

# Start your local backend first
cd backend
uvicorn main:app --reload

# In a separate terminal, expose port 8000
ngrok http 8000
```

ngrok will output a public URL like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

### Register the ngrok URL with Moolre
Use this as your temporary webhook callback URL in the Moolre portal:
```
https://abc123.ngrok-free.app/webhooks/moolre/payment
```

Update `MOOLRE_WEBHOOK_SECRET` in your local `backend/.env` with the
secret from the portal.

### Test the webhook flow
1. Trigger a test payment via the Moolre sandbox USSD flow
2. Watch your local FastAPI logs — you should see the webhook hit
3. Verify the transaction is recorded in Supabase and the Trust Score updates

> ngrok URLs change every session on the free plan. Re-register the URL
> in the Moolre portal each time you restart ngrok, or use a paid ngrok
> plan with a fixed subdomain.

---

## 8. Preview vs Production Environment Separation

| | Local | Preview (Vercel PR) | Production |
|---|---|---|---|
| `APP_ENV` | `development` | `development` | `production` |
| CORS | `*` (all origins) | `*` (all origins) | `https://agro-os.vercel.app` only |
| Database | Local / Supabase dev branch | Supabase dev branch | Supabase production |
| Moolre keys | Sandbox keys | Sandbox keys | Live keys |
| Webhook URL | ngrok | ngrok / Render preview | Render production |
| Demo data | Synthetic `DEMO_FARMERS` | Synthetic `DEMO_FARMERS` | Real farmer data (future) |

> Never use live Moolre keys or production Supabase credentials in local
> or preview environments.

---

## 9. Post-Deploy Smoke Test Checklist

Run these checks after every production or staging deployment.

### 9.1 Health checks

Use the lightweight liveness endpoint to confirm that the API process is up:
```bash
curl https://agro-os-api.onrender.com/health/live
```

Use readiness for database and model availability:
```bash
curl https://agro-os-api.onrender.com/health/ready
```

`/health/ready` returns HTTP 503 with `database: "fail"` when PostgreSQL is
unreachable. In production it also returns 503 when the required Agro-AI
artifact is unavailable. Keep Render's health-check path on `/health` until the
production model artifact is deployed; then switch it to `/health/ready`.

The existing aggregate endpoint remains available for frontend cold-start
warming and operational diagnostics:
```bash
curl https://agro-os-api.onrender.com/health
```
Expected response:
```json
{
  "status": "healthy",
  "model_ready": true,
  "model_version": "agro-ai-rf-v1",
  "feature_schema_version": "agro-ai-features-v1",
  "artifact_source": "..."
}
```

### 9.2 API root
```bash
curl https://agro-os-api.onrender.com/
```
Expected response:
```json
{
  "message": "Welcome to AgroOS API",
  "version": "1.0.0",
  "environment": "production",
  "currency": "GHS",
  "docs": null
}
```

> When `APP_ENV=production`, `/docs` and `/redoc` are disabled. The `docs`
> field in the root response is `null`.

### 9.3 Interactive API docs (development only)

Open in browser when running locally or with `APP_ENV=development`:

```
http://localhost:8000/docs
```

In production (`APP_ENV=production`), `/docs` and `/redoc` return 404.

### 9.4 Farmers list (Agro-AI)
```bash
curl https://agro-os-api.onrender.com/api/farmers
```
Should return the synthetic `DEMO_FARMERS` list with Agro-AI scores.

### 9.5 CORS check
```bash
curl -H "Origin: https://agro-os.vercel.app" \
     -I https://agro-os-api.onrender.com/health
```
Response headers should include:
```
access-control-allow-origin: https://agro-os.vercel.app
```

### 9.6 Frontend loads
Open `https://agro-os.vercel.app` in a browser. The dashboard should load
and display farmer data from the backend (network tab — API calls should
return 200).

### 9.7 Webhook reachability (production)
Send a test event from the Moolre portal to
`https://agro-os-api.onrender.com/webhooks/moolre/payment`. Check Render logs for
a 200 response.

---

## 10. References

- `backend/main.py` — CORS configuration, router registration, health endpoints
- `backend/app/config.py` — settings loaded from `.env`
- `backend/.env.example` — full environment variable reference
- `README.md` — technology stack and monorepo structure
- `docs/scoring-systems.md` — Trust Score webhook flow
- `docs/data-privacy.md` — data handling for production deployments
