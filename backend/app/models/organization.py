import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user_links = relationship("UserOrganization", back_populates="organization", lazy="selectin")


class UserOrganization(Base):
    __tablename__ = "user_organizations"
    __table_args__ = (UniqueConstraint("user_id", "org_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    role: Mapped[str] = mapped_column(String(50), default="owner")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user = relationship("User", back_populates="org_links", lazy="selectin")
    organization = relationship("Organization", back_populates="user_links", lazy="selectin")
