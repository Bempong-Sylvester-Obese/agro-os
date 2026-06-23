# Agro-AI Evaluation And Readiness

This document tracks the AI-side work needed to move AgroCredit from a hackathon demo toward enterprise-grade operation.

## Current State

The current backend trains a Random Forest classifier on deterministic synthetic cooperative data and exposes score endpoints through FastAPI. This is enough to demonstrate the concept, but evaluation results on the synthetic dataset only prove that the model can approximate the synthetic label rule.

Production evaluation needs real outcomes from Supabase and Moolre flows, such as dues repayment, loan repayment, late repayment, default, and successful disbursement completion.

## Enterprise AI Gaps

- Reproducible training: training now has a dedicated CLI, but production should run it from CI or a controlled notebook/job.
- Real labels: synthetic labels must be replaced with real repayment or repayment-risk outcomes.
- Model artifacts: FastAPI can load a local `joblib` artifact, but the artifact should be promoted through a model registry.
- Decision auditability: local JSONL audit logging exists for development; production should persist this in Supabase with tenant and actor IDs.
- Explainability: current reasons are heuristic; production lending decisions should use a reviewed explainability approach and a model card.
- Monitoring: W&B captures offline evaluation; production still needs drift, latency, error, and score-distribution monitoring.
- Governance: threshold changes, feature schema changes, and model promotions should require review.

## Auth And Tenant Context

Auth is owned separately, but the AI endpoint already accepts optional `farmer_id`, `cooperative_id`, and `actor_id` fields on `POST /api/agro-ai/predict`. These fields are written into the prediction audit log when present, so auth can later populate them from the session and organization membership without changing the model contract.

## W&B Usage

Run training and evaluation from the backend package:

```bash
cd backend
python -m app.agro_ai.train --wandb-mode offline
```

Use online W&B after authenticating locally:

```bash
cd backend
wandb login
python -m app.agro_ai.train --wandb-mode online --wandb-project agro-os
```

The training command logs:

- model parameters
- dataset split metadata
- ROC AUC, PR AUC, accuracy, precision, recall, F1, and Brier score
- approval, manual-review, false-approval, and false-rejection rates
- threshold comparisons for scores `55`, `68`, and `82`
- confusion matrix
- feature importances
- model artifact

## Demo Versus Real Evaluation

Demo evaluation uses the synthetic generator in `backend/app/agro_ai/synthetic_data.py`. This is useful for validating the pipeline, W&B integration, and artifact loading.

Real evaluation should use Supabase-backed facts:

- farmer profile and cooperative membership history
- payment consistency and Moolre transaction history
- harvest and yield records
- prior loan repayment events
- outstanding balances and savings behavior
- final repayment outcome labels

The model should not be presented as production-grade credit risk scoring until it is evaluated against real outcomes and reviewed for calibration, bias, and explainability.

---

## Governance and Model Card

This document covers evaluation methodology and enterprise readiness gaps.
For the model card, decision thresholds, explainability policy, audit log
location, known limitations, and the promotion path from synthetic to
production labels, see [`docs/agro-ai-governance.md`](agro-ai-governance.md).

## Relationship to Trust Score

Agro-AI runs in parallel with the rules-based Trust Score engine. The two
systems currently use different data sources and serve different surfaces.
For a full comparison, the Golden Path demo flow, and the production
roadmap for merging the two, see [`docs/scoring-systems.md`](scoring-systems.md).
