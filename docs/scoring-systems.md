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
| **Data source** | Real DB records (transactions, loans, production, attendance) | Synthetic `DEMO_FARMERS` dataset |
| **Endpoint** | `GET /farmers/{id}/trust-score` | `GET /api/farmers`, `/api/agro-ai/*` |
| **Shown on dashboard?** | ❌ Not currently displayed | ✅ Shown on dashboard |
| **Updated by webhooks?** | ✅ Yes — Moolre payment webhook triggers recalculation | ❌ No |
| **Used by USSD?** | ✅ Yes — USSD option 5 reads DB trust score | ❌ No |

These two systems **do not share data**. They produce different scores for
the same farmer and are not interchangeable.

---

## System 1 — Trust Score (Rules-Based)

### What it is
The Trust Score is AgroOS's production-grade scoring engine. It is implemented
in `backend/app/services/trust_score_service.py` and computes a weighted score
from verified database records:

- **Transaction history** — payment regularity, dues compliance
- **Loan repayment** — on-time repayment rate
- **Production records** — farm output consistency
- **Attendance** — cooperative meeting participation

### When it updates
The Trust Score recalculates automatically when a Moolre payment webhook
fires — i.e. when a farmer pays cooperative dues through the USSD menu.

### Where it is used
- **USSD Option 5 ("Check Farm Status")** — reads and displays the DB trust
  score for the authenticated farmer
- **`/farmers/{id}/trust-score`** — REST endpoint for admin or integration use

### What it is NOT
The Trust Score is not currently visible on the web dashboard. This is a
known gap — see Roadmap below.

### Demo narration (Trust Score path)
> *"When the farmer pays dues through the USSD menu, Moolre fires a webhook
> to our FastAPI backend. The backend records the transaction, then
> recalculates the farmer's Trust Score using our rules engine — weighing
> payment history, loan repayment, production records, and attendance.
> The farmer can check their updated score by selecting Option 5 on the
> USSD menu."*

---

## System 2 — Agro-AI Score (Random Forest)

### What it is
Agro-AI is AgroOS's experimental ML scoring layer, implemented in
`backend/app/agro_ai/`. It uses a trained Random Forest classifier to predict
creditworthiness or risk tier for a farmer.

### Data source
Agro-AI currently runs on **`DEMO_FARMERS`** — a synthetic dataset hardcoded
for hackathon purposes. It does **not** read from the live database.

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
> synthetic dataset so judges can see the ML layer in action. In production,
> this model will train on verified DB records — the same data the Trust Score
> engine already uses."*

---

## Golden Path — What Updates After Dues Payment

This is the most important thing to get right during the demo narration.

**The Golden Path is:**

```
Farmer selects USSD Option 2 (Pay Cooperative Dues)
  → Moolre processes payment
    → Moolre fires webhook to /webhooks/moolre
      → FastAPI records Transaction in DB
        → trust_score_service.py recalculates Trust Score
          → Farmer selects USSD Option 5 (Check Farm Status)
            → Updated Trust Score is returned
```

**What does NOT update:** the dashboard Agro-AI score. Do not tell a judge
"the score on the dashboard updates after payment" — it does not.

**Safe demo narration sequence:**
1. Show the dashboard — narrate it as the Agro-AI ML layer
2. Demonstrate dues payment via USSD
3. Switch to USSD Option 5 to show the updated Trust Score
4. Explain that in production these two layers will merge (see Roadmap)

---

## USSD Option 5 — Demo Script Note

USSD Option 5 ("Check Farm Status") is backed by the **Trust Score engine**,
not Agro-AI. When demoing this option:

- The score returned is computed from DB transactions, loans, production, and
  attendance records
- It will reflect any dues payment made during the same demo session
- It will **not** match the score shown on the web dashboard (which is Agro-AI)

If a judge asks why the two numbers differ, the answer is:
> *"The dashboard shows our ML prediction layer running on a representative
> dataset. The USSD score is our rules-based engine reading live DB records.
> Merging these two into a unified score is on our roadmap."*

---

## Roadmap — Merging the Two Systems

The long-term architecture is a **single unified score** backed by DB facts
and optionally enhanced by the ML model. The path is:

### Phase 1 (Current — Hackathon)
- Trust Score: rules-based, DB-backed, webhook-triggered ✅
- Agro-AI: ML-based, synthetic data, dashboard display ✅
- No integration between the two

### Phase 2 (Post-Hackathon MVP)
- Feed real DB records into Agro-AI training pipeline
- Replace `DEMO_FARMERS` synthetic data with live farmer data
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
