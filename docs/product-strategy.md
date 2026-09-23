# AgroOS Product Strategy

> **Status:** Living document for the B2B product. The original hackathon
> framing (Moolre Startup Cup, July 2026) is archived under
> [`docs/archive/`](archive/). Provider names below are illustrative: the
> platform integrates payments, SMS, and USSD through provider-neutral ports
> (see [`architecture/adding-a-provider.md`](architecture/adding-a-provider.md)).

## Vision

AgroOS is the operating system for agricultural organisations in Ghana and,
over time, the wider region. It replaces paper ledgers, spreadsheets, and
manual mobile-money reconciliation with one platform that runs an
organisation's members or workers, money, production, communication, and
credit history, and that farmers can reach from a feature phone.

## Who We Sell To

AgroOS is sold business-to-business to the organisation, not to individual
farmers. Two organisation types are supported by the same codebase and are
distinguished by `organization_type`:

| | Cooperative (primary) | Solo Farm (secondary tier) |
|---|---|---|
| Customer | Cooperative societies registered under Act 1148: cocoa, cashew, shea, livestock, poultry, mixed producer groups | Independent farm owners employing wage labour |
| Buyer persona | Secretary / manager, finance officer, executive committee | Farm owner or manager |
| Core loop | Dues → trust score → input loans → produce settlement | Tasks → attendance → payroll |
| Farmer-side channel | USSD self-service (pay dues, request/repay loan, balances, announcements) | USSD for workers (attendance/payslips, planned) |
| Plans | `starter` (free), `growth`, `enterprise` — member-count bands | `solo` — worker-count bands |
| Spec | This document | [`solo-farm-product-spec.md`](solo-farm-product-spec.md) |

Larger customers (unions, apex bodies, aggregators) that operate several
cooperatives are served by an organisation layer with consolidated billing
([#237](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/237)).

## Value Proposition

For a cooperative's leadership:

1. **Collections without cash handling.** Dues obligations are defined once;
   farmers pay from their own phone via USSD and mobile money, and the ledger
   updates from the provider webhook, not from a clerk's notebook.
2. **Credit decisions from data the cooperative already has.** AgroCredit turns
   dues consistency, production records, attendance, and loan history into a
   transparent Trust Score that informs input-loan approvals.
3. **Transparent produce settlement.** Intake, aggregation, buyer sales, fee
   itemisation, and dual-approved payouts replace the spreadsheet handoff
   between collection centres and finance.
4. **Reach every member.** SMS and USSD work on the phones farmers actually
   own; nothing requires a smartphone or data bundle.
5. **Audit-ready records.** Every financial action is attributable to a user
   and role, with cross-cooperative isolation enforced by the API.

## Core Modules

| Module | What it does | Status |
|---|---|---|
| Member management | Farmer profiles, crop/animal/mixed production focus, membership standing, roles | Shipped |
| Finance hub | Dues obligations and reminders, farmer-initiated payments, loan request → approval → disbursement → repayment, provider wallet reconciliation | Shipped |
| Communications | SMS broadcasts and event-driven notifications with per-member consent | Shipped; consent tracking in [#247](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/247) |
| Production tracking | Unit-aware expected vs. actual output for crop, animal, and mixed producers | Shipped |
| AgroCredit | Trust Score (rules-based) and Agro-AI recommendation (ML) | Shipped; model trained on synthetic data until real labels exist (see [`agro-ai-governance.md`](agro-ai-governance.md)) |
| USSD access | Farmer self-service menu, identical across gateways | Shipped |
| Commerce & settlement | Intake, aggregation, buyer sales, dual-approved settlements, retryable payouts | Shipped for crops; animal/mixed in [#249](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/249) |
| Governance | Multi-role staff, invitations, attendance at meetings | Shipped; role model formalised in [#244](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/244) |
| Solo-farm operations | Workers, tasks, attendance, payroll | Shipped (MVP) |
| Billing | Plan catalogue, checkout, entitlements, subscription lifecycle | In progress: [#233](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/233)–[#237](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/237) |

## Business Model

Subscription pricing per organisation, billed monthly in GHS, with bands that
scale on the dimension the customer already thinks in (members for
cooperatives, workers for solo farms). The catalogue lives in
`backend/app/services/plans.py` and drives both the public pricing page and
server-side entitlements, so a limit shown to a customer is the limit that is
enforced.

Principles:

- No per-transaction take on farmer money. Provider fees are passed through
  transparently; AgroOS earns from the subscription.
- A free `starter` tier exists so a cooperative can digitise its member
  register before committing.
- Limits are enforced at the API (member count, worker count, SMS quota,
  feature flags), never only in the UI.

## Farmer Experience Principles

- **Feature-phone first.** Every farmer-facing flow must be completable over
  USSD and SMS; the dashboard is for staff.
- **The farmer initiates their own payments.** Staff define obligations; they
  cannot debit a farmer.
- **One menu everywhere.** The USSD menu is defined once in
  `UssdApplicationService`; gateway adapters only translate transport, so a
  farmer sees the same options regardless of network or aggregator.
- **Explainable credit.** The Trust Score is rules-based and inspectable; the
  ML recommendation is advisory and labelled as such.

## AgroCredit Roadmap

1. **Now:** rules-based Trust Score on real cooperative records; Agro-AI Random
   Forest trained on deterministic synthetic data, surfaced as an advisory
   recommendation with an explicit synthetic-data disclaimer.
2. **Next:** collect real repayment outcomes from live cooperatives as labels;
   evaluate against held-out cooperatives; publish model cards.
3. **Later:** retrain on real labels, calibrate per crop/region, and expose
   score history to farmers over USSD.

Governance, evaluation criteria, and the promotion path are in
[`agro-ai-governance.md`](agro-ai-governance.md) and
[`agro-ai-evaluation.md`](agro-ai-evaluation.md).

## Compliance and Data Protection

AgroOS processes farmer PII (names, phone numbers, transactions, credit
scores, SMS content). Current posture and open items are tracked in
[`COMPLIANCE.md`](../COMPLIANCE.md), [`SECURITY.md`](../SECURITY.md), and
[`data-privacy.md`](data-privacy.md). Before onboarding a first paying
cooperative with real farmer data:

- [ ] Register with Ghana's Data Protection Commission under Act 843
- [ ] Appoint and publish a Data Protection Officer contact
- [ ] Legal review of `data-privacy.md` and `COMPLIANCE.md` by Ghanaian counsel
- [ ] Per-member SMS consent recorded and honoured ([#247](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/247))

## Related Documents

- [`architecture.md`](architecture.md) — system architecture
- [`architecture/adding-a-provider.md`](architecture/adding-a-provider.md) — provider port/adapter guide
- [`architecture/tenancy-decision.md`](architecture/tenancy-decision.md) — tenant isolation decision and threat model
- [`api-contract.md`](api-contract.md) — frontend/backend contract
- [`deployment.md`](deployment.md) — deployment runbook
- [`solo-farm-product-spec.md`](solo-farm-product-spec.md) — solo-farm tier
