"""Pydantic schemas for API request/response."""

from app.schemas.auth import LoginRequest, SignupRequest, Token
from app.schemas.invitation import InvitationCreate, InvitationResponse, InvitationValidation
from app.schemas.organization import (
    MemberInfo,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationWithMembers,
)
from app.schemas.user import OrganizationMembershipInfo, UserCreate, UserResponse, UserWithOrgs
from app.schemas.warehouse import (
    ColumnInfo,
    WarehouseConnectionCreate,
    WarehouseConnectionResponse,
    WarehouseConnectionStatus,
    WarehouseTableInfo,
    WarehouseTestResult,
)

__all__ = [
    # Auth
    "LoginRequest",
    "SignupRequest",
    "Token",
    # User
    "UserCreate",
    "UserResponse",
    "UserWithOrgs",
    "OrganizationMembershipInfo",
    # Organization
    "OrganizationCreate",
    "OrganizationResponse",
    "OrganizationWithMembers",
    "MemberInfo",
    # Invitation
    "InvitationCreate",
    "InvitationResponse",
    "InvitationValidation",
    # Warehouse
    "WarehouseConnectionCreate",
    "WarehouseConnectionResponse",
    "WarehouseConnectionStatus",
    "WarehouseTestResult",
    "WarehouseTableInfo",
    "ColumnInfo",
]
