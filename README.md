# AgroOS

**The Digital Infrastructure and Operating System for African Farmer Cooperatives.**

AgroOS is a B2B management platform for Ghanaian agricultural organisations. Cooperatives use it to run members, dues, input loans, produce settlement, communications, and AgroCredit scoring; independent **solo farms** use the same platform for workers, tasks, attendance, and payroll (see [`docs/solo-farm-product-spec.md`](docs/solo-farm-product-spec.md)). Farmers reach it from any feature phone over USSD and SMS.

Payments, SMS, and USSD are integrated through provider-neutral ports; the current adapters target Moolre and Africa's Talking. Product framing lives in [`docs/product-strategy.md`](docs/product-strategy.md).

---

## Core Features

* **Member Management (CRM):** Centralized dashboard replacing physical ledgers to track crop, animal, or mixed production profiles and cooperative standing.
* **Finance Hub:** Cooperative-defined dues obligations and reminders, farmer-initiated dues payments, and bulk loan disbursements via integrated payment providers.
* **Cooperative Communications:** SMS broadcasts for dues reminders, meeting notices, and payment confirmations.
* **AgroCredit AI:** A machine learning engine (Scikit-learn) that synthesizes cooperative data, payment consistency, and historical production output to generate a dynamic **Farmer Trust Score**.
* **Native USSD Access:** Offline-first interaction allowing farmers to dial a USSD short code to pay dues and check balances without needing internet access or a smartphone.
* **Production Tracking:** Unit-aware expected vs. actual records for crop, animal, and mixed producers.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Vite, React, custom CSS |
| Backend API & Webhooks | Python, FastAPI |
| Database | Supabase (PostgreSQL) |
| Payments & USSD | Provider adapters (currently Moolre) |
| AI / Machine Learning | Scikit-learn |
| Deployment | Vercel (Frontend), Render (Backend) |

---

## Architecture

AgroOS follows a **ports-and-adapters** architecture. Payment and SMS providers are abstract behind port interfaces, with concrete adapters that translate provider-specific APIs into domain-normalized operations. See [`docs/architecture.md`](docs/architecture.md) for the full architecture document, [`docs/architecture/adding-a-provider.md`](docs/architecture/adding-a-provider.md) to integrate a new payment/SMS/USSD provider, and [`docs/architecture/tenancy-decision.md`](docs/architecture/tenancy-decision.md) for the tenant-isolation model.

```
┌─────────────────────────────────────────────────┐
│                  Frontend (Vite + React)         │
└────────────────────┬────────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────────┐
│              FastAPI Backend                     │
│  Routes → Services → Domain → Provider Ports    │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Payment  │  │   SMS    │  │   USSD   │      │
│  │ Provider │  │ Provider │  │ Adapters │      │
│  │  Port    │  │  Port    │  │          │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │              │             │             │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐      │
│  │ Provider │  │ Provider │  │ Gateway  │      │
│  │ Adapters │  │ Adapters │  │ Adapters │      │
│  └──────────┘  └──────────┘  └──────────┘      │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│          PostgreSQL (Supabase)                   │
└─────────────────────────────────────────────────┘
```

---

## Monorepo Structure

```text
agro-os/
├── backend/                   # FastAPI application and API contracts
├── docs/                      # Product strategy, architecture, runbooks
│   ├── architecture.md        # System architecture document
│   ├── architecture/          # Provider guide, tenancy decision record
│   └── archive/               # Historical hackathon material (not maintained)
├── frontend/                  # Vite + React web dashboard
├── supabase/                  # Database schema, migrations, and seed data
├── .env.example               # Root environment reference
└── README.md
```

---

## Getting Started

### Prerequisites

* Node.js (v18+)
* Python (3.10+)
* Supabase CLI (optional, for local DB management)
* Payment provider sandbox credentials

### 1. Clone and Configure

1. Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env` for local development.
2. Read `docs/product-strategy.md` for the product vision.
3. Choose a feature branch before making changes.
4. For deeper backend setup and API details, see `backend/README.md`.

### Environment Files

- **`backend/.env`**: Runtime env file for the FastAPI backend. Copy from `backend/.env.example`.
- **`frontend/.env`**: Local env file for the Vite app. Copy from `frontend/.env.example` (e.g., `VITE_API_URL=http://localhost:8000`, `VITE_COOPERATIVE_ID=1`).
- **Root `.env` / `.env.example`**: Shared reference for workspace-level variables.

### 2. Local Development

From the repository root:

```bash
npm run setup:backend
npm run setup:frontend
npm run api
npm run dev
```

Additional root scripts:

```bash
npm run test:backend   # Run backend pytest suite
npm run train:ai       # Train/evaluate Agro-AI model
npm run build          # Build Vite frontend
```

Reference docs:

| Topic | Document |
|---|---|
| Product framing, customers, roadmap | [`docs/product-strategy.md`](docs/product-strategy.md) |
| System architecture | [`docs/architecture.md`](docs/architecture.md) |
| Adding a payment / SMS / USSD provider | [`docs/architecture/adding-a-provider.md`](docs/architecture/adding-a-provider.md) |
| Frontend ↔ backend API contract | [`docs/api-contract.md`](docs/api-contract.md) |
| Backend endpoints, env vars, tests | [`backend/README.md`](backend/README.md) |
| Deployment runbook (Render, Vercel, webhooks) | [`docs/deployment.md`](docs/deployment.md) |
| Payment provider setup | [`docs/moolre-setup.md`](docs/moolre-setup.md) |
| Security, tenancy, compliance, privacy | [`SECURITY.md`](SECURITY.md), [`docs/architecture/tenancy-decision.md`](docs/architecture/tenancy-decision.md), [`COMPLIANCE.md`](COMPLIANCE.md), [`docs/data-privacy.md`](docs/data-privacy.md) |
| Solo-farm tier | [`docs/solo-farm-product-spec.md`](docs/solo-farm-product-spec.md) |
| AgroCredit / Agro-AI | [`docs/scoring-systems.md`](docs/scoring-systems.md), [`docs/agro-ai-governance.md`](docs/agro-ai-governance.md) |

### 3. Repository Areas

* `frontend/` — cooperative and solo-farm dashboards plus public marketing pages.
* `backend/` — FastAPI routes, services, provider adapters, webhooks, USSD, scoring, Alembic migrations.
* `supabase/` — reference SQL mirroring the ORM; Alembic is authoritative.
* `docs/` — product, architecture, and operations documentation.

---

## AgroCredit AI Engine

AgroCredit includes `agro-ai`: a Scikit-learn Random Forest model that uses dues consistency, payment timeliness, production completion and output, cooperative attendance, loan history, outstanding balances, and savings behavior to generate an administrator-friendly credit-worthiness recommendation. The current model is trained on deterministic synthetic data and is advisory only until it is retrained on real repayment outcomes; see [`docs/agro-ai-governance.md`](docs/agro-ai-governance.md).

Production tracking and scoring support crop, animal, and mixed producers.

When a farmer makes a USSD payment, a webhook triggers the FastAPI backend to record the transaction and recalculate their Trust Score in Supabase.

---

See **[CONTRIBUTING.md](./CONTRIBUTING.md)** for branch naming, PR checklists, test commands, and secrets policy.

1. **Never push directly to `main`.**
2. Branch naming convention: `feat/feature-name`, `fix/bug-name`, `docs/update-name`.
3. Ensure backend code passes `ruff` linting and frontend code passes `eslint` before opening a Pull Request.
