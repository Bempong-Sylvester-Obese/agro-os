### Task 1: Add `organization_type` to Cooperative model + DB migration

**Files:**
- Modify: `backend/app/models/models.py:101`
- Create: `backend/alembic/versions/007_organization_type.py`
- Modify: `backend/app/schemas/schemas.py:40-46`
- Modify: `backend/app/schemas/auth.py:43`

**Step 1: Add `organization_type` column to Cooperative model**

In `backend/app/models/models.py`, add after `subscription_plan` (line 101):

```python
organization_type = Column(String, default="cooperative", nullable=False)
```

**Step 2: Create Alembic migration**

Create `backend/alembic/versions/007_organization_type.py`:

```python
"""add organization_type to cooperatives

Revision ID: 007_organization_type
Revises: 006_farmer_finance_flows
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "007_organization_type"
down_revision = "006_farmer_finance_flows"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cooperatives",
        sa.Column("organization_type", sa.String(), server_default="cooperative", nullable=False),
    )


def downgrade():
    op.drop_column("cooperatives", "organization_type")
```

**Step 3: Update CooperativeResponse schema**

In `backend/app/schemas/schemas.py`, add to `CooperativeResponse`:

```python
organization_type: str = "cooperative"
```

And add to `CooperativeUpdate`:

```python
organization_type: Optional[str] = None
```

**Step 4: Update SignupRequest schema**

In `backend/app/schemas/auth.py`, update `SignupRequest`:

```python
organization_type: Literal["cooperative", "solo_farm"] = "cooperative"
```

Update `SignupResponse`:

```python
organization_type: str = "cooperative"
```

**Step 5: Run migration**

```bash
cd backend && alembic upgrade head
```
