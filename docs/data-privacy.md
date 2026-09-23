# AgroOS Data Privacy Policy

> This document covers data handling specifically. For the broader
> regulatory picture (payments, AML, telecom, cooperative law), see
> [`COMPLIANCE.md`](../COMPLIANCE.md) at the repo root.

> **Status:** Pre-production policy for the B2B product — pending legal review
> **Last updated:** 2026-09
> **Maintainer:** AgroOS Core Team
>
> ⚠️ This document is a non-legal summary for cooperative administrators,
> customers, and contributors. It does not constitute legal advice. Before
> onboarding real farmer data it must be reviewed by a qualified legal
> professional with knowledge of Ghanaian data protection law
> (tracked in `COMPLIANCE.md` §7).

---

## 1. Purpose

AgroOS collects and processes personal data as part of its cooperative
management platform. This policy describes what data is collected, why it is
collected, who may access it, and how it is handled in development/staging
environments (which hold only synthetic data) and in production (which holds
real cooperative and farmer data).

All contributors, operators, and cooperative administrators interacting with
AgroOS data are expected to understand and respect these guidelines.

---

## 2. Categories of Personal Data Collected

The following categories of personally identifiable information (PII) are
collected or processed by AgroOS:

### 2.1 Identity and Contact Data
- **Full name** (`Farmer.name`) — used to identify cooperative members
- **Phone number** (`Farmer.phone`) — primary contact channel; used
  for SMS communications and farmer lookup

### 2.2 Location Data
- **Farm location / region** (`Farmer.location` or associated cooperative
  region) — used for cooperative grouping, logistics, and reporting

### 2.3 Financial Data
- **Transaction records** (`Transaction` model) — includes amounts, dates,
  transaction types, and associated farmer IDs
- **Credit score** (`Farmer.trust_score` or derived scoring fields) —
  computed from transaction history; influences lending or input credit
  decisions within the cooperative

### 2.4 Communication Data
- **SMS message content** (`CommunicationLog` model) — outbound messages sent
  to farmers via the platform; may include personalized financial summaries,
  alerts, or cooperative notices
- **Sender ID** — messages sent through the Moolre-approved sender ID; no
  unauthorised sender IDs should be used

### 2.5 Inferred / Derived Data
- Any aggregated or AI-generated assessments (e.g., risk tier, repayment
  likelihood) derived from the above are also considered personal data under
  Ghanaian law and must be handled accordingly.

---

## 3. Purpose of Collection

Data is collected solely for the following purposes:

| Data Category         | Purpose                                                    |
|-----------------------|------------------------------------------------------------|
| Name, phone           | Farmer identity, communication, account lookup             |
| Location              | Cooperative grouping, regional reporting                   |
| Transactions          | Financial tracking, credit assessment, cooperative records |
| Credit score          | Input credit eligibility, cooperative risk management      |
| SMS / CommunicationLog | Farmer notification, financial summaries, alerts           |

Data will not be used for advertising, sold to third parties, or processed for
purposes outside of cooperative management without explicit consent.

---

## 4. Data Access and Administrative Scope

### 4.1 Enforcement
Production deployments require `AUTH_ENABLED=true` (the backend refuses to
start otherwise). Every request is scoped to the authenticated user's
cooperative by the API layer; see `SECURITY.md` → *Tenant Isolation* and
`docs/architecture/tenancy-decision.md`. Development and staging environments
may run with authentication disabled and **must therefore hold only synthetic
data** (Section 6).

### 4.2 Roles
Data access is governed by roles:

| Role                    | Permitted Access                                               |
|-------------------------|----------------------------------------------------------------|
| **Cooperative Admin**   | Full access to members in their cooperative only              |
| **Farmer (self)**       | View own profile, transactions, and received communications    |
| **Platform Operator**   | Aggregate/anonymised data; no direct PII access without audit  |
| **External Auditor**    | Read-only access to specific records upon authorisation        |

Cross-cooperative access is not permitted. Admins may not access farmer records
outside their assigned cooperative.

> Staff roles currently enforced by the API are `admin` and `finance_officer`
> (plus read-only USSD self-service for farmers). Formalising the full role
> set is tracked in [#244](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/244).
> Farmer self-service and auditor access run through the same
> cooperative-scoped API; there is no direct database access for any role.

---

## 5. SMS Consent and Sender ID

### 5.1 Consent
Before any SMS is sent to a farmer, that farmer must have:
- Voluntarily registered with the cooperative platform
- Been informed that they will receive SMS communications from the platform
- Had an opportunity to opt out

Implied consent from cooperative membership is not sufficient for financial
alerts or credit-related messages.

**How the platform enforces this** (implemented under
[#247](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/247)):

- Consent is stored per membership on `cooperative_memberships.sms_consent`
  and **defaults to off**. A member is only opted in when the cooperative
  explicitly records that the member agreed (the "Member agreed to receive SMS
  alerts" checkbox when adding or editing a member, or `sms_consent: true` on
  `POST /farmers/` / `PUT /farmers/{id}`).
- Every change is timestamped: `sms_consent_at` records when consent was last
  granted and `sms_opt_out_at` when it was last withdrawn. Dashboard changes
  are written to the admin audit log as `member.sms_consent_granted` /
  `member.sms_consent_withdrawn` with `source=dashboard`; USSD changes use the
  actor `ussd:<msisdn>` and `source=ussd`.
- Members can opt out or back in themselves without cooperative involvement
  from the USSD main menu (**8. SMS Alerts**) on either gateway.
- All member-addressed send paths check consent before contacting the SMS
  provider: dues reminders, payment confirmations, payment-action notices,
  loan rejections, loan repayment reminders, settlement statements,
  announcements and cooperative broadcasts. When a member has not consented,
  no provider call is made and a `CommunicationLog` row is written with
  `status = skipped_no_consent` and `recipients_count = 0`, so the decision is
  auditable. The reminder job counts these as skipped rather than failed.
- `send_single_sms` (ad-hoc operator messages to an arbitrary number) does
  not carry a membership and therefore cannot check membership consent; it
  must only be used for operationally necessary messages the recipient has
  requested.
- **Legacy rows.** Memberships created before migration
  `020_membership_consent_audit` kept the value they had (previously the
  column defaulted to on) and carry no `sms_consent_at` timestamp.
  Cooperatives should review those members and record consent explicitly;
  the dashboard shows an "SMS on / SMS off" tag per member to make this visible.

### 5.2 Sender ID
All outbound SMS must use the sender ID approved by the SMS provider and
registered with Ghana's National Communications Authority (NCA) for the
platform operator's legal entity. Use of unapproved or spoofed sender IDs is
prohibited.

### 5.3 Message Content
SMS content logged in `CommunicationLog` may include sensitive financial
figures (balances, credit scores, transaction amounts). This content must be
treated as financial PII and must not be displayed to unauthorised parties.

---

## 6. Demo and Sandbox Data

### 6.1 What is Demo Data
Demo data refers to the synthetic farmer profiles, fabricated transactions,
and generated communication logs inserted by the Golden Path seed
(`SEED_DEMO_DATA=true`) for development, staging, automated tests, and sales
demonstrations.

### 6.2 Rules for Demo Data
- All demo farmer names, phone numbers, and financial records **must be
  fictitious** and must not correspond to real individuals
- Phone numbers used in demo data must not be real, dialable numbers. Use
  formats that cannot be accidentally dialled (e.g., `+233 000 XXX XXXX`)
- SMS messages should not be sent to real phone numbers during demo or testing

### 6.3 Separation from Production Data
Production is identified by `APP_ENV=production`. In that mode the seed
never runs, the demo-reset API returns 404, and the purge CLI refuses without
an explicit flag (see `docs/api-contract.md` → *Demo data in production*).
Any environment holding real farmer data must run as a separate,
access-controlled instance from development and staging.

---

## 7. Data Retention and Deletion

### 7.1 Synthetic Data
Synthetic seed data carries no PII and may be reset or purged at any time
using the demo-reset workflow or `backend/scripts/purge_demo_data.py`.

### 7.2 Production Data
In production, the following retention periods apply (subject to legal
review):

| Data Type           | Proposed Retention                                         |
|---------------------|------------------------------------------------------------|
| Farmer profile      | Duration of cooperative membership + 2 years              |
| Transaction records | 7 years (financial record-keeping standard)                |
| Credit scores       | Recalculated on demand; historical snapshots retained 2 years |
| SMS logs            | 12 months rolling                                          |
| Deleted accounts    | Hard-deleted within 90 days of request                     |

Farmers or cooperative admins may request deletion of a farmer's profile. The
platform must support a deletion workflow before any production launch.

---

## 8. Ghana Data Protection Act — Summary Note

> ⚠️ This section is a high-level, non-legal summary for awareness only. It
> must not be relied upon as legal guidance. Seek qualified legal counsel before
> production deployment.

Ghana's **Data Protection Act, 2012 (Act 843)** governs the collection,
processing, and storage of personal data in Ghana. Key obligations relevant
to AgroOS include:

- **Registration**: Any entity processing personal data must register with the
  Data Protection Commission (DPC)
- **Lawful basis**: Processing must have a lawful basis — typically consent,
  contractual necessity, or legitimate interest
- **Purpose limitation**: Data collected for one purpose may not be used for
  another without fresh consent
- **Data subject rights**: Individuals have the right to access, correct, and
  request deletion of their personal data
- **Security obligation**: Data controllers must implement reasonable security
  measures against unauthorised access, loss, or destruction
- **Cross-border transfers**: Transfer of Ghanaian personal data outside Ghana
  requires adequate protection safeguards

AgroOS, if deployed at scale, would likely qualify as a **data controller**
under Act 843 and must register accordingly. The cooperative admins may also
qualify as data processors.

**Flagged for legal review prior to any non-demo deployment.**

---

## 9. Security Posture

Data privacy cannot be separated from security. For current security
commitments, known vulnerabilities, and disclosure procedures, see
[`SECURITY.md`](../SECURITY.md).

Particular areas of intersection:
- API endpoints that return farmer PII must require authentication (tracked)
- Financial transaction endpoints must be rate-limited
- SMS logs must not be exposed in any public or unauthenticated endpoint
- Credit score fields must not appear in list views visible to other farmers

---

## 10. Contact and Policy Updates

This policy is reviewed whenever data handling changes; substantive changes
are tracked through GitHub issues on the project repository.

For questions, contact the AgroOS team via the project repository. A
designated Data Protection Officer (DPO) contact for data access and deletion
requests will be published here before any production launch.

---

*AgroOS — Agricultural Cooperative Management Platform*
