"""AgroOS Backend API — Main Application"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from contextlib import asynccontextmanager

from app.database.db import Base, _init_db
from app.routes import (
    communications,
    cooperatives,
    farmers,
    loans,
    production,
    transactions,
    webhooks,
)

logging.basicConfig(level=logging.INFO)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB and create tables on startup."""
    _init_db()
    from app.database.db import engine  # engine is ready after _init_db()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AgroOS API",
    description=(
        "Backend API for AgroOS — Digital Infrastructure for African Farmer Cooperatives.\n\n"
        "Powered by Moolre for payments, SMS, and USSD access."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

# Register all routers
app.include_router(cooperatives.router)
app.include_router(farmers.router)
app.include_router(transactions.router)
app.include_router(loans.router)
app.include_router(production.router)
app.include_router(communications.router)
app.include_router(webhooks.router)


@app.get("/", tags=["health"])
def root():
    """API root — returns version info."""
    return {
        "message": "Welcome to AgroOS API",
        "version": "1.0.0",
        "environment": settings.app_env,
        "currency": settings.default_currency,
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint for deployment monitors."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
