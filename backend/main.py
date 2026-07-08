"""AgroOS Backend API — Main Application"""

import logging

import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database.db import Base, create_session, _init_db
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
    webhooks,
)
from app.agro_ai.runtime import agro_ai as agro_ai_runtime

logging.basicConfig(level=logging.INFO)

settings = get_settings()

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
    from app.database.db import engine  # engine is ready after _init_db()
    Base.metadata.create_all(bind=engine)

    if settings.seed_demo_data or settings.app_env == "development":
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
_origins = ["*"] if settings.app_env == "development" else [
    "https://agro-os.vercel.app",  # Update with actual frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def optional_admin_auth(request: Request, call_next):
    """Protect mutating API routes when AUTH_ENABLED=true."""
    if not settings.auth_enabled or request.method in {"GET", "HEAD", "OPTIONS"}:
        return await call_next(request)

    path = request.url.path
    if path.startswith("/auth/login") or path.startswith("/webhooks/"):
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
