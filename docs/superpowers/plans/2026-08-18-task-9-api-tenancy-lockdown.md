# Task 9: API-Only Tenancy Lockdown — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-closed `require_cooperative_scope()` FastAPI dependency and apply it to key data-access routes, ensuring every authenticated request is scoped to its cooperative at the API layer.

**Architecture:** Create a new dependency in `backend/app/dependencies/cooperative_scope.py` that raises 403 if no cooperative_id can be resolved from the JWT or query params. Apply it to list/detail routes on transactions, loans, cooperatives, farmers, production, sales, and payroll. Update SECURITY.md and COMPLIANCE.md to document the API-only tenancy model.

**Tech Stack:** Python/FastAPI, existing dependency injection pattern

## Global Constraints

- All changes on branch `feat/m1-m2-close-milestones` (branched from `dev`)
- Run `npm run test:backend` after each task to verify nothing breaks
- No new external dependencies unless absolutely necessary
- Follow existing code style (no comments unless asked)
- Commit after each task with descriptive message

---

### Task 9.1: Create `require_cooperative_scope()` dependency

**Files:**
- Modify: `backend/app/dependencies/cooperative_scope.py`
- Modify: `backend/app/dependencies/__init__.py`

**Interfaces:**
- Consumes: `User` (from auth), `cooperative_id` query param, `Settings`
- Produces: `require_cooperative_scope` FastAPI dependency (returns `int`)

- [ ] **Step 1: Add `require_cooperative_scope()` to `cooperative_scope.py`**

Add a new FastAPI dependency function after `resolve_cooperative_scope`. This is a stricter variant that **always** raises 403 when no cooperative scope is found, regardless of `auth_enabled`. It uses `Depends` to receive FastAPI-injected arguments.

```python
from fastapi import Depends, HTTPException, Query

from app.services.auth_service import get_current_user


def require_cooperative_scope(
    current_user: User | None = Depends(get_current_user),
    cooperative_id: int | None = Query(default=None),
) -> int:
    """Fail-closed: return cooperative_id or raise 403.

    Every authenticated request that touches cooperative-scoped data
    must use this dependency.  It replaces the loose
    ``resolve_cooperative_scope`` for mutations and key list endpoints.
    """
    if current_user is not None and current_user.cooperative_id:
        return current_user.cooperative_id
    if cooperative_id is not None:
        return cooperative_id
    raise HTTPException(status_code=403, detail="Cooperative scope required")
```

- [ ] **Step 2: Export from `__init__.py`**

In `backend/app/dependencies/__init__.py`, add:

```python
from app.dependencies.cooperative_scope import require_cooperative_scope

__all__ = ["require_cooperative_scope"]
```

- [ ] **Step 3: Verify app boots**

Run: `cd backend; python -c "from main import app; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add backend/app/dependencies/cooperative_scope.py backend/app/dependencies/__init__.py
git commit -m "feat: add fail-closed require_cooperative_scope dependency (#240)"
```

---

### Task 9.2: Apply `require_cooperative_scope` to transaction routes

**Files:**
- Modify: `backend/app/routes/transactions.py`

**Interfaces:**
- Consumes: `require_cooperative_scope` from Task 9.1

- [ ] **Step 1: Import the new dependency**

In `backend/app/routes/transactions.py`, add to imports:

```python
from app.dependencies.cooperative_scope import require_cooperative_scope
```

- [ ] **Step 2: Apply to `list_transactions`**

Replace the manual `resolve_cooperative_scope` call with the dependency in the function signature:

```python
@router.get("/", response_model=list[TransactionResponse])
async def list_transactions(
    farmer_id: int | None = None,
    status: TransactionStatus | None = None,
    transaction_type: TransactionType | None = None,
    scoped_coop_id: int = Depends(require_cooperative_scope),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
```

Remove the manual `resolve_cooperative_scope(...)` call inside the function body and use `scoped_coop_id` directly.

- [ ] **Step 3: Apply to `list_webhook_events`**

Replace the manual auth check + `current_user.cooperative_id` with `Depends(require_cooperative_scope)`.

- [ ] **Step 4: Verify app boots**

Run: `cd backend; python -c "from main import app; print('OK')"`

- [ ] **Step 5: Run backend tests**

Run: `npm run test:backend`

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/transactions.py
git commit -m "feat: apply require_cooperative_scope to transaction routes (#240)"
```

---

### Task 9.3: Apply `require_cooperative_scope` to loan routes

**Files:**
- Modify: `backend/app/routes/loans.py`

**Interfaces:**
- Consumes: `require_cooperative_scope` from Task 9.1

- [ ] **Step 1: Import the new dependency**

```python
from app.dependencies.cooperative_scope import require_cooperative_scope
```

- [ ] **Step 2: Apply to `list_loans`**

Replace the manual `resolve_cooperative_scope` call with `Depends(require_cooperative_scope)` in the function signature.

- [ ] **Step 3: Apply to `get_loan`, `get_loan_reminders`**

These use `_get_loan_or_404` which already calls `enforce_cooperative_scope`. The dependency is an additional layer. Apply to the route signatures.

- [ ] **Step 4: Verify app boots and run tests**

Run: `cd backend; python -c "from main import app; print('OK')"` then `npm run test:backend`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/loans.py
git commit -m "feat: apply require_cooperative_scope to loan routes (#240)"
```

---

### Task 9.4: Apply `require_cooperative_scope` to cooperatives, farmers, production, sales, and payroll routes

**Files:**
- Modify: `backend/app/routes/cooperatives.py`
- Modify: `backend/app/routes/farmers.py`
- Modify: `backend/app/routes/production.py`
- Modify: `backend/app/routes/sales.py`
- Modify: `backend/app/routes/payroll.py`

**Interfaces:**
- Consumes: `require_cooperative_scope` from Task 9.1

- [ ] **Step 1: cooperatives.py — apply to `list_cooperatives`**

Add `from app.dependencies.cooperative_scope import require_cooperative_scope` and apply `Depends(require_cooperative_scope)` to `list_cooperatives`.

- [ ] **Step 2: farmers.py — apply to `list_farmers`**

Replace the manual cooperative scoping block with `Depends(require_cooperative_scope)`.

- [ ] **Step 3: production.py — apply to `list_productions`**

Replace the manual cooperative scoping block with `Depends(require_cooperative_scope)`.

- [ ] **Step 4: sales.py — apply to `list_sales`**

Replace the manual `_scope(...)` calls with `Depends(require_cooperative_scope)`.

- [ ] **Step 5: payroll.py — apply to `payroll_summary`, `approve_payroll`, `disburse_payroll`, `payroll_history`**

Replace the manual `enforce_cooperative_scope` calls in the function bodies with `Depends(require_cooperative_scope)` in the signatures.

- [ ] **Step 6: Verify app boots and run tests**

Run: `cd backend; python -c "from main import app; print('OK')"` then `npm run test:backend`

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/cooperatives.py backend/app/routes/farmers.py backend/app/routes/production.py backend/app/routes/sales.py backend/app/routes/payroll.py
git commit - "feat: apply require_cooperative_scope to cooperatives/farmers/production/sales/payroll (#240)"
```

---

### Task 9.5: Update SECURITY.md tenancy section

**Files:**
- Modify: `SECURITY.md`

**Interfaces:**
- None

- [ ] **Step 1: Update the Tenant Isolation section**

Replace the existing Tenant Isolation section (lines 77-104) with a revised version that documents the API-only tenancy model as the primary (and currently enforced) mechanism. Specifically:

- Document that `require_cooperative_scope()` is the primary defense
- JWT contains `cooperative_id`, validated on every request via FastAPI DI
- Route handlers must filter queries by cooperative scope
- DB connection uses service-role (bypasses RLS) — defense-in-depth only
- Threat model: "If a route handler omits cooperative filtering, cross-tenant data could leak"
- RLS reference SQL retained in `supabase/migrations/009_tenant_rls_policies.sql` for future enforcement

- [ ] **Step 2: Commit**

```bash
git add SECURITY.md
git commit -m "docs: update SECURITY.md tenancy section for API-only model (#240)"
```

---

### Task 9.6: Update COMPLIANCE.md tenancy section

**Files:**
- Modify: `COMPLIANCE.md`

**Interfaces:**
- None

- [ ] **Step 1: Update cross-cooperative isolation reference**

In COMPLIANCE.md §5 (Cooperative Governance Alignment), update line 109-111 to reference `require_cooperative_scope` as the enforced mechanism. Remove any hackathon-scope caveats about RLS.

- [ ] **Step 2: Commit**

```bash
git add COMPLIANCE.md
git commit -m "docs: update COMPLIANCE.md for API-only tenancy model (#240)"
```

---

### Task 9.7: Final verification and commit

**Files:**
- All modified files

- [ ] **Step 1: Verify app boots**

Run: `cd backend; python -c "from main import app; print('OK')"`

- [ ] **Step 2: Run full backend test suite**

Run: `npm run test:backend`
Expected: All tests pass

- [ ] **Step 3: If tests fail, fix them and re-run**

- [ ] **Step 4: Final commit with all changes**

```bash
git add -A
git commit -m "feat: add API-only cooperative scope enforcement (#240)"
```

- [ ] **Step 5: Write report**

Write report to: `C:\Users\Dell G3 15 GAMING\Desktop\agro-os\.superpowers\sdd\2026-08-18-m1-m2-production-hardening-decoupling\task-9-report.md`
