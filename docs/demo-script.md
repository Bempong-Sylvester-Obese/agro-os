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
