# Team Assignments

Use this document to keep ownership clear during the hackathon. Update names once the team confirms who is handling each area.

## Workstreams

### Frontend Dashboard
Owner: Julien Oboe Addy

Responsibilities:
- Build the cooperative admin dashboard in `frontend/`.
- Create views for overview, members, finance, production, loans, SMS, and USSD activity.
- Work with the backend owner on API response shapes.
- Keep the Golden Path demo visible in the UI.

### Backend API and Moolre Integration
Owner: Elvis Antwi Boateng Osei 

Responsibilities:
- Build the FastAPI application in `backend/`.
- Create endpoints for farmers, transactions, loans, production records, announcements, and Trust Scores.
- Implement Moolre payment, webhook, transfer/disbursement, SMS, and status-check integrations.
- Own server-side environment variable usage and API security.

### Database and Demo Data
Owner: Sylvester Obese Bempong 

Responsibilities:
- Own Supabase schema, migrations, and seed data in `supabase/`.
- Define tables for cooperatives, farmers, payments, loans, harvests, announcements, USSD sessions, SMS messages, webhook events, and Trust Scores.
- Provide realistic seeded data for the final demo.
- Keep database changes aligned with frontend and backend contracts.

### Demo Flow and Pitch
Owner: Ramzy Gbati Konde 

Responsibilities:
- Own the Golden Path demo script in `docs/demo-script.md`.
- Coordinate the story, sample farmer, sample cooperative, and presentation flow.
- Prepare fallback demo data if live Moolre sandbox access is delayed.
- Keep the pitch focused on cooperative impact, financial inclusion, and Moolre-powered infrastructure.

## Branching

- Use `frontend` for frontend implementation.
- Use `backend-work` for backend implementation.
- Use `feat/agro-ai-credit-model` for database and AI scoring model work.
- Use `docs/demo-flow` for pitch and documentation work.

> Branch names above reflect what's currently in the repo. Run `git branch -a` and correct any that have drifted before merging this doc.

## Coordination Checklist

Who actually holds access to each of these — not who should, who does right now:

| Resource | Owner | Notes |
|---|---|---|
| Moolre API credentials (sandbox) | `TBD` | |
| Moolre API credentials (production, if applicable) | `TBD` | |
| Supabase project (admin access) | `TBD` | |
| Vercel deployment (project owner) | `TBD` | |
| Backend host (if separate from Vercel) | `TBD` | |

If you need access you don't have, request it from the owner listed above rather than working around it. Rotate shared credentials after the hackathon ends.

## Milestones

- [MVP](https://github.com/Bempong-Sylvester-Obese/agro-os/milestone/1) — required for first working AgroOS MVP
- [Demo](https://github.com/Bempong-Sylvester-Obese/agro-os/milestone/2) — Golden Path demo, pitch flow, fallback data
- [Documentation](https://github.com/Bempong-Sylvester-Obese/agro-os/milestone/3) — README, runbooks, policy docs

> Milestone numbers are inferred from issue references, not verified directly — confirm against github.com/Bempong-Sylvester-Obese/agro-os/milestones before relying on these links.

## Coordination Rules

- Do not push directly to `main`.
- Keep PRs focused on one workstream.
- Document any API or schema changes before teammates depend on them.
- Prefer demo-ready, working slices over broad unfinished features.
