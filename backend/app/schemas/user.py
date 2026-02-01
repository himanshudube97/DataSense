"""User schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str


class UserResponse(UserBase):
    """User response schema."""

    id: uuid.UUID
    is_active: bool
    is_superadmin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserWithOrgs(UserResponse):
    """User response with organization memberships."""

    organizations: list["OrganizationMembershipInfo"] = []


class OrganizationMembershipInfo(BaseModel):
    """Organization membership info for user response."""

    organization_id: uuid.UUID
    organization_name: str
    role: str

    model_config = {"from_attributes": True}


# Update forward reference
UserWithOrgs.model_rebuild()
