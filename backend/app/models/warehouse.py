import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class WarehouseConnection(BaseModel):
    """
    Supabase warehouse connection configuration per organization.

    Each organization has one warehouse connection to their own Supabase project.
    Credentials are encrypted before storage.
    """

    __tablename__ = "warehouse_connections"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # Supabase project URL (e.g., https://abc123.supabase.co)
    supabase_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    # Encrypted Supabase service role key
    supabase_key_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    # Database schema to use (default: public)
    schema_name: Mapped[str] = mapped_column(
        String(100),
        default="public",
        nullable=False,
    )
    # Connection status
    is_connected: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Additional configuration
    config: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="warehouse_connection",
    )
    tables: Mapped[list["WarehouseTable"]] = relationship(
        "WarehouseTable",
        back_populates="warehouse_connection",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<WarehouseConnection org={self.organization_id}>"


class WarehouseTable(BaseModel):
    """
    Registry of tables in the user's warehouse.

    Tracks tables created from sources or transformations.
    """

    __tablename__ = "warehouse_tables"

    warehouse_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    # Reference to source or transformation that created this table
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    transformation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transformations.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Statistics
    row_count: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    last_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Schema information
    schema_info: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    warehouse_connection: Mapped["WarehouseConnection"] = relationship(
        "WarehouseConnection",
        back_populates="tables",
    )
    source: Mapped["Source | None"] = relationship("Source")
    transformation: Mapped["Transformation | None"] = relationship("Transformation")

    def __repr__(self) -> str:
        return f"<WarehouseTable {self.table_name}>"
