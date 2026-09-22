# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in AgroOS, please do not open a
public GitHub issue. Contact the maintainers directly via the project
repository or private communication channels.

We will acknowledge receipt within 48 hours and aim to resolve confirmed
issues before any production deployment.

## Scope

The following areas are in scope for security review:

- FastAPI backend endpoints (authentication, input validation)
- Tenant isolation (API-only tenancy; see [Tenant Isolation](#tenant-isolation))
- Payment webhook signature verification
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

Public routes are limited to signup/login, root and health probes, and the
configured webhook callback paths (see `WEBHOOK_CALLBACK_PATH` in config).

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
| Mock payment webhooks | Webhook secret unset | Must be set in production |
| Demo seed/reset | Hidden via frontend build flag | Must not be accessible in production |

## Webhook Security

| Endpoint | Verification |
|---|---|
| `POST /webhooks/payment` | HMAC-SHA256 via provider-specific header when webhook secret is set |
| `POST /webhooks/ussd` (alias `/webhooks/moolre/ussd`) | Query-string shared secret via `MOOLRE_USSD_SECRET` |
| `POST /ussd/callback` | Query-string shared secret via `USSD_CALLBACK_SECRET` |
| `POST /ussdk/*` | HMAC-SHA256 via `X-USSDK-Signature` and `USSDK_HOOK_SECRET` |

When the webhook secret is unset, payment webhook signature checks are
skipped (development/sandbox only). Production deployments must set the secret.

USSD callbacks fail closed in production when their endpoint-specific secret is
unset. Development and test environments may omit these secrets.

## Tenant Isolation

**Decision: API-only tenancy.** Cross-cooperative isolation is enforced solely
by the FastAPI layer; database row-level security (RLS) is *not* deployed and
is not relied on. The full decision record, requirements table, and threat
model live in
[docs/architecture/tenancy-decision.md](docs/architecture/tenancy-decision.md).

What that means in practice:

1. **Scope comes from the JWT.** Protected route handlers call
   `enforce_cooperative_scope` or `require_cooperative_scope`, which replace
   any cooperative ID in the path, query string, or body with the
   authenticated user's cooperative. Mismatches return 403; unknown IDs 404.
   Covered by `backend/tests/test_auth_rbac.py`.

2. **Production requires authentication.** `APP_ENV=production` with
   `AUTH_ENABLED=false` fails startup validation.

3. **Clients never hold database access.** The frontend ships no Supabase or
   Postgres SDK, no connection string, and no `VITE_SUPABASE_*` /
   `VITE_DATABASE_*` variables; `frontend/src/security/noDirectDatabaseAccess.test.js`
   fails the build's test run if any appear. `DATABASE_URL`, `SECRET_KEY`, and
   provider secrets are configured only on the backend host.

4. **Referential integrity cannot cross tenants.** Alembic
   cooperative-consistency constraints keep memberships, loans, and
   transactions within one cooperative.

The SQL under `supabase/migrations/*_rls_policies.sql` is reference material
only: it is not applied by Alembic, it targets Supabase Auth roles AgroOS does
not use, and the backend's owner-level connection would bypass it regardless.
Compromise of the backend host or `DATABASE_URL` therefore yields cross-tenant
access; this is the accepted residual risk of the decision (threat T5 in the
decision record). The prerequisites for adding database RLS as a later
defense-in-depth layer are listed there under *Future work*.

## Rate Limits

Abuse-sensitive POST routes use per-client, one-minute limits: login 10,
webhook callbacks 120, SMS sends 5, and dues collection 10. A rejected
request returns HTTP 429 with `Retry-After`. Limits can be adjusted with the
`RATE_LIMIT_*` environment variables; health probes are always exempt.

## Data Privacy

AgroOS collects and processes farmer PII including names, phone numbers,
financial transactions, credit scores, and SMS content. For the full data
handling policy, PII categories, access scope, SMS consent requirements,
and retention schedule, see [docs/data-privacy.md](docs/data-privacy.md).
