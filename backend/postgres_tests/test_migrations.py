"""PostgreSQL migration smoke tests for fresh and adopted metadata schemas."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from alembic import command
from app.config import get_settings
from app.database.db import Base

DATABASE_URL = os.environ.get("POSTGRES_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="POSTGRES_TEST_DATABASE_URL is required",
)


def _config(database_url: str) -> Config:
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    return config


def _reset_schema(admin_engine, schema: str) -> None:
    with admin_engine.begin() as connection:
        connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        connection.execute(CreateSchema(schema))


def test_migrations_adopt_fresh_metadata_and_harden_existing_rows():
    schema = f"agro_migrations_{uuid4().hex}"
    original_database_url = os.environ.get("DATABASE_URL")
    admin_engine = create_engine(DATABASE_URL)
    scoped_url = make_url(DATABASE_URL).set(
        query={
            **dict(make_url(DATABASE_URL).query),
            "options": f"-csearch_path={schema}",
        }
    )
    scoped_database_url = scoped_url.render_as_string(hide_password=False)
    engine = create_engine(scoped_url)
    config = _config(scoped_database_url)

    try:
        _reset_schema(admin_engine, schema)
        Base.metadata.create_all(engine)
        command.upgrade(config, "head")
        assert inspect(engine).has_table("demo_bookings")

        _reset_schema(admin_engine, schema)
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
                    "ALTER TABLE transactions "
                    "DROP COLUMN action_expires_at, "
                    "DROP COLUMN customer_action, "
                    "DROP COLUMN initiation_channel, "
                    "DROP COLUMN loan_id"
                )
            )
            connection.execute(
                text("ALTER TABLE loans DROP COLUMN request_channel")
            )
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
                    "VALUES (:cooperative_id, 'legacy@example.com', "
                    "'legacy.action', NULL)"
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
        transaction_columns = {
            column["name"] for column in inspect(engine).get_columns("transactions")
        }
        assert {
            "action_expires_at",
            "customer_action",
            "initiation_channel",
            "loan_id",
        }.issubset(transaction_columns)
        loan_columns = {
            column["name"] for column in inspect(engine).get_columns("loans")
        }
        assert "request_channel" in loan_columns
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT created_at IS NOT NULL FROM admin_audit_logs "
                    "WHERE action = 'legacy.action'"
                )
            ).scalar_one()
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        admin_engine.dispose()
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url
        get_settings.cache_clear()
