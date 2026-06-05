# Team Assignments

Use this document to keep ownership clear during the hackathon. Update names once the team confirms who is handling each area.

## Workstreams

### Frontend Dashboard

Owner: TBD

Responsibilities:

- Build the cooperative admin dashboard in `frontend/`.
- Create views for overview, members, finance, production, loans, SMS, and USSD activity.
- Work with the backend owner on API response shapes.
- Keep the Golden Path demo visible in the UI.

### Backend API and Moolre Integration

Owner: TBD

Responsibilities:

- Build the FastAPI application in `backend/`.
- Create endpoints for farmers, transactions, loans, production records, announcements, and Trust Scores.
- Implement Moolre payment, webhook, transfer/disbursement, SMS, and status-check integrations.
- Own server-side environment variable usage and API security.

### Database and Demo Data

Owner: TBD

Responsibilities:

- Own Supabase schema, migrations, and seed data in `supabase/`.
- Define tables for cooperatives, farmers, payments, loans, harvests, announcements, USSD sessions, SMS messages, webhook events, and Trust Scores.
- Provide realistic seeded data for the final demo.
- Keep database changes aligned with frontend and backend contracts.

### Demo Flow and Pitch

Owner: TBD

Responsibilities:

- Own the Golden Path demo script in `docs/demo-script.md`.
- Coordinate the story, sample farmer, sample cooperative, and presentation flow.
- Prepare fallback demo data if live Moolre sandbox access is delayed.
- Keep the pitch focused on cooperative impact, financial inclusion, and Moolre-powered infrastructure.

## Branching

- Use `feat/frontend-dashboard` for frontend implementation.
- Use `feat/backend-api` for backend implementation.
- Use `feat/supabase-schema` for database work.
- Use `docs/demo-flow` for pitch and documentation work.

## Coordination Rules

- Do not push directly to `main`.
- Keep PRs focused on one workstream.
- Document any API or schema changes before teammates depend on them.
- Prefer demo-ready, working slices over broad unfinished features.
