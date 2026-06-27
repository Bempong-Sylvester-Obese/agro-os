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

## About AgroOS

AgroOS is a unified digital operating system built for African farmer cooperatives — replacing fragmented tools with a single platform for member management, financial operations, and production tracking.

The frontend dashboard is built with **Next.js**, **Tailwind CSS**, and **shadcn/ui**, giving cooperative administrators a clean, data-rich interface that replaces physical ledgers and manual record-keeping.

**Key dashboard capabilities:**
- Member profiles and cooperative standing
- Dues payment status and bulk disbursements
- SMS broadcasts for announcements and reminders
- Production tracking (expected vs. actual harvests)
- AgroCredit Trust Score monitoring per farmer

Designed with rural African realities in mind — farmers without smartphones interact via a native Moolre USSD menu, with their data flowing to the dashboard in real-time through payment webhooks. AgroOS is not just a management tool; it is the financial and operational infrastructure that connects unbanked rural farmers to formal cooperative systems.