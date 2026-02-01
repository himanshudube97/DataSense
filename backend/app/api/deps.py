"""API dependencies for authentication and authorization."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import OrganizationMember, OrgMemberRole, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    Raises HTTPException 401 if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == user_uuid, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user (alias for get_current_user with active check)."""
    return current_user


async def require_superadmin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Require the current user to be a superadmin.

    Raises HTTPException 403 if user is not a superadmin.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return current_user


class RequireOrgRole:
    """
    Dependency class to require a specific role in an organization.

    Usage:
        @router.get("/orgs/{org_id}/settings")
        async def get_settings(
            org_id: uuid.UUID,
            current_user: User = Depends(RequireOrgRole(OrgMemberRole.admin)),
            db: AsyncSession = Depends(get_db),
        ):
            ...
    """

    def __init__(self, min_role: OrgMemberRole):
        """
        Initialize with minimum required role.

        Role hierarchy: OWNER > ADMIN > MEMBER > VIEWER
        """
        self.min_role = min_role
        self.role_hierarchy = {
            OrgMemberRole.viewer: 0,
            OrgMemberRole.member: 1,
            OrgMemberRole.admin: 2,
            OrgMemberRole.owner: 3,
        }

    async def __call__(
        self,
        org_id: uuid.UUID,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        """Check if user has required role in the organization."""
        # Superadmins bypass org role checks
        if current_user.is_superadmin:
            return current_user

        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == org_id,
                OrganizationMember.deleted_at.is_(None),
            )
        )
        membership = result.scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization",
            )

        user_role_level = self.role_hierarchy.get(membership.role, 0)
        required_role_level = self.role_hierarchy.get(self.min_role, 0)

        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {self.min_role.value} role or higher",
            )

        return current_user


# Common role dependencies
require_org_viewer = RequireOrgRole(OrgMemberRole.viewer)
require_org_member = RequireOrgRole(OrgMemberRole.member)
require_org_admin = RequireOrgRole(OrgMemberRole.admin)
require_org_owner = RequireOrgRole(OrgMemberRole.owner)
