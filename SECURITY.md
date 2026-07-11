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

## Authentication Model

The backend ships with JWT-based admin login (`POST /auth/login`) and an
optional auth middleware controlled by `AUTH_ENABLED` (default: `false`).

| Setting | Default | Behaviour |
|---|---|---|
| `AUTH_ENABLED=false` | Demo / local dev | GET routes are open; mutating routes are not blocked by JWT |
| `AUTH_ENABLED=true` | Staging / production | Mutating API routes require `Authorization: Bearer <token>` |

Routes always excluded from JWT middleware: `/auth/login` and `/webhooks/*`.

**RBAC and cooperative scoping are not yet enforced.** Any authenticated
admin can access all cooperatives until role-based access is implemented.

## Webhook Security

| Endpoint | Verification |
|---|---|
| `POST /webhooks/moolre/payment` | HMAC-SHA256 via `X-Moolre-Signature` when `MOOLRE_WEBHOOK_SECRET` is set |
| `POST /webhooks/moolre/ussd` | No signature verification today (see open issues) |
| `POST /webhooks/moolre/payment/simulate` | Disabled when `APP_ENV=production` |

When `MOOLRE_WEBHOOK_SECRET` is unset, payment webhook signature checks are
skipped (development/sandbox only). Production deployments must set the secret.

## Known Limitations (Hackathon Phase)

- Cooperative-scoped RBAC is not enforced on API routes
- USSD webhook callbacks are not authenticated
- No rate limiting is currently applied to API endpoints
- Supabase row-level security policies are not yet deployed

For production hardening work in progress, see the open GitHub issues labeled
`priority: p0` and `priority: p1`.

## Data Privacy

AgroOS collects and processes farmer PII including names, phone numbers,
financial transactions, credit scores, and SMS content. For the full data
handling policy, PII categories, access scope, SMS consent requirements,
and retention schedule, see [docs/data-privacy.md](docs/data-privacy.md).
