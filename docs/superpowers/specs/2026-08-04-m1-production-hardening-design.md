# M1 — Production Hardening Design

**Date:** 2026-08-04
**Milestone:** [M1 — Production Hardening](https://github.com/Bempong-Sylvester-Obese/agro-os/milestone/5)

---

## Design Decisions

### #220 — Auth Moolre USSD Webhook (`/webhooks/moolre/ussd`)
**Decision:** Add `MOOLRE_USSD_SECRET` env var. Require `?secret=<MOOLRE_USSD_SECRET>` query param on the webhook URL. Reject with 401 if missing/mismatched. This is the standard approach for callbacks that don't support HMAC headers. Moolre's callback URL can be configured with query params.

### #221 — Fail Closed When MOOLRE_WEBHOOK_SECRET is Unset
**Decision:** In production (APP_ENV=production), reject payment webhooks with 503 if MOOLRE_WEBHOOK_SECRET is not configured. Keep dev/sandbox bypass. Add startup health check warning.

### #222 — Auth USSD /ussd/callback
**Decision:** Add `USSD_CALLBACK_SECRET` env var. Require `?secret=<USSD_CALLBACK_SECRET>` on the Africa's Talking callback URL. AT supports query params in callback config. Reject with 401 if missing/mismatched.

### #223 — Gate Demo Features in Production
**Decision:** Disable `/admin/demo-reset/*` entirely in production (return 404). Keep `SEED_DEMO_DATA` rejection in config validator (already done). Verify no other demo endpoints leak.

### #238 — Persist USSD Sessions
**Decision:** Replace in-memory `_ussd_sessions: dict` with DB-backed sessions using existing `ussd_sessions` table. Add `session_state` JSON column to `UssdSession` model. TTL: auto-expire sessions > 1 hour. This survives dyno restarts and handles horizontal scaling.

### #239 — Alembic as Single Schema Source
**Decision:** Add `-- REFERENCE ONLY` header to each `supabase/migrations/*.sql` file. Update `supabase/README.md` to clarify Alembic is the authoritative source.

### #240 — Real Tenant RLS
**Decision:** Add cooperative-scoped RLS policies on core tables (farmers, transactions, loans, productions, trust_scores) as defense-in-depth. Primary isolation remains API-layer via `enforce_cooperative_scope`.

### #241 — Docs Rewrite (p2)
**Decision:** Update SECURITY.md and COMPLIANCE.md to reflect current production posture: JWT auth, webhook signature verification, tenant isolation, demo gating.
