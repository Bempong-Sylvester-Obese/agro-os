# Golden Path Demo Script

This script keeps the hackathon demo focused on one complete story instead of a feature tour.

## Demo Goal

Show how AgroOS helps a farmer cooperative collect dues, reconcile payments, improve farmer creditworthiness, and disburse an input loan through Moolre-powered infrastructure.

## Demo Characters

- Cooperative: Kuapa Kokoo Demo Cooperative
- Farmer: Abena Mensah
- Admin: Cooperative finance officer
- Loan purpose: Fertilizer/input loan

## Pre-Demo State

- Abena is an active cooperative member.
- Her monthly dues are outstanding.
- Her current Trust Score is below the preferred loan approval threshold.
- The cooperative dashboard shows pending dues and pending input loan requests.

## Story Sequence

### 1. Admin Sends Reminder

The admin sends an SMS dues reminder to Abena and other farmers.

What to show:

- SMS campaign or notification action.
- Message text reminding farmers to pay dues through the Moolre merchant code.

### 2. Farmer Uses USSD

Abena dials the AgroOS/Moolre USSD merchant code from a feature phone.

Example menu:

```text
Welcome to AgroOS (Kuapa Kokoo)
1. Check Loan Balance
2. Pay Cooperative Dues
3. Request Input Loan
4. View Latest Announcements
5. Check Farm Status
Select option: 2
```

What to show:

- USSD menu mock or event log.
- Farmer selects dues payment.
- Payment is initiated through Moolre.

### 3. Moolre Confirms Payment

Moolre processes the payment and sends a webhook to the AgroOS backend.

What to show:

- Payment moves from pending to successful.
- Transaction reference is saved.
- Dashboard finance metrics update.

Fallback if sandbox access is delayed:

- Trigger a simulated webhook from the backend.
- Use seeded Moolre-like transaction data.

### 4. Trust Score Updates

AgroOS recalculates Abena's Trust Score after the successful dues payment.

What to show:

- Previous score.
- New score.
- Reason for score movement: dues paid on time.

Suggested explanation:

> AgroOS turns cooperative behavior into alternative credit data, helping farmers build trust even without formal banking history.

### 5. Admin Approves Input Loan

The admin reviews Abena's improved score and approves a fertilizer/input loan.

What to show:

- Farmer profile.
- Trust Score.
- Loan request details.
- Approval action.

### 6. Moolre Disburses Loan

AgroOS sends the approved loan through Moolre bulk disbursement or transfer.

What to show:

- Disbursement batch or transfer request.
- Recipient, amount, and status.
- Final successful payout confirmation.

## Closing Message

AgroOS is not just a payment app. It is cooperative infrastructure: member records, payment collection, USSD access, SMS communication, production tracking, and credit scoring working together for farmers who are often excluded from formal financial systems.

## Demo Fallbacks

- If Moolre sandbox access is unavailable, use a simulated Moolre webhook.
- If SMS sending is unavailable, show the prepared message and log it as a sent notification.
- If live USSD is unavailable, show the menu as a mock interaction and store it as a USSD session.
- If the Trust Score model is not trained, use the rules-based scoring formula.

---

## Presenter Runbook

This section is for whoever is at the keyboard during the pitch. It assumes
you already know the Story Sequence above — this is the mechanical "what do
I click / type" layer on top of it.

### Pre-Demo Checklist (do this 30–60 minutes before presenting)

- [ ] **Backend is running and healthy**
  ```bash
  npm run api
  curl http://localhost:8000/health
  ```
  Expect `{"status": "ok"}` (or equivalent 200 response). If this fails, the
  rest of the demo cannot proceed — fix this first.
- [ ] **Frontend is running and pointed at the right API**
  ```bash
  npm run dev
  ```
  Confirm `VITE_API_URL` in `.env` matches where the backend is running
  (`http://localhost:8000` for local).
- [ ] **`.env` is filled in from `backend/.env.example`** — at minimum
  `DATABASE_URL`, `SECRET_KEY`, `DEFAULT_SMS_SENDER_ID`. See
  [`docs/moolre-setup.md`](./moolre-setup.md) for Moolre-specific vars.
- [ ] **Decide Moolre mode for this presentation**, and know which fallback
  tier you're on:
  - **Tier 1 (best):** Live Moolre sandbox reachable, `ngrok` tunnel up,
    `MOOLRE_WEBHOOK_SECRET` set — real signed webhook round-trip.
  - **Tier 2 (fallback):** Sandbox/ngrok unavailable — use the manual
    webhook fallback in "Fallback: Simulating a Moolre Payment" below.
  - **Tier 3 (fallback):** Backend itself unreachable — narrate the story
    from the frontend demo-data fallback (`DEMO_FARMERS`/`DEMO_LOANS` in
    `frontend/src/api/*.js`) and be upfront that it's illustrative, not live.
- [ ] **Seed a demo farmer and cooperative** (see "Sample Farmer Reference"
  below — there is currently no one-command seed script, so this is a
  manual pre-flight step).
- [ ] **Log in to the dashboard once** before presenting so the login screen
  isn't the first thing judges see you fumbling with.
  Demo login: `kwabena@ashantifarmers.gh` / `harvest2026` (from
  `frontend/src/pages/LoginPage.jsx`).
- [ ] **Close/mute anything that could pop up** during screen share (Slack,
  email, notifications).

### Screen-by-Screen Click Path

The dashboard has six tabs in the left nav: **Overview, Members, Payments,
Loans, Trust & Agro-AI scores, SMS broadcasts** (plus Settings, not used in
the demo). Map the Story Sequence onto them like this:

| Story step | Tab | What you click / show | Judge one-liner |
|---|---|---|---|
| 1. Admin sends reminder | **SMS broadcasts** | Click "Send dues reminder" (pre-fills amount and due date automatically) | *"One click reaches every farmer with an outstanding balance — no manual calling."* |
| 2. Farmer uses USSD | *(narrated, not a tab)* | Show the USSD menu block from this doc, or a phone mockup/photo, while narrating Abena's session | *"She doesn't need a smartphone or data — this works on any GHS 10 feature phone."* |
| 3. Moolre confirms payment | **Payments**, then **Overview** | Show the transaction move from Pending → Paid in the Payments table, then point at the updated "Recent payments" card on Overview | *"The moment Moolre confirms, AgroOS reconciles it automatically — no admin re-entering numbers."* |
| 4. Trust Score updates | **Trust & Agro-AI scores** | Click Abena's row to open the score detail panel; point out Trust Score vs. Agro-AI credit score side by side | *"Her on-time payment just became creditworthiness data — that's the AgroCredit engine."* |
| 5. Admin approves loan | **Loans** | Find Abena's loan request, click **Approve** | *"The cooperative approves in seconds, backed by a real score instead of guesswork."* |
| 6. Moolre disburses loan | **Loans** | Click **Disburse** on the same loan; show status move to `disbursed` with a `moolre_transfer_ref` | *"Funds move straight to her wallet — the cooperative never touches cash."* |

Closing: return to **Overview** for the wide shot — dashboard cards, Top
Trust Scores, Agro-AI review queue — while delivering the Closing Message
above.

### Fallback: Simulating a Moolre Payment

There is currently **no dedicated demo/simulate endpoint** for this (that's
tracked separately in
[issue #16](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/16),
which is still open). Until #16 ships, use the real payment webhook route
directly:

1. Create a transaction with a known `moolre_reference` first (via the
   dashboard's dues flow, or directly):
   ```bash
   curl -X POST http://localhost:8000/transactions/ \
     -H "Content-Type: application/json" \
     -d '{
       "farmer_id": 1,
       "transaction_type": "dues",
       "amount": 120,
       "moolre_reference": "DEMO-REF-001"
     }'
   ```
2. Fire a webhook payload matching that reference at
   `POST /webhooks/moolre/payment` (shape taken from
   `backend/tests/test_webhooks.py`):
   ```bash
   curl -X POST http://localhost:8000/webhooks/moolre/payment \
     -H "Content-Type: application/json" \
     -d '{
       "status": 1,
       "code": "P01",
       "message": "Transaction Successful",
       "data": {
         "transactionid": "99887766",
         "externalref": "DEMO-REF-001",
         "amount": "120.00",
         "payer": "0552340001",
         "payee": "AgroOS"
       }
     }'
   ```
3. Refresh the **Payments** and **Trust & Agro-AI scores** tabs — the
   transaction should show `completed` and the Trust Score recalculation
   should be queued.

Notes:

- If `MOOLRE_WEBHOOK_SECRET` is unset in your `.env`, signature verification
  is skipped and the curl above will work as-is (dev-only behavior — see
  [`SECURITY.md`](../SECURITY.md)). If it **is** set, you'll need to compute
  a matching `X-Moolre-Signature` HMAC-SHA256 header, or temporarily unset
  the secret in your local `.env` for the demo.
- This fallback only covers the **payment** webhook. There is no simulate
  path for the **USSD** webhook — narrate that step as described in
  "Screen-by-Screen Click Path" above instead of trying to fake it live.
- Once issue #16 ships a real simulate endpoint or dashboard button, replace
  this section with that instead of the raw curl commands.

### Sample Farmer Reference — Abena Mensah

**Known gap:** AgroOS does not yet have an automated seed script
(`supabase/README.md` still describes seed data as future work). The
"Abena Mensah" persona currently only exists as hardcoded values in:

- `frontend/src/data/payments.js` and `DashboardMock.jsx` (frontend display
  mock — cooperative-facing ID `GH-0042`)
- `frontend/src/api/loans.js` `DEMO_FARMERS` (frontend API-fallback mock —
  numeric ID `1`)
- `backend/app/agro_ai/synthetic_data.py` (training data for the Agro-AI
  model, not a database record)

**None of these are automatically loaded into the live backend database.**
To have a real, queryable "Abena Mensah" for the demo, create her manually
before presenting:

```bash
# 1. Create the cooperative
curl -X POST http://localhost:8000/cooperatives/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Kuapa Kokoo Demo Cooperative", "location": "Kumasi, Ghana", "currency": "GHS"}'
# note the returned "id" — use it below as <coop_id>

# 2. Create the farmer
curl -X POST http://localhost:8000/farmers/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Abena Mensah",
    "phone": "0552340001",
    "cooperative_id": <coop_id>,
    "location": "Ashanti Region",
    "crop_type": "Maize",
    "acreage": 4.1
  }'
# note the returned "id" — this is <farmer_id>, used throughout the demo
# (frontend mocks assume this will be 1 on a fresh database)
```

Keep the returned `cooperative_id` and `farmer_id` handy — you'll need
`farmer_id` for the webhook fallback commands above and for checking
`GET /farmers/{id}/trust-score` if something looks off mid-demo.

*Follow-up:* a real `supabase/seed.sql` or a `scripts/seed_demo.py` that
creates this cooperative + Abena + a starter transaction in one command
would remove this manual step — worth its own issue if it isn't tracked
already.

### Timing Guide (5-minute pitch)

| Time | Segment |
|---|---|
| 0:00–0:30 | Problem framing — fragmented cooperative tools, unbanked farmers |
| 0:30–1:00 | Story 1: SMS reminder (**SMS broadcasts** tab) |
| 1:00–1:30 | Story 2: USSD payment (narrated) |
| 1:30–2:15 | Story 3: Payment confirmation (**Payments** → **Overview**) |
| 2:15–3:00 | Story 4: Trust Score update (**Trust & Agro-AI scores**) |
| 3:00–3:45 | Story 5–6: Loan approval + disbursement (**Loans**) |
| 3:45–4:30 | Closing message + platform breadth (back to **Overview**) |
| 4:30–5:00 | Buffer for questions / re-click anything that lagged |

If running short on time, cut Story 2 (USSD) to a single sentence rather
than skipping Trust Score or Loans — those two are the differentiators.
