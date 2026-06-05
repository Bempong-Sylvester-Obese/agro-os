# Frontend

The frontend will be the cooperative administrator dashboard for AgroOS.

## Planned Stack

- Next.js App Router
- React
- Tailwind CSS
- shadcn/ui

## Initial Responsibilities

- Dashboard overview for cooperative activity.
- Member list and farmer profile views.
- Finance view for dues, loans, and disbursements.
- Production tracking view for expected and actual harvests.
- Demo-friendly Golden Path screens that show payment and Trust Score updates.

## Moolre-Inspired Dashboard Areas

The Moolre product pages provide useful patterns for the admin dashboard:

- Wallet and finance overview: wallet balance, total collections, total disbursements, and transaction counts.
- Payment collection: dues received, outstanding dues, payment methods, and payment statuses.
- USSD activity: recent sessions, phone numbers, networks, and selected menu actions.
- Bulk disbursement: loan payout batches, recipients, total amount, and payout status.
- SMS campaigns: reminders sent, delivery status, recipients, and campaign history.
- Transaction reconciliation: successful, pending, and failed payment summaries.

Reference: [Moolre Products Overview](https://moolre.com/#products).

## API Contract

The frontend should call the FastAPI backend through `NEXT_PUBLIC_API_URL`.

During early development, mocked data is acceptable as long as the expected response shapes are documented before backend integration.
