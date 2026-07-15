"""PostgreSQL-only checks for row-lock based administrator invariants."""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.models.models import Cooperative, User
from app.routes.auth import update_user
from app.schemas.auth import UserUpdate
from app.services.auth_service import get_password_hash

DATABASE_URL = os.environ.get("POSTGRES_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="POSTGRES_TEST_DATABASE_URL is required",
)


def test_concurrent_admin_demotions_preserve_one_active_admin():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as db:
        cooperative = Cooperative(name="Locking Cooperative")
        db.add(cooperative)
        db.flush()
        admins = [
            User(
                email=f"locking-admin-{index}@example.com",
                hashed_password=get_password_hash("strong-password"),
                role="admin",
                cooperative_id=cooperative.id,
            )
            for index in range(2)
        ]
        db.add_all(admins)
        db.commit()
        cooperative_id = cooperative.id
        admin_ids = [admin.id for admin in admins]

    def demote(actor_id: int, target_id: int):
        with session_factory() as db:
            actor = db.query(User).filter(User.id == actor_id).one()
            try:
                update_user(
                    target_id,
                    UserUpdate(role="finance_officer"),
                    db,
                    actor,
                )
                return "updated"
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                lambda pair: demote(*pair),
                [(admin_ids[0], admin_ids[1]), (admin_ids[1], admin_ids[0])],
            )
        )

    assert sorted(outcomes, key=str) == [409, "updated"]
    with session_factory() as db:
        active_admins = (
            db.query(User)
            .filter(
                User.cooperative_id == cooperative_id,
                User.role == "admin",
                User.is_active.is_(True),
            )
            .count()
        )
        assert active_admins == 1

    engine.dispose()
