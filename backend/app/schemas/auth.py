"""Authentication schemas."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"


class SignupRequest(BaseModel):
    """Signup request schema (via invitation)."""

    token: str
    full_name: str
    password: str
