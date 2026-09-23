import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.models.models import StaffRefreshToken, User

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
optional_bearer = HTTPBearer(auto_error=False)


def _secret_key() -> str:
    return get_settings().secret_key


def access_token_minutes() -> int:
    """Configured access-token lifetime (#248): 60 min in production unless
    ``ACCESS_TOKEN_EXPIRE_MINUTES`` overrides it (capped at 24h there)."""
    return get_settings().effective_access_token_minutes


def session_claims(user: User) -> dict:
    """Claims embedded in every staff access token; single source of truth so
    login, signup, scope switching and refresh all agree."""
    cooperative = user.cooperative
    return {
        "sub": user.email,
        "user_id": user.id,
        "cooperative_id": user.cooperative_id,
        "organization_id": user.organization_id,
        "role": user.role,
        "organization_type": cooperative.organization_type if cooperative else None,
    }


def issue_access_token(user: User) -> str:
    return create_access_token(session_claims(user), expires_delta=timedelta(minutes=access_token_minutes()))


def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_refresh_token(db: Session, user: User) -> str:
    """Create an opaque, single-use refresh token and persist only its hash."""
    raw = secrets.token_urlsafe(48)
    db.add(
        StaffRefreshToken(
            user_id=user.id,
            token_hash=_hash_refresh_token(raw),
            expires_at=datetime.utcnow() + timedelta(days=get_settings().refresh_token_expire_days),
        )
    )
    db.flush()
    return raw


def rotate_refresh_token(db: Session, raw: str) -> tuple[User, str]:
    """Exchange a live refresh token for a new one (rotation).

    The presented token is revoked whether or not the exchange succeeds so a
    replayed token cannot be used twice. Raises 401 on unknown, expired,
    revoked or inactive-user tokens.
    """
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    if not raw:
        raise invalid
    record = db.query(StaffRefreshToken).filter(StaffRefreshToken.token_hash == _hash_refresh_token(raw)).first()
    if record is None:
        raise invalid
    now = datetime.utcnow()
    if record.revoked_at is not None or record.expires_at <= now:
        # Replay of a *rotated* token is treated as theft (the original holder
        # already received a replacement). Logout / password-change revokes
        # without rotating and must not kill a newly issued session.
        if record.rotated:
            revoke_user_refresh_tokens(db, record.user_id)
            db.commit()
        raise invalid
    user = db.query(User).filter(User.id == record.user_id).first()
    if user is None or not user.is_active:
        record.revoked_at = now
        db.commit()
        raise invalid
    record.revoked_at = now
    record.rotated = True
    new_raw = issue_refresh_token(db, user)
    db.commit()
    return user, new_raw


def revoke_user_refresh_tokens(db: Session, user_id: int) -> int:
    """Revoke every live refresh token for a user (password change/reset, deactivation)."""
    now = datetime.utcnow()
    return (
        db.query(StaffRefreshToken)
        .filter(StaffRefreshToken.user_id == user_id, StaffRefreshToken.revoked_at.is_(None))
        .update({StaffRefreshToken.revoked_at: now}, synchronize_session=False)
    )


def revoke_refresh_token(db: Session, raw: str | None) -> bool:
    """Revoke one presented refresh token (logout). Unknown tokens are ignored."""
    if not raw:
        return False
    record = db.query(StaffRefreshToken).filter(StaffRefreshToken.token_hash == _hash_refresh_token(raw)).first()
    if record is None or record.revoked_at is not None:
        return False
    record.revoked_at = datetime.utcnow()
    return True


def session_response(db: Session, user: User, *, refresh_token: str | None = None, **extra) -> dict:
    """Login/refresh payload: short-lived access token + rotating refresh token.

    Pass ``refresh_token`` when one was already minted (rotation) so exactly
    one live refresh token is created per exchange.
    """
    payload = {
        "access_token": issue_access_token(user),
        "refresh_token": refresh_token or issue_refresh_token(db, user),
        "token_type": "bearer",
        "expires_in": access_token_minutes() * 60,
    }
    payload.update(extra)
    return payload


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, _secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def _authenticated_user(token: str | None, db: Session) -> User | None:
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = decode_access_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except HTTPException:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = _authenticated_user(token, db)
    if user is not None and user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required",
        )
    return user


def get_password_change_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Authenticate a user without blocking the required-password-change endpoint."""
    return _authenticated_user(token, db)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, _secret_key(), algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        return (
            db.query(User)
            .filter(User.email == email, User.is_active.is_(True))
            .first()
        )
    except jwt.PyJWTError:
        return None


def require_authenticated_user(
    current_user: User | None = Depends(get_current_user),
) -> User:
    settings = get_settings()
    if not settings.auth_enabled or current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


def require_roles(*allowed_roles: str):
    """Require an authenticated user with one of the supplied roles."""
    normalized = {role.lower() for role in allowed_roles}

    def dependency(current_user: User | None = Depends(get_current_user)) -> User | None:
        if not get_settings().auth_enabled:
            return None
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if (current_user.role or "").lower() not in normalized:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return dependency


def enforce_cooperative_scope(current_user: User | None, cooperative_id: int) -> None:
    """Reject authenticated cross-cooperative access without leaking tenant data."""
    if current_user is not None and current_user.cooperative_id != cooperative_id:
        raise HTTPException(status_code=404, detail="Resource not found")


def generate_reset_or_invite_token() -> str:
    return secrets.token_hex(32)

def reset_token_valid(user) -> bool:
    if not user.reset_token or not user.reset_token_expires_at:
        return False
    return datetime.utcnow() < user.reset_token_expires_at

def invite_token_valid(user) -> bool:
    if not user.invite_token or not user.invite_token_expires_at:
        return False
    return datetime.utcnow() < user.invite_token_expires_at
