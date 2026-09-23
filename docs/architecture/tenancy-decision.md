# Decision: API-only tenancy (no client-facing database RLS)

**Status:** Adopted (closes [#240](https://github.com/Bempong-Sylvester-Obese/agro-os/issues/240))
**Applies to:** every deployment with `APP_ENV=production`

## Decision

AgroOS enforces multi-tenant isolation **exclusively at the FastAPI layer**.
The database is reachable only from the backend, using a single server-side
credential that no client ever holds. PostgreSQL row-level security (RLS) is
**not** relied on for tenant isolation and is not deployed by the backend's
migrations.

We considered the alternative — deploying per-tenant RLS on the tables the
apps touch — and rejected it for now because:

1. AgroOS issues its own JWTs (`app/services/auth_service.py`), not Supabase
   Auth JWTs, so Supabase's `authenticated` role and `auth.uid()`-based
   policies cannot identify our users. Policies would need a custom
   `SET LOCAL app.current_cooperative_id` per transaction plus a
   non-superuser runtime role, and the reference SQL in
   `supabase/migrations/002_rls_policies.sql`, `008_m5_rls_policies.sql`,
   and `009_tenant_rls_policies.sql` was written against roles the backend
   does not use.
2. The backend connects with an owner-level role that bypasses RLS entirely,
   so "deploying" those policies would document protection that does not
   exist for the only connection that matters.
3. There is exactly one data path (the API). Guarding it well is simpler to
   verify and test than keeping two enforcement layers in sync.

RLS remains a candidate defense-in-depth layer for a later milestone; the
prerequisites are listed under *Future work*.

## What "API-only tenancy" requires

| Requirement | Where it is enforced | How it is verified |
|---|---|---|
| Clients never hold database credentials | Frontend has no Supabase/Postgres SDK and no `VITE_SUPABASE_*`/`DATABASE_URL` variables; only `VITE_API_URL` | `frontend/src/security/noDirectDatabaseAccess.test.js` scans `frontend/src` on every test run |
| Production requires authentication | `Settings.reject_insecure_production_settings` refuses `APP_ENV=production` with `AUTH_ENABLED=false` | `backend/tests/test_config.py`, startup fails fast |
| Every tenant-scoped route derives the cooperative from the JWT, never from the request | `app/dependencies/cooperative_scope.py` (`require_cooperative_scope`, `resolve_cooperative_scope`) and `enforce_cooperative_scope` in `app/services/auth_service.py` | `backend/tests/test_auth_rbac.py` (cross-cooperative detail/list/mutation return 403/404) |
| Unauthenticated access to tenant data fails closed | `get_current_user` + `_PUBLIC_PATHS` allowlist in `backend/main.py` | `test_sensitive_get_fails_closed_without_token` |
| Public callback routes never return tenant data | Webhook/USSD routes are write-only ingestion points that respond with acknowledgements or menu text; they are authenticated by provider secrets, not user JWTs | `test_webhooks.py`, `test_ussd_gateway_parity.py`, `test_provider_neutral_routes.py` |
| Referential integrity cannot cross tenants | Cooperative-consistency constraints in Alembic (memberships, loans, transactions reference the same cooperative) | `backend/postgres_tests/` |
| Database credentials live only in the backend environment | `DATABASE_URL` in `backend/.env` / host secrets; the `supabase_*` settings are unused placeholders | Config review; never referenced by routes |

## Threat model

| # | Threat | Mitigation | Residual risk |
|---|---|---|---|
| T1 | Authenticated user of cooperative A requests cooperative B's data by changing a path/query/body `cooperative_id` | Scope is always replaced by the JWT's `cooperative_id`; explicit mismatches return 403, unknown IDs 404 | Low. Regression-tested per route family. A new route that forgets the dependency is the main risk; reviewers must check for `require_cooperative_scope` on any list/detail endpoint |
| T2 | Forged or tampered JWT | HS256 with `SECRET_KEY`; production refuses the default key; `sub` must resolve to a live user | Low; depends on secret hygiene (rotate on leak) |
| T3 | Stolen valid JWT | Bearer token; short TTL in production is tracked in #248; `401` clears client storage | Medium until #248 lands |
| T4 | Client bypasses API and talks to the database directly | No DB credentials or SDK ship to browsers (enforced by test); database is not exposed to the public internet by the hosting configuration | Low. Requires an operator to publish credentials |
| T5 | Compromise of the backend host / `DATABASE_URL` | Full read/write across tenants (no RLS backstop) | **Accepted.** This is the trade-off of API-only tenancy. Controls: secrets in host env only, no default secrets in production, audit logging of admin actions (`AdminAuditLog`) |
| T6 | Provider webhook forged to mutate another tenant's transaction | HMAC/shared-secret verification; references are looked up server-side and resolve to a single transaction; events are idempotent (`PaymentWebhookEvent`) | Low |
| T7 | USSD caller impersonates a farmer | Phone number comes from the gateway (authenticated by callback secret), not from the user; Link Phone requires cooperative code + farmer ID | Medium: MSISDN spoofing at the telco layer is out of scope |
| T8 | Operator runs demo seed/reset/purge against production data | `is_production` gates (404 for API, `--allow-production` for CLI, seed refused at startup) | Low |
| T9 | Privilege escalation within a tenant (finance officer acting as admin) | `require_roles` on admin-only routes; role comes from the JWT | Low; role model is being formalised in #244 |

## Operational rules

- `AUTH_ENABLED=true` is mandatory in production (enforced at startup).
- `DATABASE_URL`, `SECRET_KEY`, and provider secrets are configured only on the
  backend host. They must never appear in `frontend/.env*`, build output, or
  client bundles.
- The Supabase project, if used for hosting Postgres, must have the public
  PostgREST/anon API disabled or unused: no anon/service keys are distributed.
- Any new route returning tenant data must use `require_cooperative_scope`
  (or `enforce_cooperative_scope`) and gain a cross-tenant test in
  `backend/tests/test_auth_rbac.py`.

## Organizations (Enterprise parent tenant)

Issue #237 adds an optional parent above cooperatives for Enterprise
customers (unions, federations, aggregators). The tenancy unit does **not**
change; an organization is a grouping and billing entity only.

- Schema: `organizations` table; nullable `cooperatives.organization_id` and
  `users.organization_id` (both `ON DELETE SET NULL`). Migration
  `019_organizations`.
- **Scope stays cooperative-scoped.** Every tenant-data route still resolves
  scope from the JWT's `cooperative_id`; an organization admin holds exactly one
  active cooperative scope at a time. There is no "read across the whole
  organization" query path for member or financial data.
- **Switching scope is an explicit, audited action.** `POST
  /organizations/{id}/switch` validates the target cooperative belongs to the
  admin's organization, updates `users.cooperative_id`, writes an
  `organization.scope_switched` audit row, and re-issues the JWT. Previously
  issued tokens keep their old scope until they expire.
- **Organization routes are organization-scoped.** `/organizations/{id}/...`
  returns 404 when `{id}` is not the caller's `organization_id`, mirroring the
  cooperative rule; a caller with no organization also gets 404 (no
  enumeration). Only `admin` users can create or manage an organization.
- **Consolidated billing is an aggregate, not a data leak.** `GET
  /organizations/{id}/billing` returns per-cooperative plan/usage counters and
  the organization's payment intents; it never returns member rows.
- **Plan inheritance.** While the organization's contract is live
  (`subscription_status = active` and not expired) every member cooperative's
  effective plan is Enterprise; otherwise each falls back to its own plan.
  Contract activation is an operator action (`backend/scripts/activate_enterprise.py`),
  never an API call, so subscription fields on `organizations` are immutable
  through the API.

Threat additions: T10 — an organization admin switching into a cooperative
outside their organization (blocked by the membership check in `/switch`, tested
in `backend/tests/test_organizations.py`); T11 — a cooperative admin who is not
an organization member calling `/organizations/{id}/*` (404).

## Future work (prerequisites for enabling database RLS)

1. A restricted, non-owner runtime role for the backend connection.
2. `SET LOCAL app.current_cooperative_id = :id` at the start of every request
   transaction (SQLAlchemy `after_begin` hook) so policies can evaluate it.
3. Rewrite the reference policies to key on that setting instead of Supabase
   `auth.uid()`, and move them into Alembic so they are versioned with the
   schema.
4. A `postgres_tests` suite that proves cross-tenant SELECT/UPDATE fail at the
   database even when the API guard is bypassed.
