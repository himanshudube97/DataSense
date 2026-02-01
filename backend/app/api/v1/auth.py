"""Authentication API routes."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Invitation, Organization, OrganizationMember, User
from app.schemas import (
    InvitationValidation,
    OrganizationMembershipInfo,
    SignupRequest,
    Token,
    UserWithOrgs,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Login with email and password.

    Returns a JWT access token valid for 7 days.
    """
    result = await db.execute(
        select(User).where(User.email == form_data.username, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)


@router.get("/me", response_model=UserWithOrgs)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserWithOrgs:
    """Get current user info with organization memberships."""
    # Load organization memberships with org details
    result = await db.execute(
        select(OrganizationMember, Organization)
        .join(Organization, OrganizationMember.organization_id == Organization.id)
        .where(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.deleted_at.is_(None),
            Organization.deleted_at.is_(None),
        )
    )
    memberships = result.all()

    org_info = [
        OrganizationMembershipInfo(
            organization_id=membership.organization_id,
            organization_name=org.name,
            role=membership.role.value,
        )
        for membership, org in memberships
    ]

    return UserWithOrgs(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superadmin=current_user.is_superadmin,
        created_at=current_user.created_at,
        organizations=org_info,
    )


@router.get("/invite/{token}", response_model=InvitationValidation)
async def validate_invitation(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvitationValidation:
    """
    Validate an invitation token.

    Returns invitation details if valid, or error message if invalid.
    """
    result = await db.execute(
        select(Invitation, Organization)
        .join(Organization, Invitation.organization_id == Organization.id)
        .where(Invitation.token == token)
    )
    row = result.one_or_none()

    if row is None:
        return InvitationValidation(valid=False, message="Invalid invitation token")

    invitation, org = row

    if invitation.is_accepted:
        return InvitationValidation(valid=False, message="Invitation has already been used")

    if invitation.is_expired:
        return InvitationValidation(valid=False, message="Invitation has expired")

    return InvitationValidation(
        valid=True,
        email=invitation.email,
        organization_name=org.name,
        role=invitation.role,
    )


@router.post("/signup", response_model=Token)
async def signup(
    data: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Sign up using an invitation token.

    Creates a new user account and adds them to the organization.
    Returns a JWT access token.
    """
    # Validate invitation
    result = await db.execute(
        select(Invitation).where(Invitation.token == data.token)
    )
    invitation = result.scalar_one_or_none()

    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation token",
        )

    if invitation.is_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been used",
        )

    if invitation.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == invitation.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Create user
    user = User(
        email=invitation.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        is_active=True,
        is_superadmin=False,
    )
    db.add(user)
    await db.flush()

    # Add user to organization
    membership = OrganizationMember(
        user_id=user.id,
        organization_id=invitation.organization_id,
        role=invitation.role,
    )
    db.add(membership)

    # Mark invitation as accepted
    invitation.accepted_at = datetime.now(timezone.utc)

    await db.commit()

    # Generate token
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)
