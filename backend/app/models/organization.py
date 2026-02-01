import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class OrgType(str, enum.Enum):
    """Organization type."""
    team = "team"           # Full organization (NGO)
    personal = "personal"   # Personal workspace (future)


class OrgMemberRole(str, enum.Enum):
    """Member role within an organization."""
    owner = "owner"     # Full access, can delete org
    admin = "admin"     # Can manage sources, transforms, invite members
    member = "member"   # Can create/edit transforms
    viewer = "viewer"   # Read-only access


class Organization(BaseModel):
    """
    Organization model - the root entity for multi-tenancy.

    Each NGO is one organization. All resources (sources, transforms, etc.)
    belong to an organization.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    org_type: Mapped[OrgType] = mapped_column(
        Enum(OrgType),
        default=OrgType.team,
        nullable=False,
    )
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        lazy="selectin",
    )
    sources: Mapped[list["Source"]] = relationship(
        "Source",
        back_populates="organization",
        lazy="selectin",
    )
    warehouse_connection: Mapped["WarehouseConnection | None"] = relationship(
        "WarehouseConnection",
        back_populates="organization",
        uselist=False,
        lazy="selectin",
    )
    transformations: Mapped[list["Transformation"]] = relationship(
        "Transformation",
        back_populates="organization",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"


class OrganizationMember(BaseModel):
    """
    Association table for users and organizations with role.

    A user can be a member of multiple organizations with different roles.
    """

    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[OrgMemberRole] = mapped_column(
        Enum(OrgMemberRole),
        default=OrgMemberRole.member,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="organization_memberships",
    )
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="members",
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember user={self.user_id} org={self.organization_id} role={self.role}>"
