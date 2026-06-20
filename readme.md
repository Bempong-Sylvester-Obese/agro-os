# AgroOS

**The Digital Infrastructure and Operating System for African Farmer Cooperatives.**

Built for the **Moolre Cup Hackathon**, AgroOS shifts the conversation from fragmented agricultural apps to a unified ecosystem. It empowers farmer organizations to manage members, process bulk disbursements, and generate AI-driven credit scores using offline-first Moolre USSD integration.

By bridging the gap between unconnected rural farmers and formal financial ecosystems, AgroOS provides enterprise-grade infrastructure tailored for the agricultural value chain.

---

## Core Features

* **Member Management (CRM):** Centralized dashboard replacing physical ledgers to track farmer locations, crop types, acreage, and cooperative standing.
* **Moolre Finance Hub:** Automated dues collection and bulk loan disbursements powered by Moolre's payment infrastructure.
* **Cooperative Communications:** SMS broadcasts for dues reminders, meeting notices, and payment confirmations.
* **AgroCredit AI:** A machine learning engine (Scikit-learn) that synthesizes cooperative data, payment consistency, and historical crop yields to generate a dynamic **Farmer Trust Score**.
* **Native USSD Access:** Offline-first interaction allowing farmers to dial a native Moolre Merchant Code to pay dues and check balances without needing internet access or a smartphone.
* **Production Tracking:** Data logging for expected vs. actual harvests, providing actionable insights for cooperative leaders.

---

## Technology Stack

* **Frontend:** Vite, React, custom CSS
* **Backend API & Webhooks:** Python, FastAPI
* **Database:** Supabase (PostgreSQL)
* **Payments, USSD & Messaging Infrastructure:** Moolre APIs
* **AI / Machine Learning:** Scikit-learn
* **Deployment:** Vercel (Frontend), Render (Backend)

---

## Monorepo Structure

```text
agroos/
+-- backend/                   # FastAPI application and API contracts
|   +-- README.md
+-- docs/                      # Product strategy and planning notes
|   +-- product-strategy.md
+-- frontend/                  # Next.js web dashboard
|   +-- README.md
+-- supabase/                  # Database schema, migrations, and seed data
|   +-- README.md
+-- .env.example
+-- .gitignore
+-- readme.md

```

---

## Moolre Integration Focus

AgroOS is designed around the Moolre products that best fit farmer cooperatives:

* **Payment Collection:** Collect cooperative dues and other member payments through mobile money, USSD merchant codes, or hosted payment links.
* **USSD Service:** Give feature-phone farmers an offline-first menu for dues payment, loan checks, announcements, and farm status.
* **Bulk Disbursement / Transfers:** Send approved input loans, supplier payments, or cooperative payouts to many recipients.
* **SMS:** Send dues reminders, meeting notices, weather alerts, and payment confirmations.
* **Payment Webhooks:** Receive real-time payment updates so AgroOS can reconcile transactions and update Trust Scores.
* **Transaction & Status APIs:** Check wallet/account status, list transactions, and verify payment or transfer outcomes.

Resources:

* [Moolre API Documentation](https://docs.moolre.com/#/quickstart)
* [Moolre Products Overview](https://moolre.com/#products)

---

## Getting Started

This repository is currently initialized as a team scaffold. The implementation folders are intentionally lightweight so each teammate can build their assigned area from a shared structure.

### Prerequisites

* Node.js (v18+)
* Python (3.10+)
* Supabase CLI (optional, for local DB management)
* Moolre Sandbox access and API credentials

### 1. Clone and Configure

1. Copy `.env.example` to your local environment file when implementation work begins.
2. Read `docs/product-strategy.md` for the product vision and Golden Path demo.
3. Choose a feature branch before making changes.

### 2. Local Development

From the repository root:

```bash
npm run setup:backend
npm run setup:frontend
npm run api
npm run dev
```

Use `npm run build` from the repository root to build the Vite frontend.

### 3. Team Work Areas

* `frontend/` owns the cooperative admin dashboard.
* `backend/` owns FastAPI routes, webhook handling, and Trust Score logic.
* `supabase/` owns schema, migrations, and demo seed data.
* `docs/` owns product strategy and shared planning notes.

---

## The AgroCredit AI Engine

For the hackathon MVP, AgroCredit now includes `agro-ai`: a Scikit-learn Random Forest model trained on deterministic synthetic cooperative data. It uses dues consistency, payment timeliness, historical crop yields, cooperative attendance, loan history, outstanding balances, and savings behavior to generate an administrator-friendly credit-worthiness recommendation.

When a farmer makes a USSD payment via Moolre, a webhook should trigger the FastAPI backend to record the transaction and recalculate their Trust Score in Supabase.

---

## Contribution Guidelines

To ensure rapid development and zero merge conflicts during the hackathon:

1. **Never push directly to `main`.**
2. Branch naming convention: `feat/feature-name`, `fix/bug-name`, `docs/update-name`.
3. Ensure backend code passes `ruff` linting and frontend code passes `eslint` before opening a Pull Request.