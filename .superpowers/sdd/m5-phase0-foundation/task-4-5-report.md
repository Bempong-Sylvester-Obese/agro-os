# Tasks 4+5 Report — Expand role validators + wire org_type through signup

**Status:** ✅ Done

**Commit:** `b743677`

**Changes:**
- `backend/app/schemas/auth.py`: `UserCreate.role` and `UserUpdate.role` expanded to include `farm_owner`, `farm_manager`, `supervisor`
- `backend/app/routes/auth.py`: `organization_type` added to `Cooperative` creation and signup response dict

**Verification:**
- `from app.schemas.auth import UserCreate` → OK
- `from app.routes.auth import router` → OK

**Concerns:** None.
