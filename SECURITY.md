# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in AgroOS, please do not open a
public GitHub issue. Contact the maintainers directly via the Moolre
Startup Cup hackathon communication channels.

We will acknowledge receipt within 48 hours and aim to resolve confirmed
issues before any public demo or production deployment.

## Scope

During the hackathon phase (Moolre Startup Cup, July 2026), the following
areas are in scope for security review:

- FastAPI backend endpoints (authentication, input validation)
- Supabase row-level security configuration
- Moolre webhook signature verification
- Environment variable and secret handling (.env.example hygiene)

## Known Limitations (Hackathon Phase)

- No authentication or RBAC is enforced in the current demo build
- The system must only be run with synthetic demo data until auth is implemented
- No rate limiting is currently applied to API endpoints

## Data Privacy

AgroOS collects and processes farmer PII including names, phone numbers,
financial transactions, credit scores, and SMS content. For the full data
handling policy, PII categories, access scope, SMS consent requirements,
and retention schedule, see [docs/data-privacy.md](docs/data-privacy.md).
