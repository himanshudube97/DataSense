"""Admin API routes for organization and user management."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_org_admin, require_superadmin
from app.core.config import settings
from app.core.database import get_db
from app.models import Invitation, Organization, OrganizationMember, OrgMemberRole, User
from app.schemas import (
    InvitationCreate,
    InvitationResponse,
    MemberInfo,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationWithMembers,
)

router = APIRouter(tags=["Admin"])


# ============================================================================
# Organization Management (Superadmin only)
# ============================================================================


@router.post("/admin/organizations", response_model=OrganizationResponse)
async def create_organization(
    data: OrganizationCreate,
    current_user: Annotated[User, Depends(require_superadmin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationResponse:
    """
    Create a new organization.

    Superadmin only.
    """
    # Check if slug already exists
    result = await db.execute(
        select(Organization).where(
            Organization.slug == data.slug, Organization.deleted_at.is_(None)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization with this slug already exists",
        )

    org = Organization(
        name=data.name,
        slug=data.slug,
        description=data.description,
        org_type=data.org_type,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)

    return OrganizationResponse.model_validate(org)


@router.get("/admin/organizations", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: Annotated[User, Depends(require_superadmin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrganizationResponse]:
    """
    List all organizations.

    Superadmin only.
    """
    result = await db.execute(
        select(Organization)
        .where(Organization.deleted_at.is_(None))
        .order_by(Organization.created_at.desc())
    )
    orgs = result.scalars().all()
    return [OrganizationResponse.model_validate(org) for org in orgs]


@router.get("/admin/organizations/{org_id}", response_model=OrganizationWithMembers)
async def get_organization(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_superadmin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationWithMembers:
    """
    Get organization details with members.

    Superadmin only.
    """
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_id, Organization.deleted_at.is_(None)
        )
    )
    org = result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Get members
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.deleted_at.is_(None),
        )
    )
    members_data = result.all()

    members = [
        MemberInfo(
            user_id=member.user_id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            joined_at=member.created_at,
        )
        for member, user in members_data
    ]

    return OrganizationWithMembers(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        org_type=org.org_type,
        created_at=org.created_at,
        members=members,
    )


# ============================================================================
# Invitation Management
# ============================================================================


@router.post("/invitations", response_model=InvitationResponse)
async def create_invitation(
    data: InvitationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvitationResponse:
    """
    Create an invitation to join an organization.

    - Superadmins can invite to any organization with any role
    - Org admins/owners can invite to their organization (up to their own role)
    """
    # Check organization exists
    result = await db.execute(
        select(Organization).where(
            Organization.id == data.organization_id, Organization.deleted_at.is_(None)
        )
    )
    org = result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Permission check
    if not current_user.is_superadmin:
        # Check if user is admin/owner of the org
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == data.organization_id,
                OrganizationMember.deleted_at.is_(None),
            )
        )
        membership = result.scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization",
            )

        if membership.role not in [OrgMemberRole.admin, OrgMemberRole.owner]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and owners can invite members",
            )

        # Can only invite up to their own role level
        role_hierarchy = {
            OrgMemberRole.viewer: 0,
            OrgMemberRole.member: 1,
            OrgMemberRole.admin: 2,
            OrgMemberRole.owner: 3,
        }
        if role_hierarchy[data.role] > role_hierarchy[membership.role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot invite with a role higher than your own",
            )

    # Check if user already exists in org
    result = await db.execute(
        select(User).where(User.email == data.email, User.deleted_at.is_(None))
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == existing_user.id,
                OrganizationMember.organization_id == data.organization_id,
                OrganizationMember.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization",
            )

    # Check for pending invitation
    result = await db.execute(
        select(Invitation).where(
            Invitation.email == data.email,
            Invitation.organization_id == data.organization_id,
            Invitation.accepted_at.is_(None),
        )
    )
    existing_invitation = result.scalar_one_or_none()

    if existing_invitation and not existing_invitation.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending invitation already exists for this email",
        )

    # Create invitation
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.INVITATION_EXPIRE_DAYS)

    invitation = Invitation(
        email=data.email,
        organization_id=data.organization_id,
        role=data.role,
        token=token,
        expires_at=expires_at,
        invited_by_id=current_user.id,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        organization_id=invitation.organization_id,
        organization_name=org.name,
        role=invitation.role,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        is_expired=invitation.is_expired,
        is_accepted=invitation.is_accepted,
    )


@router.get("/organizations/{org_id}/invitations", response_model=list[InvitationResponse])
async def list_organization_invitations(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[InvitationResponse]:
    """
    List pending invitations for an organization.

    Requires admin role in the organization.
    """
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_id, Organization.deleted_at.is_(None)
        )
    )
    org = result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    result = await db.execute(
        select(Invitation)
        .where(
            Invitation.organization_id == org_id,
            Invitation.accepted_at.is_(None),
        )
        .order_by(Invitation.created_at.desc())
    )
    invitations = result.scalars().all()

    return [
        InvitationResponse(
            id=inv.id,
            email=inv.email,
            organization_id=inv.organization_id,
            organization_name=org.name,
            role=inv.role,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            is_expired=inv.is_expired,
            is_accepted=inv.is_accepted,
        )
        for inv in invitations
    ]


# ============================================================================
# Organization Member Management
# ============================================================================


@router.get("/organizations/{org_id}/members", response_model=list[MemberInfo])
async def list_organization_members(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MemberInfo]:
    """
    List members of an organization.

    Requires membership in the organization (any role).
    """
    # Check org exists
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_id, Organization.deleted_at.is_(None)
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check user is member (unless superadmin)
    if not current_user.is_superadmin:
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == org_id,
                OrganizationMember.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization",
            )

    # Get members
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.deleted_at.is_(None),
        )
    )
    members_data = result.all()

    return [
        MemberInfo(
            user_id=member.user_id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            joined_at=member.created_at,
        )
        for member, user in members_data
    ]


@router.delete("/organizations/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Remove a member from an organization.

    Requires admin role in the organization.
    Cannot remove yourself or the last owner.
    """
    # Get the membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id,
            OrganizationMember.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in organization",
        )

    # Prevent self-removal
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the organization",
        )

    # If removing an owner, check there's at least one other owner
    if membership.role == OrgMemberRole.owner:
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.role == OrgMemberRole.owner,
                OrganizationMember.deleted_at.is_(None),
                OrganizationMember.user_id != user_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner of the organization",
            )

    # Soft delete the membership
    membership.deleted_at = datetime.now(timezone.utc)
    await db.commit()
