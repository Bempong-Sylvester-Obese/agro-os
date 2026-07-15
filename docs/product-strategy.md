# AgroOS Product Strategy

Prepared for the Moolre Cup Hackathon team.

## Vision

AgroOS is the digital operating system for African farmer cooperatives. Instead of building a single-purpose payment app, the product unifies member management, Moolre-powered financial flows, production tracking, communication, and creditworthiness scoring into one cooperative admin platform.

## Target Users

The first users are cooperative administrators who manage large groups of farmers and currently rely on paper ledgers, spreadsheets, and manual payment reconciliation.

Example cooperative segments:

- Large cocoa cooperatives handling high-volume member records and payouts.
- Mid-sized farmer unions managing loans, crop production, and dues.
- Certified producer groups that need traceability, compliance records, and direct market visibility.

## Core Modules

- Member Management: farmer profiles, location, crop type, acreage, cooperative standing, and membership status.
- Finance Hub: Moolre-powered dues collection, loan disbursement, supplier payments, and transaction tracking.
- Communication: SMS announcements for dues reminders, meetings, weather alerts, and payment notifications.
- Production Tracking: expected harvest, actual harvest, crop type, acreage, and yield history.
- AgroCredit: trust score generation from alternative cooperative data.
- USSD Access: feature-phone access for farmers without smartphones or reliable internet.

## Moolre Product Mapping

Moolre's platform includes payment collection, USSD payments, bulk disbursement, SMS, WhatsApp, storefront, sales, and API services. AgroOS should focus on the services that directly support farmer cooperative operations:

- Payment Collection: cooperative dues, member contributions, and other receivables.
- USSD Service: offline farmer access through merchant codes and menu-based interactions.
- Bulk Disbursement / Transfers: input loans, supplier payments, and cooperative payouts.
- SMS: reminders, announcements, confirmations, and repayment notifications.
- API Service: backend integration for payment initiation, payment status, transfer initiation, transfer status, transaction listing, and payment webhooks.

References:

- [Moolre API Documentation](https://docs.moolre.com/#/quickstart)
- [Moolre Products Overview](https://moolre.com/#products)

## AgroCredit Trust Score

The first MVP should use a transparent scoring formula before introducing a trained ML model. This keeps the hackathon demo deterministic and easy to explain.

Primary inputs:

- Dues payment consistency: high importance because it reflects financial discipline.
- Historical crop yields: high importance because it indicates production capacity and repayment potential.
- Cooperative attendance: medium importance because it signals engagement and access to training.

## USSD Menu Concept

```text
Welcome to AgroOS (Kuapa Kokoo)
1. Check Loan Balance
2. Pay Cooperative Dues (Moolre)
3. Request Input Loan
4. View Latest Announcements
5. Complete Pending Payment
Select option: _
```

## Golden Path Demo

1. A farmer receives an SMS reminder that monthly cooperative dues are required.
2. The farmer dials the USSD code and pays dues through Moolre.
3. Moolre sends a payment webhook to the FastAPI backend.
4. The backend records the transaction and recalculates the farmer's Trust Score.
5. The admin dashboard updates with the new payment and higher Trust Score.
6. The farmer submits a fertilizer/input loan request through USSD.
7. A cooperative leader approves or rejects the request in the dashboard.
8. An approved payout is sent back to the farmer through Moolre.

## MVP Principle

Build the smallest complete system that tells the end-to-end story. A simulated Moolre webhook and rules-based Trust Score are acceptable for the first version if real sandbox access or ML training takes too long.

---

## Compliance and Data Privacy

AgroOS processes personally identifiable information (PII) belonging to
farmers, including names, phone numbers, financial transactions, credit
scores, and SMS message content.

### Current Status (Hackathon)
- A data privacy policy covering PII categories, access scope, demo data
  rules, SMS consent, and retention windows has been documented at
  [docs/data-privacy.md](data-privacy.md)
- Only synthetic demo data may be used in the current build

### Pre-Production Dependencies
- [ ] Implement RBAC before onboarding real farmers
- [ ] Register with Ghana's Data Protection Commission (DPC) under Act 843
- [ ] Appoint a Data Protection Officer (DPO) and publish contact details
- [ ] Legal review of docs/data-privacy.md by qualified Ghanaian counsel

> See [docs/data-privacy.md](data-privacy.md) for the full policy.
