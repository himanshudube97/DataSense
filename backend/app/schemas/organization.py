"""Organization schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.organization import OrgMemberRole, OrgType


class OrganizationBase(BaseModel):
    """Base organization schema."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""

    org_type: OrgType = OrgType.team


class OrganizationResponse(OrganizationBase):
    """Organization response schema."""

    id: uuid.UUID
    org_type: OrgType
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationWithMembers(OrganizationResponse):
    """Organization response with members."""

    members: list["MemberInfo"] = []


class MemberInfo(BaseModel):
    """Member info for organization response."""

    user_id: uuid.UUID
    email: str
    full_name: str
    role: OrgMemberRole
    joined_at: datetime

    model_config = {"from_attributes": True}


# Update forward reference
OrganizationWithMembers.model_rebuild()
