# M4 — Cooperative Product Completeness Design

**Date:** 2026-08-04
**Milestone:** [M4 — Cooperative Product Completeness](https://github.com/Bempong-Sylvester-Obese/agro-os/milestone/8)
**Status:** Design

---

## 1. #244 — Complete RBAC: Enum Roles, Frontend Nav Gating

### Current State
- 5 roles defined in schemas: `admin`, `finance_officer`, `farm_owner`, `farm_manager`, `supervisor`
- Only 2 surfaced in GovernanceSettings.jsx UI: `admin`, `finance_officer`
- `require_roles()` guards exist on backend routes
- No role-based nav gating on cooperative dashboard sidebar

### Changes

**Backend:** No changes needed. All 5 roles defined, guards in place.

**Frontend:**
- `GovernanceSettings.jsx`: Expand role dropdown from 2 to all 5 roles
- `DashboardPage.jsx`: Add role-based nav gating for cooperative org type:

| Role | Operations | Finance | Commerce | Communications | Governance |
|------|:--:|:--:|:--:|:--:|:--:|
| admin | Full | Full | Full | Full | Full |
| finance_officer | Full | Full | Hidden | View | View |
| farm_owner | Full | Hidden | Hidden | View | View |
| farm_manager | Full | Hidden | Hidden | View | View |
| supervisor | Full | Hidden | Hidden | View | View |

- Operate on same `filteredNavGroups` pattern already established for solo_farm roles in DashboardPage.jsx

---

## 2. #245 — Attendance Recording UI for Trust Score

### Current State
- `POST /farmers/{farmer_id}/attendance` and `GET /farmers/{farmer_id}/attendance` exist
- Attendance contributes 15% to Trust Score
- No dashboard UI for recording cooperative meeting attendance

### Changes

**Frontend:** New `CooperativeAttendance` component added to cooperative dashboard:
- Tab: "Attendance" (for cooperative org type, under Operations)
- Date picker + event name input
- Member list with attendance checkboxes (mark attended/absent per member per event)
- Bulk toggle: mark all present / mark all absent
- Submits `POST /farmers/{id}/attendance` per checked member
- Shows past attendance records filtered by event

---

## 3. #246 — Announcements CRUD + SMS Broadcast + USSD

### Current State
- No Announcement model, no CRUD API, no dashboard UI
- USSD option 4 returns static: "No new announcements. Check with your cooperative leader."
- SMS broadcast exists but no announcement integration

### Changes

**Model:** New `Announcement` model:
- `id`, `cooperative_id` (FK), `title` (varchar), `body` (text), `send_sms` (bool), `created_by` (FK→users), `created_at`
- Alembic migration

**Backend:** New `announcements.py` route:
- `GET /announcements` — list for cooperative (paginated)
- `POST /announcements` — create (admin/finance_officer only). If `send_sms=true`, broadcast to all active members via `CommunicationsService.send_bulk_sms()`  
- `DELETE /announcements/{id}` — soft delete (admin only)

**Frontend:** New "Announcements" tab:
- Create form: title, body, SMS toggle
- List of past announcements with timestamps
- Visible to Operations group for cooperative org

**USSD:** Update option 4 to return latest 3 announcements with title + body. Replace static placeholder.

**Supabase:** Add `announcements` table to migrations.

---

## 4. #247 — SMS Consent / Opt-Out

### Current State
- Zero implementation. Compliance docs exist but no code.
- No consent check before SMS dispatch.

### Changes

**Model:** Add `sms_consent` to `CooperativeMembership`:
- `sms_consent` (Boolean, default `True`, not null)
- Alembic migration

**Backend:**
- `CommunicationsService`: check `membership.sms_consent` before sending SMS. Skip non-consenting members. Log as "skipped_consent".
- Member update endpoint: allow toggling `sms_consent`

**Frontend:**
- Member edit/profile: SMS consent toggle (checkbox)
- Non-consenting members excluded from broadcast recipient count

**Supabase:** Add `sms_consent` column to `cooperative_memberships`.

---

## 5. #248 — Auth Lifecycle Hardening

### Current State
- No password reset, no invite flow, tokens last 7 days, no force-password-change
- Admin creates users manually via existing register form

### Changes

**Model changes:**
- Add `reset_token`, `reset_token_expires_at` (DateTime, nullable) to `User`
- Add `must_change_password` (Boolean, default `True` for admin-created users) to `User`
- Add `invite_token`, `invite_token_expires_at` (DateTime, nullable) to `User`

**Backend endpoints:**

1. **Password reset request:** `POST /auth/password-reset-request`
   - Accepts email, always returns 200 (don't reveal account existence)
   - If account exists: generate `reset_token` (64-char random hex), set expiry (15 min), store on user
   - If email/sending is unavailable: log the reset token to backend logs (interim manual process). Document this as temporary.

2. **Password reset confirm:** `POST /auth/password-reset-confirm`
   - Accepts `reset_token` + `new_password`
   - Validates token exists, not expired, not used
   - Sets new password, clears `reset_token`/`reset_token_expires_at`, clears `must_change_password`

3. **Invite user:** `POST /auth/invite`
   - Admin creates user with email + role, generates `invite_token` (single-use, 72h expiry)
   - Returns invite link/code for admin to share manually (interim — no email infra)
   - New endpoint for invite acceptance: `POST /auth/accept-invite` (token + password)

4. **Token TTL:** Add `ACCESS_TOKEN_EXPIRE_MINUTES` env var, default 15 in production, 10080 (7d) in dev

5. **Force password change:** On login, if `must_change_password=true`, return `password_change_required: true` in response. Frontend intercepts and redirects to set-password screen.

**Frontend:**
- Login page: "Forgot password?" link → request form → confirmation → new password form
- First-login flow: if `password_change_required`, redirect to mandatory password-change screen
- GovernanceSettings: updated invite UI (generates invite link, no email)

---

## 6. #249 — Extend Commerce Settlement to Animal/Mixed Production

### Current State
- `ProductionKind` enum exists (`crop`, `animal`)
- `ProductionFocus` on memberships exists (`crop`, `animal`, `mixed`)
- But `intake.py` explicitly blocks animal-only members (line 56-59)
- Settlement pipeline works on intake records — crop-only currently

### Changes

**Backend:**
- `intake.py`: Remove the block that rejects `production_focus=animal` members. Mixed already allowed.
- `ProduceIntakeCreate` schema: allow `product_name` (unified field) instead of mandating `crop_type`
- Settlement flow: already processes intake records generically — no settlement changes needed once intake accepts animal products

**Frontend:**
- Intake form: add product type selector (crop / animal) + product name input for animal products

**Priority:** p2

---

## 7. #250 — Gate Synthetic Agro-AI with Warnings

### Current State
- Model trained on 100% synthetic data (beta distributions + heuristic labels)
- Real features pulled from operational DB for live farmers
- `is_synthetic_fallback` flag exists on model but not exposed via API

### Changes

**Backend:**
- Expose `is_synthetic` in prediction API response
- Add deprecation-style response header or field

**Frontend:**
- `Scores.jsx`: Replace existing info banner with prominent warning:
  > *"Trust scores are experimental — trained on synthetic data, not real repayment history. Use as an advisory tool only."*
- Show yellow/orange warning banner when model is synthetic

---

## 8. #251 — JWT Hydrate / Demo Cleanup

### Current State
- `frontend/src/data/payments.js`: 6 demo farmers, 5 static payments, static scores — dead code (zero imports)
- `frontend/src/components/DashboardMock.jsx`: static marketing mock, only used by HomePage.jsx
- `withDemoFallback`: exported but never called

### Changes

- Delete `frontend/src/data/payments.js`
- Move DashboardMock static data inline into HomePage.jsx (or remove if unused) and delete the component file
- Verify build passes after removal
