# AgroOS

**The Digital Infrastructure and Operating System for African Farmer Cooperatives.**

AgroOS is a B2B cooperative management platform for Ghanaian agricultural cooperatives. It empowers farmer organizations to manage members, process bulk disbursements, and generate AI-driven credit scores using offline-first USSD integration.

By bridging the gap between unconnected rural farmers and formal financial ecosystems, AgroOS provides enterprise-grade infrastructure tailored for the agricultural value chain.

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

AgroOS follows a **ports-and-adapters** architecture. Payment and SMS providers are abstract behind port interfaces, with concrete adapters that translate provider-specific APIs into domain-normalized operations. See [`docs/architecture.md`](docs/architecture.md) for the full architecture document.

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
├── docs/                      # Product strategy, architecture, and planning
│   └── architecture.md        # System architecture document
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

- `docs/` for strategy, architecture, and planning documents
- `docs/architecture.md` for system architecture and provider integration
- `backend/README.md` for backend endpoints, environment variables, linting, and test commands

### 3. Team Work Areas

* `frontend/` owns the cooperative admin dashboard.
* `backend/` owns FastAPI routes, webhook handling, and Trust Score logic.
* `supabase/` owns schema, migrations, and demo seed data.
* `docs/` owns product strategy and shared planning notes.

---

## AgroCredit AI Engine

AgroCredit includes `agro-ai`: a Scikit-learn Random Forest model trained on deterministic synthetic cooperative data. It uses dues consistency, payment timeliness, production completion and output, cooperative attendance, loan history, outstanding balances, and savings behavior to generate an administrator-friendly credit-worthiness recommendation.

Production tracking and scoring support crop, animal, and mixed producers.

When a farmer makes a USSD payment, a webhook triggers the FastAPI backend to record the transaction and recalculate their Trust Score in Supabase.

---

See **[CONTRIBUTING.md](./CONTRIBUTING.md)** for branch naming, PR checklists, test commands, and secrets policy.

1. **Never push directly to `main`.**
2. Branch naming convention: `feat/feature-name`, `fix/bug-name`, `docs/update-name`.
3. Ensure backend code passes `ruff` linting and frontend code passes `eslint` before opening a Pull Request.
