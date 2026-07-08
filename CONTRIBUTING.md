# Contributing to AgroOS



AgroOS is a hackathon monorepo with a tight timeline. These rules exist to keep merge conflicts near zero and `main` always green. Read this once before opening your first branch.

---

## 1. Branch Naming

Every branch **must** follow this pattern:

```
<type>/<short-description>
```

| Prefix | When to use |
|---|---|
| `feat/` | New feature or capability |
| `fix/` | Bug fix or broken behaviour |
| `docs/` | Documentation only (no logic changes) |
| `integrate/` | Wiring two sub-systems together (e.g. Moolre webhook ↔ Trust Score) |

**Examples**

```
feat/trust-score-engine
fix/supabase-null-member-id
docs/api-contract-update
integrate/moolre-webhook-fastapi
```

Anything that doesn't fit gets a `feat/` prefix. When in doubt, ask in the group chat before branching.

---

## 2. Never Push to `main`

`main` is protected. Direct pushes will be rejected.

```
# correct
git checkout -b feat/your-feature
git push origin feat/your-feature

# wrong — never do this
git push origin main
```

All changes reach `main` through a Pull Request that has been reviewed by at least one other teammate.

---

## 3. Before Opening a PR — Run These Checks

All three checks must pass locally before you push and request review.

### Backend (Python / FastAPI)

```bash
# From repo root or backend/
ruff check backend/

# Run backend tests
npm run test:backend
# or directly: cd backend && pytest
```

`ruff` replaces flake8 + isort + pyupgrade. Fix every reported issue — do not add `# noqa` without a comment explaining why.

### Frontend (Next.js)

```bash
# From frontend/
cd frontend
npm run build
```

A successful `next build` is the minimum bar. ESLint is wired into the build; it will fail on lint errors too. Fix them before pushing.

### Quick sanity checklist

```
[ ] ruff check passes with 0 errors
[ ] npm run build exits 0
[ ] No .env file staged (git status confirms)
[ ] No secrets or API keys in any file
```

---

## 4. Managing Python Dependencies (`backend/requirements.in` → `pip-compile`)

Never edit `backend/requirements.txt` by hand. It is auto-generated.

**To add or change a dependency:**

1. Edit `backend/requirements.in` — add the package with a loose version pin:
   ```
   fastapi>=0.111
   scikit-learn>=1.4
   ```
2. Regenerate the locked file:
   ```bash
   pip install pip-tools          # one-time setup
   cd backend
   pip-compile requirements.in    # writes requirements.txt
   ```
3. Commit **both** files together:
   ```bash
   git add backend/requirements.in backend/requirements.txt
   git commit -m "deps: add scikit-learn for Trust Score engine"
   ```

This keeps the lock file deterministic across all teammates' machines.

---

## 5. Linking PRs to Issues and Milestones

### Closing keywords

Put one of these in your PR description to auto-close the issue on merge:

```
Closes #<issue-number>
Fixes #<issue-number>
Resolves #<issue-number>
```

Example PR description opening:

```
Closes #17

Implements the AgroCredit rules-based Trust Score engine.
Webhook from Moolre triggers recalculation on each payment event.
```

### Milestones

Assign your PR to the correct milestone when you open it:

| Milestone | What belongs here |
|---|---|
| **MVP** | Anything needed for the first working demo path |
| **Demo** | Polish, seed data, and presentation-ready flows |
| **Documentation** | `docs/`, `readme.md`, `CONTRIBUTING.md`, API contracts |

If you are unsure, look at the issue's milestone and match it.

---

## 6. Environment Secrets — Never Commit `.env`

`.env` is in `.gitignore`. Keep it that way.

**Rules:**

- Never commit `.env`, `.env.local`, `.env.production`, or any file containing real API keys.
- Use `.env.example` to document which variables are required (no real values, just the key names and a short comment).
- If you need a new secret, add the key name to `.env.example` and share the actual value with teammates via the group chat or a shared secrets manager — never via a commit or PR comment.

**If you accidentally commit a secret:**

1. Immediately rotate the key in the relevant dashboard (Moolre, Supabase, etc.).
2. Remove it from history: `git filter-repo` or contact the repo owner.
3. Force-push and notify the team.

A committed secret that has been rotated is a recoverable mistake. A committed secret that hasn't been rotated is a live vulnerability.

---

## 7. PR Checklist

Copy this into every PR description before submitting:

```markdown
## PR Checklist

- [ ] Branch follows naming convention (`feat/`, `fix/`, `docs/`, `integrate/`)
- [ ] `ruff check backend/` passes with 0 errors
- [ ] `npm run build` (frontend) exits 0
- [ ] No `.env` or secrets staged
- [ ] If Python deps changed: both `requirements.in` and `requirements.txt` committed
- [ ] PR is linked to an issue with a closing keyword (`Closes #N`)
- [ ] PR is assigned to the correct milestone (MVP / Demo / Documentation)
- [ ] At least one teammate requested for review
```

---

## 8. Quick Reference

```
Branch off main    →  git checkout -b <type>/<description>
Lint Python        →  ruff check backend/
Test backend       →  npm run test:backend
Build frontend     →  cd frontend && npm run build
Add Python dep     →  edit requirements.in → pip-compile → commit both
Link to issue      →  "Closes #N" in PR description
Never push to main →  always open a PR
Never commit .env  →  rotate the key immediately if it happens
```
