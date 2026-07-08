"""Minimal JWT admin authentication for demo deployments."""

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.dependencies.auth import create_access_token
from app.schemas.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    email = payload.email.strip().lower()
    if email != settings.admin_email.lower() or payload.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(email)
    return LoginResponse(
        access_token=token,
        user={
            "email": email,
            "name": "Cooperative Admin",
            "initials": "CA",
            "role": "Finance Officer",
        },
    )
