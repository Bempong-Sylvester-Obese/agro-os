from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Literal["admin", "finance_officer", "farm_owner", "farm_manager", "supervisor"] = "finance_officer"

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

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    role: Literal["admin", "finance_officer", "farm_owner", "farm_manager", "supervisor"] | None = None
    is_active: bool | None = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse | None = None
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
    role: Literal[
        "admin", "finance_officer", "farm_owner", "farm_manager", "supervisor"
    ]


class AcceptInviteRequest(BaseModel):
    invite_token: str
    password: str
