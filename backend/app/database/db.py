"""Database Connection and Session Management"""

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

# Base class shared by all models
Base = declarative_base()

# Module-level placeholders — populated lazily by _init_db()
_engine = None
_SessionLocal = None


def _engine_kwargs(database_url: str, *, echo: bool) -> dict:
    """Build create_engine kwargs with fail-fast timeouts for hosted Postgres."""
    kwargs: dict = {
        "echo": echo,
        "pool_pre_ping": True,
    }
    try:
        backend = make_url(database_url).get_backend_name()
    except Exception:
        backend = ""
    if backend.startswith("postgresql"):
        # QueuePool options are Postgres-only; SQLite tests use SingletonThreadPool.
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 5
        # Avoid Render boot loops that hang forever on unreachable DB / lock waits.
        kwargs["connect_args"] = {
            "connect_timeout": 10,
            "options": "-c lock_timeout=10000 -c statement_timeout=60000",
        }
    return kwargs


def _init_db():
    """Lazily create the engine and session factory on first use."""
    global _engine, _SessionLocal
    if _engine is None:
        from app.config import get_settings

        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            **_engine_kwargs(settings.database_url, echo=settings.debug),
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
