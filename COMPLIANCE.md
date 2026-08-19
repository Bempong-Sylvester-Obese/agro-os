# AgroOS Compliance Policy

> **Status:** Production — Provider-Neutral Architecture
> **Last updated:** 2026-08
> **Maintainer:** AgroOS Core Team (Ramzy, Julien, Elvis, Sylvester)
>
> This document is a non-legal summary for cooperative administrators,
> partners, and auditors. It does not constitute legal advice. Before any
> production deployment or onboarding of real farmer data or funds, this
> policy must be reviewed by qualified Ghanaian legal counsel and, where
> relevant, by payment provider compliance teams.

---

## 1. Purpose

AgroOS is a cooperative management platform that touches farmer personal
data, cooperative finances, SMS/USSD communication, and third-party payment
rails. Operating in this space means AgroOS sits at the intersection of
several regulatory regimes in Ghana, not just data privacy. This policy is
the single index of what applies, what is currently in place, and what is
still outstanding — written so a partner or auditor can see our compliance
posture at a glance.

For the detailed data-handling policy (PII categories, retention, consent),
see [`docs/data-privacy.md`](docs/data-privacy.md). For vulnerability
handling and technical security controls, see [`SECURITY.md`](SECURITY.md).
This document sits above both and adds the regulatory areas specific to
being an agritech / cooperative-fintech platform.

---

## 2. Regulatory Framework

| Area | Governing Law / Body | Relevance to AgroOS |
|---|---|---|
| Data protection | Data Protection Act, 2012 (Act 843); Data Protection Commission (DPC) | Farmer PII, credit scores, SMS logs — see `docs/data-privacy.md` |
| Payment services | Payment Systems and Services Act, 2019 (Act 987); Bank of Ghana (BoG) | AgroOS itself is not a payment service provider — it integrates with licensed PSPs rather than holding or moving money directly |
| Anti-money laundering | Anti-Money Laundering Act, 2020 (Act 1044); Financial Intelligence Centre (FIC) | Cooperative dues, loans, and aggregate wallet balances create AML exposure once real money and real identities are involved |
| Electronic transactions | Electronic Transactions Act, 2008 (Act 772) | Consent, record-keeping, and validity of electronic/USSD transactions |
| Telecom / SMS | Electronic Communications Act, 2008 (Act 775); National Communications Authority (NCA) | Sender ID registration, unsolicited messaging rules |
| Cooperative societies | Co-operatives Societies Act, 2020 (Act 1148) | Governs how farmer cooperatives themselves are legally constituted; relevant to how AgroOS represents cooperative structure and admin authority in-app |
| Consumer protection | Consumer Protection principles under BoG/NCA guidelines | Transparent pricing, dispute handling, opt-out rights |

AgroOS does not claim compliance with all of the above today. This table
exists so gaps are visible and trackable rather than discovered later.

---

## 3. Payment Compliance

AgroOS does not hold a Payment Service Provider (PSP) or Dedicated
Electronic Money Issuer (DEMI) license, and is not attempting to become
one. Instead:

- All money movement (collections, disbursements, USSD payment prompts)
  is routed through **licensed payment providers**. AgroOS never custodies
  farmer or cooperative funds directly.
- Webhook-verified payment confirmations (HMAC-SHA256) are the system of
  record for whether a payment succeeded — see `SECURITY.md` § Webhook Security.
- AgroOS's obligation is to accurately reflect provider-confirmed
  transaction state, not to independently settle funds.
- The provider adapter layer (`backend/app/adapters/`) translates
  provider-specific payloads into normalized `PaymentEvent` domain objects,
  decoupling business logic from any single provider.

### 3.1 AML / KYC posture

- **Current:** No KYC is performed. All farmer records must be synthetic
  (see `docs/data-privacy.md` § 6).
- **Projected:** Farmer and cooperative-admin identity verification will be
  delegated to the payment provider's existing KYC flow where possible,
  rather than AgroOS building a parallel KYC system. Cooperative aggregate
  wallet balances and dues collection thresholds will need AML
  transaction-monitoring rules before real deployment — not yet implemented,
  tracked as a future issue.

---

## 4. Telecom Compliance (SMS / USSD)

- All outbound SMS uses the **provider-approved sender ID** only. Spoofed
  or unapproved sender IDs are prohibited and would violate NCA rules —
  see `docs/data-privacy.md` § 5.2.
- USSD menu flows run through the provider's short-code infrastructure;
  AgroOS does not operate its own short code.
- Consent is required before financial or credit-related SMS is sent —
  cooperative membership alone is not sufficient consent (§5.1 of the
  data privacy policy).

---

## 5. Cooperative Governance Alignment

AgroOS mirrors, but does not replace, the legal structure of a
cooperative society under Act 1148:

- Role scoping in-app (`admin`, `finance_officer`) reflects operational
  roles, not the formal governance roles (e.g. management committee,
  auditor) a registered cooperative is required to have.
- AgroOS is a record-keeping and communication tool for a cooperative's
  existing governance — it does not itself constitute the cooperative's
  legal registration, bylaws, or audit obligations to the Department of
  Co-operatives.
- Cross-cooperative data isolation (enforced at the API layer per
  `SECURITY.md`) reflects that each cooperative is a distinct legal
  entity, even where multiple cooperatives use the same AgroOS instance.

---

## 6. Consumer / Farmer Protection

- Pricing (see `/pricing`) is published and not conditional on
  undisclosed fees.
- Farmers have the right to know what data is collected and why
  (`docs/data-privacy.md` § 2–3) and to request deletion (§7).
- SMS opt-out must be honoured — implied consent from membership is
  explicitly not treated as sufficient for financial alerts.

---

## 7. Current Compliance Status Summary

| Item | Status |
|---|---|
| Data privacy policy documented | Done (`docs/data-privacy.md`) |
| Security policy & webhook verification (payments) | Done for payment webhook |
| USSD webhook signature verification | Done — shared-secret validation |
| Role-based access control (production) | Enforced — JWT scoped per cooperative |
| Supabase row-level security | Deployed — tenant-scoped RLS as defense-in-depth |
| Provider-neutral architecture | Done — payment/SMS behind port interfaces |
| AML/transaction monitoring | Not started — deferred to provider KYC + future issue |
| Data Protection Commission registration | Not applicable pre-launch; required before real farmer data |
| Legal review of this policy and data-privacy.md | Outstanding — required before production |

---

## 8. Contact

For questions, contact the AgroOS team via the project repository. A
designated compliance/DPO contact will be added ahead of any production
launch.

---

*AgroOS — Agricultural Cooperative Management Platform*
