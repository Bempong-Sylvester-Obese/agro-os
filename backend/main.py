"""AgroOS Backend API — Main Application"""

import logging

import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database.db import create_session, engine, _init_db
from app.database.seed import seed_golden_path
from app.dependencies.auth import decode_access_token
from app.routes import (
    agro_ai,
    auth,
    communications,
    cooperatives,
    farmers,
    loans,
    production,
    transactions,
    ussdk_hooks,
    webhooks,
)
from app.agro_ai.runtime import agro_ai as agro_ai_runtime

logging.basicConfig(level=logging.INFO)

settings = get_settings()

# Moolre callback POSTs must stay unauthenticated; other /webhooks routes do not.
_MOOLRE_CALLBACK_PATHS = frozenset({
    "/webhooks/moolre/payment",
    "/webhooks/moolre/ussd",
})

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB and create tables on startup."""
    _init_db()

    if settings.seed_demo_data:
        db = create_session()
        try:
            seed_golden_path(db)
        finally:
            db.close()

    yield


_is_production = settings.app_env == "production"
_docs_url = None if _is_production else "/docs"
_redoc_url = None if _is_production else "/redoc"

app = FastAPI(
    title="AgroOS API",
    description=(
        "Backend API for AgroOS — Digital Infrastructure for African Farmer Cooperatives.\n\n"
        "Powered by Moolre for payments, SMS, and USSD access."
    ),
    version="1.0.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=lifespan,
)

# Configure CORS
_dev_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
]
_prod_origins = [
    "https://agro-os-amber.vercel.app",
    "https://agroos.company",
    "https://www.agroos.company",
]
if settings.app_env.lower() in ("development", "dev"):
    _origins = ["*"]
    _allow_credentials = False
else:
    _origins = _dev_origins + _prod_origins
    if settings.cors_origins:
        _origins.extend([o.strip() for o in settings.cors_origins.split(",") if o.strip()])
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def optional_admin_auth(request: Request, call_next):
    """Protect mutating API routes when AUTH_ENABLED=true."""
    if not settings.auth_enabled or request.method in {"GET", "HEAD", "OPTIONS"}:
        return await call_next(request)

    path = request.url.path
    if path.startswith("/auth/login") or path in _MOOLRE_CALLBACK_PATHS:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})

    try:
        decode_access_token(auth_header.split(" ", 1)[1])
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return await call_next(request)

# Register all routers
app.include_router(auth.router)
app.include_router(cooperatives.router)
app.include_router(farmers.router)
app.include_router(transactions.router)
app.include_router(loans.router)
app.include_router(production.router)
app.include_router(communications.router)
app.include_router(webhooks.router)
app.include_router(ussdk_hooks.router)
app.include_router(agro_ai.router)


@app.get("/", tags=["health"])
def root():
    """API root — returns version info."""
    return {
        "message": "Welcome to AgroOS API",
        "version": "1.0.0",
        "environment": settings.app_env,
        "currency": settings.default_currency,
        "docs": _docs_url,
        "auth_enabled": settings.auth_enabled,
    }


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint for deployment monitors."""
    model_meta = agro_ai_runtime.metadata
    require_artifact = settings.agro_ai_require_artifact or settings.app_env == "production"
    model_ready = not (require_artifact and model_meta["is_synthetic_fallback"])
    status = "healthy" if model_ready else "degraded"

    return {
        "status": status,
        "model_ready": model_ready,
        **model_meta,
    }


def _readiness_payload() -> tuple[dict, bool]:
    """Build readiness metadata and report whether all required components are ready."""
    current_settings = get_settings()
    model_meta = agro_ai_runtime.metadata
    model_source = "synthetic" if model_meta["is_synthetic_fallback"] else "artifact"
    require_artifact = (
        current_settings.agro_ai_require_artifact
        or current_settings.app_env.lower() in {"production", "prod"}
    )
    model_ready = not (require_artifact and model_source == "synthetic")

    database = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logging.exception("Database readiness probe failed")
        database = "fail"

    ready = database == "ok" and model_ready
    return {
        "status": "ready" if ready else "not_ready",
        "database": database,
        "model_source": model_source,
        "model_ready": model_ready,
        **model_meta,
    }, ready


@app.get("/health/live", tags=["health"])
def health_live():
    """Liveness probe: the API process can accept requests."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def health_ready():
    """Readiness probe: database connectivity and required model are available."""
    payload, ready = _readiness_payload()
    if not ready:
        return JSONResponse(status_code=503, content=payload)
    return payload


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
