# Supabase

This directory will contain the AgroOS database schema, migrations, and demo seed data.

## Planned Entities

- `cooperatives`
- `farmers`
- `farmer_profiles`
- `dues_payments`
- `transactions`
- `loans`
- `loan_disbursements`
- `disbursement_batches`
- `harvests`
- `announcements`
- `sms_messages`
- `ussd_sessions`
- `payment_webhook_events`
- `trust_scores`

## Initial Responsibilities

- Define tables for the Golden Path demo.
- Seed realistic cooperative and farmer records.
- Include payment, harvest, and loan data that can drive the dashboard and Trust Score.
- Store Moolre transaction references, payment statuses, transfer statuses, USSD session metadata, and webhook payload audit records.
- Keep schema changes reviewable so backend and frontend teammates can align on contracts.

## Moolre Data To Preserve

For reconciliation and demos, database records should preserve enough Moolre metadata to trace each financial action:

- Moolre payment or transaction reference.
- Farmer phone number and mobile money network when available.
- Payment method, amount, currency, and status.
- Webhook event type, received timestamp, and raw payload snapshot.
- Disbursement batch ID, recipient count, total amount, and status.
- SMS message reference and delivery status for reminders.
- USSD session ID, short code, selected menu path, network, and timestamp.

## Notes

For the first MVP, seed data should prioritize a strong demo story over exhaustive real-world coverage.
