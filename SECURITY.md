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

The backend uses JWT-based authentication with configurable token TTL.
JWTs include `cooperative_id` and `role`. `admin` can manage cooperative
profiles, members, production, finance, loans, and communications.
`finance_officer` is limited to finance, loan, and communication operations.
Authenticated reads and writes are constrained to the user's cooperative;
request body and query-string cooperative IDs cannot override that scope.

Password reset uses time-limited, single-use tokens sent to the user's
registered email.

Production deployments must set `AUTH_ENABLED=true`.

| Setting | Default | Behaviour |
|---|---|---|
| `AUTH_ENABLED=false` | Local tests/development only | Routes retain local-development compatibility |
| `AUTH_ENABLED=true` | Staging / production | Every non-public route requires `Authorization: Bearer <token>` |

Public routes are limited to signup/login, root and health probes, and the exact
Moolre/USSDK callback paths configured in `backend/main.py`.

## Token Configuration

| Setting | Default | Description |
|---|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | JWT access token TTL in minutes |
| `JWT_SECRET_KEY` | (required) | HMAC signing secret for JWTs |

## Demo Feature Gating

Features intended only for demonstration or which carry elevated risk are
gated behind feature flags and must not be active in production:

| Feature | Flag | Production Status |
|---|---|---|
| USSD sandbox mode | `USSD_SANDBOX=true` | Must be disabled in production |
| Unauthenticated routes | `AUTH_ENABLED=false` | Must be enabled in production |
| Mock payment webhooks | `MOOLRE_WEBHOOK_SECRET` unset | Must be set in production |

## Webhook Security

| Endpoint | Verification |
|---|---|
| `POST /webhooks/moolre/payment` | HMAC-SHA256 via `X-Moolre-Signature` when `MOOLRE_WEBHOOK_SECRET` is set |
| `POST /webhooks/moolre/ussd` | Shared-secret verification via `USSD_SHARED_SECRET` |

When `MOOLRE_WEBHOOK_SECRET` is unset, payment webhook signature checks are
skipped (development/sandbox only). Production deployments must set the secret.

USSD webhooks are authenticated using a pre-shared secret (`USSD_SHARED_SECRET`)
validated on every callback. This closes the USSD integrity gap identified in
earlier versions of this policy.

## Tenant Isolation

Cross-cooperative data isolation follows a defense-in-depth model:

1. **API-layer enforcement (primary):** The `enforce_cooperative_scope`
   middleware extracts `cooperative_id` from the authenticated JWT and
   enforces it on every request. Query-string and request-body cooperative
   IDs cannot override this scope.

2. **Row-level security (defense-in-depth):** Supabase RLS policies scope
   SELECT access on `farmers`, `transactions`, `loans`, `productions`, and
   `trust_scores` to the cooperative identified by
   `app.current_cooperative_id`. See `supabase/migrations/009_tenant_rls_policies.sql`.

RLS functions as a secondary enforcement layer — if the API-layer guard is
ever bypassed, the database still prevents cross-cooperative data access.

## Rate Limits

Abuse-sensitive POST routes use per-client, one-minute limits: login 10,
Moolre/USSDK callbacks 120, SMS sends 5, and dues collection 10. A rejected
request returns HTTP 429 with `Retry-After`. Limits can be adjusted with the
`RATE_LIMIT_*` environment variables; health probes are always exempt.

## Data Privacy

AgroOS collects and processes farmer PII including names, phone numbers,
financial transactions, credit scores, and SMS content. For the full data
handling policy, PII categories, access scope, SMS consent requirements,
and retention schedule, see [docs/data-privacy.md](docs/data-privacy.md).
