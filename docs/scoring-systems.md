# AgroOS Scoring Systems

> **Status:** Hackathon Reference Doc — Moolre Startup Cup (July 2026)
> **Maintainer:** AgroOS Core Team
> **Last updated:** 2026-06

This document explains the two scoring systems that exist in AgroOS, when
each one applies, and what the demo team should say during narration.

---

## Overview

AgroOS currently has **two independent scoring engines** running in parallel:

| | Trust Score | Agro-AI Score |
|---|---|---|
| **Engine** | Rules-based weighted formula | Random Forest ML model |
| **Data source** | Real DB records (transactions, loans, production, attendance) | DB records when present; synthetic fallback otherwise |
| **Endpoint** | `GET /farmers/{id}/trust-score` | `GET /api/farmers`, `/api/agro-ai/*` |
| **Shown on dashboard?** | ❌ Not currently displayed | ✅ Shown on dashboard |
| **Updated by webhooks?** | ✅ Yes — Moolre payment webhook triggers recalculation | ❌ No |
| **Used by USSD?** | ❌ No — Option 5 completes pending payments | ❌ No |

These systems use different formulas and remain non-interchangeable. For a DB
member they now draw from the same operational history, but only the Trust
Score is persisted and recalculated by payment webhooks.

---

## System 1 — Trust Score (Rules-Based)

### What it is
The Trust Score is AgroOS's production-grade scoring engine. It is implemented
in `backend/app/services/trust_score_service.py` and computes a weighted score
from verified database records:

- **Transaction history** — payment regularity, dues compliance
- **Loan repayment** — on-time repayment rate
- **Production records** — crop or animal completion and output consistency
- **Attendance** — cooperative meeting participation

### When it updates
The Trust Score recalculates automatically when a Moolre payment webhook
fires — i.e. when a farmer pays cooperative dues through the USSD menu.

### Where it is used
- **`/farmers/{id}/trust-score`** — REST endpoint for admin or integration use
- **Backend member records** — the current rules-based score is persisted for
  API and integration use, but is not yet rendered in the dashboard

### What it is NOT
The current feature-phone menu does not expose a score lookup. Option 5 is
reserved for completing a pending payment privately on the farmer's phone.

### Demo narration (Trust Score path)
> *"When the farmer pays dues through the USSD menu, Moolre fires a webhook
> to our FastAPI backend. The backend records the transaction, then
> recalculates the farmer's Trust Score using our rules engine — weighing
> payment history, loan repayment, production records, and attendance. The
> updated score is available through the cooperative's Trust Score API."*

---

## System 2 — Agro-AI Score (Random Forest)

### What it is
Agro-AI is AgroOS's experimental ML scoring layer, implemented in
`backend/app/agro_ai/`. It uses a trained Random Forest classifier to predict
creditworthiness or risk tier for a farmer.

### Data source
Agro-AI assessments are built from cooperative-scoped DB members and their
payment, production, attendance, and loan records. If demo fallback is allowed
and a requested member is not in the DB, the API can use `DEMO_FARMERS`.
Training data remains synthetic, so this is still a demonstration model rather
than a production credit model.

Unified expected/actual production quantities feed the existing
`yield_performance` feature, and animal scale is normalized into the existing
`acreage` slot. This intentionally preserves the exact
`agro-ai-features-v1` names and order so deployed v1 artifacts remain loadable.
The legacy names describe artifact inputs, not a crop-only product limitation.

### Where it is used
- **Web dashboard** — the score shown on the farmer profile card is the
  Agro-AI score
- **`/api/agro-ai/*`** endpoints — ML inference routes
- **`/api/farmers`** — farmer list with Agro-AI score attached

### What it is NOT
Agro-AI scores are not updated by webhooks. Paying dues does not change the
Agro-AI score. This means the dashboard score will not reflect demo
transactions in real time.

### Demo narration (Agro-AI path)
> *"The dashboard shows an Agro-AI score — this is our Random Forest model's
> creditworthiness prediction. In this demo build it runs on a representative
> synthetic training set so judges can see the ML layer in action. Live
> assessments normalize verified cooperative records into that model's stable
> v1 feature contract. Production use still requires training and validation
> against real repayment outcomes."*

---

## Golden Path — What Updates After Dues Payment

This is the most important thing to get right during the demo narration

**The Golden Path is:**

```
Farmer selects USSD Option 2 (Pay Cooperative Dues)
  → Moolre processes payment
    → Moolre fires webhook to /webhooks/moolre
      → FastAPI records Transaction in DB
        → trust_score_service.py recalculates Trust Score
          → Updated Trust Score is available from the REST API
```

**What does NOT update:** the dashboard Agro-AI score. Do not tell a judge
"the score on the dashboard updates after payment" — it does not.

**Safe demo narration sequence:**
1. Show the dashboard — narrate it as the Agro-AI ML layer
2. Demonstrate dues payment via USSD
3. Explain that the recalculated Trust Score is available through the REST API
4. Explain how this rules layer complements Agro-AI (see Roadmap)

---

## USSD Option 5 — Payment Completion

Option 5 lists payment requests tied to the caller's registered membership.
If Moolre requires TP14 verification, the farmer enters the OTP in this USSD
session. It does not display a score and never asks cooperative staff to relay
the OTP.

---

## Roadmap — Merging the Two Systems

The long-term architecture is a **single unified score** backed by DB facts
and optionally enhanced by the ML model. The path is:

### Phase 1 (Current — Hackathon)
- Trust Score: rules-based, DB-backed, webhook-triggered ✅
- Agro-AI: ML-based, synthetic-trained, DB-backed inference with demo fallback ✅
- Independent formulas and update lifecycles

### Phase 2 (Post-Hackathon MVP)
- Feed real repayment outcomes into the Agro-AI training pipeline
- Retain synthetic records only as an explicit demo fallback
- Expose unified score on dashboard (currently shows Agro-AI only)

### Phase 3 (Production)
- Single `/farmers/{id}/score` endpoint returning a unified score
- ML model retrained periodically on accumulated DB history
- Trust Score weights tunable by cooperative admin
- Full audit trail of score changes tied to transactions

---

## References

- `backend/app/services/trust_score_service.py` — Trust Score engine
- `backend/app/agro_ai/` — Random Forest ML model and inference routes
- `docs/product-strategy.md` — rules-first MVP principle
- `docs/agro-ai-evaluation.md` — Agro-AI model evaluation and rationale
- `docs/data-privacy.md` — handling of farmer scores as PII
