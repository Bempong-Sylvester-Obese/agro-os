"""
Test configuration and fixtures.

Uses an in-memory SQLite database so tests have zero external dependencies
and no file-locking issues on Windows.
DATABASE_URL is patched BEFORE any app code is imported so the lazy
db.py engine never tries to connect to Postgres.
"""

import os

# --------------------------------------------------------------------------
# Override DB URL BEFORE any app imports — lazy engine picks this up.
# --------------------------------------------------------------------------
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MOOLRE_API_USER"] = "test-user"
os.environ["MOOLRE_ACCOUNT_NUMBER"] = "TEST-ACCOUNT-001"
os.environ["AUTH_ENABLED"] = "false"
os.environ["APP_ENV"] = "test"
os.environ["MOOLRE_WEBHOOK_SECRET"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database.db import Base, get_db

get_settings.cache_clear()
from main import app

# --------------------------------------------------------------------------
# Shared in-memory SQLite engine
# SQLite requires connect_args={"check_same_thread": False} for FastAPI.
# We use a single shared connection so the same in-memory DB is visible
# across the test session — in-memory DBs disappear when the connection closes.
# --------------------------------------------------------------------------

_connection = None
_engine = None
TestingSessionLocal = None


def _get_engine():
    global _connection, _engine, TestingSessionLocal
    if _engine is None:
        _engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        # Keep a single connection alive for the whole session
        _connection = _engine.connect()
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=_connection
        )
        Base.metadata.create_all(bind=_connection)
    return _engine


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create tables once and keep the connection alive for the whole session."""
    _get_engine()
    yield
    if _connection:
        _connection.close()


@pytest.fixture()
def db():
    """
    Yield a DB session per test.
    Uses a nested transaction (SAVEPOINT) that is rolled back after each test.
    """
    _get_engine()
    nested = _connection.begin_nested()
    session = TestingSessionLocal()
    yield session
    session.close()
    nested.rollback()


@pytest.fixture()
def client(db):
    """FastAPI TestClient with DB dependency overridden to use the test session."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------
# Shared factory fixtures
# --------------------------------------------------------------------------


@pytest.fixture()
def demo_admin(db):
    """Demo admin user for auth integration tests."""
    from app.models.models import Cooperative, User
    from app.services.auth_service import get_password_hash

    coop = Cooperative(name="Kuapa Kokoo Demo", currency="GHS")
    db.add(coop)
    db.flush()
    user = User(
        email="admin@agroos.demo",
        hashed_password=get_password_hash("demo1234"),
        role="admin",
        cooperative_id=coop.id,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def cooperative(client):
    resp = client.post(
        "/cooperatives/",
        json={
            "name": "Kuapa Kokoo",
            "description": "Test cooperative",
            "location": "Kumasi, Ghana",
            "currency": "GHS",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def farmer(client, cooperative):
    resp = client.post(
        "/farmers/",
        json={
            "name": "Kofi Mensah",
            "phone": "+233551000001",
            "cooperative_id": cooperative["id"],
            "location": "Ashanti Region",
            "crop_type": "Cocoa",
            "acreage": 5.0,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def transaction(client, farmer):
    resp = client.post(
        "/transactions/",
        json={
            "farmer_id": farmer["id"],
            "transaction_type": "dues",
            "amount": 50.0,
            "currency": "GHS",
            "description": "Monthly dues",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
