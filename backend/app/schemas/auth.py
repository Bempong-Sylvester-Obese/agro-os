from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app.auth.roles import RoleLiteral


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: RoleLiteral = "finance_officer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool = True
    onboarding_role: str | None = None
    cooperative_id: int | None = None
    organization_id: int | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    role: RoleLiteral | None = None
    is_active: bool | None = None

class CurrentUserResponse(UserResponse):
    """Authoritative profile for the signed-in user (``GET /auth/me``).

    The frontend hydrates its session from this instead of inventing display
    strings from JWT claims (#251).
    """

    cooperative_name: str | None = None
    organization_type: str | None = None
    password_change_required: bool = False


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse | None = None
    cooperative_name: str | None = None
    organization_type: str | None = None
    password_change_required: bool = False

class SignupRequest(BaseModel):
    """Combined cooperative + user registration in one step."""
    email: EmailStr
    password: str
    cooperative_name: str
    location: Optional[str] = None
    member_count: Optional[int] = None  # stored as cooperative description hint
    subscription_plan: Literal["starter", "growth", "solo"] = "starter"
    organization_type: Literal["cooperative", "solo_farm"] = "cooperative"
    onboarding_role: str | None = Field(default=None, max_length=80)
    checkout_ref: str | None = None
    subscription_band: str | None = None

class SignupResponse(BaseModel):
    access_token: str
    token_type: str
    cooperative_id: int
    cooperative_name: str
    subscription_plan: Literal["starter", "growth", "solo"]
    subscription_status: str | None = "active"
    organization_type: str = "cooperative"
    onboarding_role: str | None = None
    subscription_band: str | None = None

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    reset_token: str
    new_password: str


class PasswordChangeRequest(BaseModel):
    new_password: str


class InviteUserRequest(BaseModel):
    email: str
    role: RoleLiteral


class RoleDescriptor(BaseModel):
    key: str
    label: str
    capabilities: str
    tracks: list[str]


class RoleCatalogue(BaseModel):
    roles: list[RoleDescriptor]


class AcceptInviteRequest(BaseModel):
    invite_token: str
    password: str
