"""Invitation schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.organization import OrgMemberRole


class InvitationCreate(BaseModel):
    """Schema for creating an invitation."""

    email: EmailStr
    organization_id: uuid.UUID
    role: OrgMemberRole = OrgMemberRole.member


class InvitationResponse(BaseModel):
    """Invitation response schema."""

    id: uuid.UUID
    email: str
    organization_id: uuid.UUID
    organization_name: str
    role: OrgMemberRole
    expires_at: datetime
    created_at: datetime
    is_expired: bool
    is_accepted: bool

    model_config = {"from_attributes": True}


class InvitationValidation(BaseModel):
    """Invitation validation response."""

    valid: bool
    email: str | None = None
    organization_name: str | None = None
    role: OrgMemberRole | None = None
    message: str | None = None
