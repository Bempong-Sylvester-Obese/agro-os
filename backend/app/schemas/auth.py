from pydantic import BaseModel, EmailStr
from typing import Literal, Optional

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
    cooperative_id: int | None = None

    class Config:
        from_attributes = True

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

class SignupResponse(BaseModel):
    access_token: str
    token_type: str
    cooperative_id: int
    cooperative_name: str
