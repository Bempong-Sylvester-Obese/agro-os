# AgroOS Data Privacy Policy

> **Status:** Draft — Hackathon Scope (Moolre Startup Cup, July 2026)
> **Last updated:** 2026-06
> **Maintainer:** AgroOS Core Team (Ramzy, Julien, Elvis, Sylvester)
>
> ⚠️ This document is a non-legal summary for cooperative administrators and
> hackathon demo evaluators. It does not constitute legal advice. Before any
> production deployment or onboarding of real farmer data, this policy must be
> reviewed by a qualified legal professional with knowledge of Ghanaian data
> protection law.

---

## 1. Purpose

AgroOS collects and processes personal data as part of its cooperative
management platform. This policy describes what data is collected, why it is
collected, who may access it, and how it is handled — both in the current
hackathon/demo environment and in a projected production context.

All team members, demo users, and cooperative administrators interacting with
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

### 4.1 Current Scope (Hackathon / Demo)
During the Moolre Startup Cup demo phase, the system has no enforced
authentication or role-based access control. Any user with access to the
running demo can view all data. **Only synthetic or anonymised demo data
should be used in this environment.** See Section 6.

### 4.2 Projected Production Scope
In a production deployment, data access will be governed by roles:

| Role                    | Permitted Access                                               |
|-------------------------|----------------------------------------------------------------|
| **Cooperative Admin**   | Full access to members in their cooperative only              |
| **Farmer (self)**       | View own profile, transactions, and received communications    |
| **Platform Operator**   | Aggregate/anonymised data; no direct PII access without audit  |
| **External Auditor**    | Read-only access to specific records upon authorisation        |

Cross-cooperative access is not permitted. Admins may not access farmer records
outside their assigned cooperative.

> 🔧 Auth implementation is tracked as a future GitHub issue. Until RBAC is
> implemented and tested, the system must not be used with real farmer data.

---

## 5. SMS Consent and Sender ID

### 5.1 Consent
Before any SMS is sent to a farmer, that farmer must have:
- Voluntarily registered with the cooperative platform
- Been informed that they will receive SMS communications from the platform
- Had an opportunity to opt out

Implied consent from cooperative membership is not sufficient for financial
alerts or credit-related messages.

### 5.2 Sender ID
All outbound SMS must use the **Moolre-approved sender ID** configured for
the hackathon. Use of unapproved or spoofed sender IDs is prohibited and may
violate Ghana's National Communications Authority (NCA) regulations.

In production, the registered sender ID must correspond to the platform
operator's legally registered entity name.

### 5.3 Message Content
SMS content logged in `CommunicationLog` may include sensitive financial
figures (balances, credit scores, transaction amounts). This content must be
treated as financial PII and must not be displayed to unauthorised parties.

---

## 6. Demo and Sandbox Data

### 6.1 What is Demo Data
Demo data refers to synthetic farmer profiles, fabricated transactions, and
generated communication logs used solely for evaluation and demonstration
purposes during the hackathon.

### 6.2 Rules for Demo Data
- All demo farmer names, phone numbers, and financial records **must be
  fictitious** and must not correspond to real individuals
- Phone numbers used in demo data must not be real, dialable numbers. Use
  formats that cannot be accidentally dialled (e.g., `+233 000 XXX XXXX`)
- SMS messages should not be sent to real phone numbers during demo or testing

### 6.3 Separation from Production Data
The demo/sandbox environment must be clearly labelled (e.g., `NODE_ENV=demo`
or equivalent). Any production or pilot environment with real farmer data must
run in a separate, access-controlled instance.

---

## 7. Data Retention and Deletion

### 7.1 Hackathon Scope
All demo data generated during the Moolre Startup Cup will be deleted within
**30 days of the final judging date** (estimated: August 2026), unless retained
for academic or retrospective documentation with all PII removed.

### 7.2 Production Scope (Projected)
In production, the following retention periods are proposed:

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

This policy will be updated as the platform matures beyond the hackathon phase.

For questions during the Moolre Startup Cup period, contact the AgroOS team
via the project repository or Moolre hackathon communication channels.

For future production inquiries regarding data access or deletion requests,
a designated Data Protection Officer (DPO) contact will be added here.

---

*AgroOS — Agricultural Cooperative Management Platform*
*Moolre Startup Cup 2026 | Team: Ramzy · Julien · Elvis · Sylvester*
