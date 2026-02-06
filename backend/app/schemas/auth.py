import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    org_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class OrgInfo(BaseModel):
    id: uuid.UUID
    name: str
    role: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    created_at: datetime
    organizations: list[OrgInfo] = []

    model_config = {"from_attributes": True}
