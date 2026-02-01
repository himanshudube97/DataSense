"""
Seed script to create initial superadmin user.

Run with: python -m app.core.seed
"""
import asyncio

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_superadmin(session: AsyncSession) -> None:
    """Create the initial superadmin user if it doesn't exist."""

    # Check if superadmin already exists
    result = await session.execute(
        select(User).where(User.email == settings.SUPERADMIN_EMAIL)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        print(f"Superadmin user already exists: {settings.SUPERADMIN_EMAIL}")
        return

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
    await session.commit()

    print(f"Created superadmin user: {settings.SUPERADMIN_EMAIL}")
    print("IMPORTANT: Change the password after first login!")


async def main() -> None:
    """Run seed operations."""
    async with AsyncSessionLocal() as session:
        await create_superadmin(session)


if __name__ == "__main__":
    asyncio.run(main())
