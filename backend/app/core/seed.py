"""
Seed script to create initial superadmin user and default organization.

Run with: python -m app.core.seed
"""
import asyncio
import uuid

from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.organization import Organization, OrganizationMember

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_superadmin_with_org(session: AsyncSession) -> None:
    """Create the initial superadmin user and default organization."""

    # Check if superadmin already exists
    result = await session.execute(
        select(User).where(User.email == settings.SUPERADMIN_EMAIL)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        print(f"Superadmin user already exists: {settings.SUPERADMIN_EMAIL}")

        # Check if user has an organization
        result = await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == existing_user.id,
                OrganizationMember.deleted_at.is_(None),
            )
        )
        membership = result.scalar_one_or_none()

        if membership:
            print("Superadmin already has an organization.")
            return

        superadmin = existing_user
    else:
        # Create superadmin user
        password_hash = pwd_context.hash(settings.SUPERADMIN_PASSWORD)
        superadmin = User(
            email=settings.SUPERADMIN_EMAIL,
            password_hash=password_hash,
            full_name="Dalgo Admin",
            is_active=True,
            is_superadmin=True,
        )
        session.add(superadmin)
        await session.flush()
        print(f"Created superadmin user: {settings.SUPERADMIN_EMAIL}")

    # Check if default organization exists (use raw SQL to avoid enum issue)
    result = await session.execute(
        text("""
            SELECT id FROM organizations
            WHERE slug = 'dalgo-default' AND deleted_at IS NULL
        """)
    )
    existing_org = result.fetchone()
    org_id = existing_org[0] if existing_org else None
    org = None  # We'll use org_id directly

    if not org_id:
        # Create default organization using raw SQL to handle enum properly
        org_id = uuid.uuid4()
        await session.execute(
            text("""
                INSERT INTO organizations (id, name, slug, description, org_type, settings)
                VALUES (:id, :name, :slug, :description, 'team', '{}')
            """),
            {
                "id": org_id,
                "name": "Dalgo Default",
                "slug": "dalgo-default",
                "description": "Default organization for Dalgo Lite",
            }
        )
        print("Created default organization: Dalgo Default")
    else:
        org_id = org.id

    # Check if membership already exists
    result = await session.execute(
        text("""
            SELECT id FROM organization_members
            WHERE user_id = :user_id AND organization_id = :org_id
        """),
        {"user_id": superadmin.id, "org_id": org_id}
    )
    existing_membership = result.fetchone()

    if not existing_membership:
        # Add superadmin as owner using raw SQL
        membership_id = uuid.uuid4()
        await session.execute(
            text("""
                INSERT INTO organization_members (id, user_id, organization_id, role)
                VALUES (:id, :user_id, :org_id, 'owner')
            """),
            {
                "id": membership_id,
                "user_id": superadmin.id,
                "org_id": org_id,
            }
        )
        print("Added superadmin as owner of organization: Dalgo Default")

    await session.commit()
    print("Seed completed successfully!")
    print("IMPORTANT: Change the password after first login!")


async def main() -> None:
    """Run seed operations."""
    async with AsyncSessionLocal() as session:
        await create_superadmin_with_org(session)


if __name__ == "__main__":
    asyncio.run(main())
