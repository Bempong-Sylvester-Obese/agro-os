"""PostgreSQL migration smoke tests for fresh and adopted metadata schemas."""

import os
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.config import get_settings
from app.database.db import Base

DATABASE_URL = os.environ.get("POSTGRES_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="POSTGRES_TEST_DATABASE_URL is required",
)


def _config() -> Config:
    os.environ["DATABASE_URL"] = DATABASE_URL
    get_settings.cache_clear()
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    return config


def _reset_schema(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


def test_migrations_adopt_fresh_metadata_and_harden_existing_rows():
    engine = create_engine(DATABASE_URL)
    config = _config()

    _reset_schema(engine)
    Base.metadata.create_all(engine)
    command.upgrade(config, "head")
    assert inspect(engine).has_table("demo_bookings")

    _reset_schema(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE admin_action_confirmations"))
        connection.execute(text("DROP TABLE demo_bookings"))
        connection.execute(
            text("ALTER TABLE cooperatives DROP COLUMN subscription_plan")
        )
        connection.execute(text("ALTER TABLE users DROP COLUMN onboarding_role"))
        connection.execute(
            text(
                "ALTER TABLE admin_audit_logs "
                "ALTER COLUMN created_at DROP NOT NULL, "
                "ALTER COLUMN created_at DROP DEFAULT"
            )
        )
        cooperative_id = connection.execute(
            text(
                "INSERT INTO cooperatives (name, currency) "
                "VALUES ('Adopted Cooperative', 'GHS') RETURNING id"
            )
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO admin_audit_logs "
                "(cooperative_id, actor_id, action, created_at) "
                "VALUES (:cooperative_id, 'legacy@example.com', 'legacy.action', NULL)"
            ),
            {"cooperative_id": cooperative_id},
        )
    command.stamp(config, "004_user_active")
    command.upgrade(config, "head")

    columns = {
        column["name"]: column
        for column in inspect(engine).get_columns("admin_audit_logs")
    }
    assert columns["created_at"]["nullable"] is False
    assert columns["created_at"]["default"] is not None
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT created_at IS NOT NULL FROM admin_audit_logs "
                "WHERE action = 'legacy.action'"
            )
        ).scalar_one()

    engine.dispose()
