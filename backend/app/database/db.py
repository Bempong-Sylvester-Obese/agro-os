"""Database Connection and Session Management"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Base class shared by all models
Base = declarative_base()

# Module-level placeholders — populated lazily by _init_db()
_engine = None
_SessionLocal = None


def _init_db():
    """Lazily create the engine and session factory on first use."""
    global _engine, _SessionLocal
    if _engine is None:
        from app.config import get_settings

        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


# Expose `engine` and `SessionLocal` as module attributes so that
# `main.py` (Base.metadata.create_all) and tests can still import them.
class _LazyEngine:
    """Proxy that defers engine creation until first attribute access."""

    def __getattr__(self, name):
        _init_db()
        return getattr(_engine, name)


engine = _LazyEngine()


def get_db():
    """FastAPI dependency — yields a database session per request."""
    _init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_session():
    """Return a standalone DB session (for startup tasks such as seeding)."""
    _init_db()
    return _SessionLocal()
