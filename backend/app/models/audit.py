import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """
    Audit log for tracking user actions.

    Records all significant actions for compliance and debugging.
    No soft delete - audit logs are permanent.
    """

    __tablename__ = "audit_logs"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Action performed (e.g., "source.create", "transformation.execute")
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    # Resource type (e.g., "source", "transformation", "user")
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # Resource ID
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    # Additional details about the action
    details: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    # IP address of the request
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    # User agent string
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization | None"] = relationship("Organization")
    user: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by user={self.user_id}>"
