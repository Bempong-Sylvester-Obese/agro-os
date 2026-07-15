from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Literal["admin", "finance_officer"] = "finance_officer"

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
    role: Literal["admin", "finance_officer"] | None = None
    is_active: bool | None = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse | None = None

class SignupRequest(BaseModel):
    """Combined cooperative + user registration in one step."""
    email: EmailStr
    password: str
    cooperative_name: str
    location: Optional[str] = None
    member_count: Optional[int] = None  # stored as cooperative description hint
    subscription_plan: Literal["starter", "growth"] = "starter"
    onboarding_role: str | None = Field(default=None, max_length=80)

class SignupResponse(BaseModel):
    access_token: str
    token_type: str
    cooperative_id: int
    cooperative_name: str
    subscription_plan: Literal["starter", "growth"]
    onboarding_role: str | None = None
