### Tasks 4+5: Expand role validators + wire org_type through signup

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/routes/auth.py`

**Step 1: Expand role Literals in auth schemas**

In `backend/app/schemas/auth.py`:

Change `UserCreate.role`:
```python
role: Literal["admin", "finance_officer", "farm_owner", "farm_manager", "supervisor"] = "finance_officer"
```

Change `UserUpdate.role`:
```python
role: Literal["admin", "finance_officer", "farm_owner", "farm_manager", "supervisor"] | None = None
```

**Step 2: Wire organization_type through signup route**

In `backend/app/routes/auth.py`, in the signup function, add `organization_type` when creating the cooperative:

```python
new_coop = Cooperative(
    name=data.cooperative_name,
    location=data.location,
    description=description,
    currency="GHS",
    subscription_plan=data.subscription_plan,
    organization_type=data.organization_type,
)
```

And in the signup return dict, add:
```python
"organization_type": data.organization_type,
```

**Step 3: Verify**
- Run `python -c "from app.schemas.auth import UserCreate; print('OK')"` from backend dir
- Run `python -c "from app.routes.auth import router; print('OK')"` from backend dir
