### Task 2: Create Worker model + schemas

**Files:**
- Create: `backend/app/models/worker.py`
- Create: `backend/app/schemas/worker.py`
- Modify: `backend/main.py`

**Step 1: Create Worker ORM model**

`backend/app/models/worker.py`:

```python
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.db import Base


class WorkerRole(str, enum.Enum):
    worker = "worker"
    supervisor = "supervisor"


class WorkerStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, index=True)
    wage_rate = Column(Float, default=0.0)
    role = Column(Enum(WorkerRole), default=WorkerRole.worker)
    status = Column(Enum(WorkerStatus), default=WorkerStatus.active)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cooperative = relationship("Cooperative")

    __table_args__ = (
        UniqueConstraint("cooperative_id", "phone", name="uq_worker_phone_per_coop"),
    )
```

**Step 2: Create Worker Pydantic schemas**

`backend/app/schemas/worker.py`:

```python
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class WorkerCreate(BaseModel):
    name: str
    phone: str
    wage_rate: float = 0.0
    role: Literal["worker", "supervisor"] = "worker"


class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    wage_rate: Optional[float] = None
    role: Optional[Literal["worker", "supervisor"]] = None
    status: Optional[Literal["active", "inactive"]] = None


class WorkerResponse(BaseModel):
    id: int
    cooperative_id: int
    name: str
    phone: str
    wage_rate: float
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

**Step 3: Register model import in main.py**

In `backend/main.py`, add among the other model imports:

```python
from app.models import worker  # noqa: F401
```
