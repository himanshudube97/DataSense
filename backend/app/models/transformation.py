import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TransformationStatus(str, enum.Enum):
    """Status of a transformation run."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Transformation(BaseModel):
    """
    Transformation definition.

    Stores the transformation configuration (recipe) that generates SQL.
    """

    __tablename__ = "transformations"

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
    # The transformation recipe (JSON) - canvas state
    recipe: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    # Output table name in warehouse
    output_table_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    # Current version number
    current_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
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
        back_populates="transformations",
    )
    created_by: Mapped["User | None"] = relationship("User")
    versions: Mapped[list["TransformationVersion"]] = relationship(
        "TransformationVersion",
        back_populates="transformation",
        lazy="selectin",
    )
    runs: Mapped[list["TransformationRun"]] = relationship(
        "TransformationRun",
        back_populates="transformation",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Transformation {self.name}>"


class TransformationVersion(BaseModel):
    """
    Version history for a transformation.

    Each time a transformation is saved, a new version is created.
    """

    __tablename__ = "transformation_versions"

    transformation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transformations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    # Snapshot of the recipe at this version
    recipe: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    # Generated SQL for this version
    generated_sql: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Change description
    change_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    transformation: Mapped["Transformation"] = relationship(
        "Transformation",
        back_populates="versions",
    )
    created_by: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<TransformationVersion {self.transformation_id} v{self.version_number}>"


class TransformationRun(BaseModel):
    """
    Execution history for a transformation.

    Tracks each time a transformation is executed.
    """

    __tablename__ = "transformation_runs"

    transformation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transformations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status: Mapped[TransformationStatus] = mapped_column(
        Enum(TransformationStatus),
        default=TransformationStatus.PENDING,
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
    # Generated SQL that was executed
    executed_sql: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    rows_affected: Mapped[int | None] = mapped_column(
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
    transformation: Mapped["Transformation"] = relationship(
        "Transformation",
        back_populates="runs",
    )
    triggered_by: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<TransformationRun {self.transformation_id} {self.status}>"
