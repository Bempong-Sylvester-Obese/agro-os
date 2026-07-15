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

The cooperative has created the dues obligation; the admin only sends Abena and other farmers an SMS reminder. Each farmer initiates their own payment.

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
5. Complete Pending Payment
6. Repay Loan
Select option: 2
```

What to show:

- USSD menu mock or event log.
- Farmer selects dues payment.
- The farmer—not dashboard staff—initiates payment through Moolre.
- If Moolre requests OTP verification, the farmer completes it in the same
  phone channel; the dashboard never displays an OTP field.

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

- The completed payment in the dashboard.
- The recalculated Trust Score response from `GET /farmers/{id}/trust-score`
  if the API is part of the live demo.

Suggested explanation:

> AgroOS turns cooperative behavior into alternative credit data, helping farmers build trust even without formal banking history.

### 5. Admin Approves Input Loan

Abena submits a fertilizer/input loan from USSD. The request appears in the
Loans tab, where the admin reviews the request and approves or rejects it. The
admin does not log the request on her behalf.

What to show:

- Farmer profile.
- USSD-originated loan request details.
- Approval action with the agreed repayment due date.

### 6. Moolre Disburses Loan

AgroOS sends the approved loan through Moolre bulk disbursement or transfer.

What to show:

- Disbursement batch or transfer request.
- Recipient, amount, and status.
- Final successful payout confirmation.

### 7. AgroOS Reminds; Farmer Repays

AgroOS sends due-date reminders without creating a debit. Abena dials the
AgroOS code, chooses **Repay Loan**, and authorizes the Moolre payment on her
own phone. Staff monitor and reconcile the result from the dashboard.

### 8. Cooperative Sells Produce and Pays Farmers

Record deliveries from two farmers, including accepted weight and grade, then
place them in one aggregation batch. Record the buyer sale and buyer-payment
reference. A second authorized officer verifies that funds were received.

Preview the settlement before approval:

- accepted kilograms and gross entitlement for each farmer;
- cooperative fee, transport or quality adjustments, and any optional loan
  recovery;
- each farmer's final net payable;
- control totals proving sale proceeds reconcile to deductions and payouts.

Approve the settlement and execute the Moolre payout batch. Show that a failed
farmer transfer can be retried while successful transfers remain protected
from duplicate payment.

## Closing Message

AgroOS is not just a payment app. It is cooperative infrastructure: member records, payment collection, USSD access, SMS communication, production tracking, and credit scoring working together for farmers who are often excluded from formal financial systems.

## Demo Fallbacks

- If Moolre sandbox access is unavailable, use a simulated Moolre webhook.
- If SMS sending is unavailable, show the prepared message and log it as a sent notification.
- If live USSD is unavailable, show the menu as a mock interaction and store it as a USSD session.
- If the Trust Score model is not trained, use the rules-based scoring formula.

## Presenter Runbook

### Pre-flight checklist (5 minutes before pitch)

1. Backend running: `npm run api` — confirm `GET /health` returns healthy.
2. Frontend running: `npm run dev` — confirm dashboard loads at `http://localhost:5173`.
3. Seed data present: `GET /farmers/` should list **Abena Mensah** (DB id `1` when freshly seeded).
4. Pending dues: note Abena's pending transaction id from `GET /transactions/?status=pending`.
5. Moolre sandbox OR plan to use **USSD activity → Simulate payment webhook** in the dashboard.
6. Login: `admin@agroos.demo` / `demo1234` (backend) or local demo user from login page.

### Start commands

```bash
npm run setup:backend   # first time only
npm run setup:frontend  # first time only
npm run api             # terminal 1 — port 8000
npm run dev             # terminal 2 — port 5173
```

Set `VITE_API_URL=http://localhost:8000` in `frontend/.env` for local wiring.

### Screen-by-screen click path (~5 minutes)

| Step | Tab | Action | Judge one-liner |
|------|-----|--------|-----------------|
| 1 | SMS broadcasts | Send dues reminder to cooperative | "AgroOS nudges farmers to pay through familiar SMS channels." |
| 2 | USSD activity | Show menu log or dial *919*4020# | "Farmers without smartphones reach the cooperative through USSD." |
| 3 | USSD activity | Complete a live Moolre payment and refresh | "Moolre confirms payment and AgroOS updates records instantly." |
| 4 | Overview / Scores | Explain the API-backed Trust Score and dashboard Agro-AI score | "Every payment builds alternative credit data for farmers." |
| 5 | Loans | Approve Abena's input loan | "Cooperative admins review farmer-originated requests before funds move." |
| 6 | Payments | Show completed transaction + webhook audit | "Finance teams reconcile Moolre payments in one dashboard." |

### Fallback: USSD without live short code

```bash
curl -X POST "$VITE_API_URL/webhooks/moolre/ussd" \
  -H "Content-Type: application/json" \
  -d '{"sessionid":"demo-1","phone":"+233552341234","input":"2"}'
```

Then refresh **USSD activity** tab.

### Seed character reference

| Character | DB farmer id | Phone | Notes |
|-----------|--------------|-------|-------|
| Abena Mensah | 1 (when seeded first) | +233552341234 | Pending dues, loan requested |
| Kuapa Kokoo Demo Cooperative | cooperative id 1 | — | Sidebar name source |

If ids differ, use `GET /farmers/` and match by name.

### Recovery lines

- **API down:** "You're seeing our offline demo mode — the same UI works live once the API connects." (topbar shows Demo data)
- **Moolre sandbox delay:** "We'll simulate the webhook — this is the same code path production uses."
- **Score unchanged:** "Trust scores refresh every 15 seconds after webhook processing."

