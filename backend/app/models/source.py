import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SourceType(str, enum.Enum):
    """Type of data source."""
    GOOGLE_SHEETS = "google_sheets"
    CSV = "csv"              # Future
    POSTGRES = "postgres"    # Future
    API = "api"              # Future


class SyncStatus(str, enum.Enum):
    """Status of a sync run."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Source(BaseModel):
    """
    Data source configuration.

    Represents a connection to an external data source (e.g., Google Sheet).
    """

    __tablename__ = "sources"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType),
        default=SourceType.GOOGLE_SHEETS,
        nullable=False,
    )
    # Source-specific configuration (e.g., spreadsheet_id, sheet_name)
    config: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    # Table name in the warehouse (auto-generated or user-defined)
    warehouse_table_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="sources",
    )
    created_by: Mapped["User | None"] = relationship("User")
    schemas: Mapped[list["SourceSchema"]] = relationship(
        "SourceSchema",
        back_populates="source",
        lazy="selectin",
    )
    sync_runs: Mapped[list["SyncRun"]] = relationship(
        "SyncRun",
        back_populates="source",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Source {self.name} ({self.source_type})>"


class SourceSchema(BaseModel):
    """
    Discovered/inferred schema for a source.

    Stores column information for each source.
    """

    __tablename__ = "source_schemas"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    column_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    column_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    is_nullable: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )
    # Additional metadata (e.g., original type from source, sample values)
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="schemas",
    )

    def __repr__(self) -> str:
        return f"<SourceSchema {self.column_name}: {self.column_type}>"


class SyncRun(BaseModel):
    """
    History of sync operations for a source.

    Tracks when data was synced from source to warehouse.
    """

    __tablename__ = "sync_runs"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus),
        default=SyncStatus.PENDING,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rows_synced: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Additional run details
    details: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    triggered_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="sync_runs",
    )
    triggered_by: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<SyncRun {self.source_id} {self.status}>"
