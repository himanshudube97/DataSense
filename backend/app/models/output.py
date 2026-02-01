import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ScheduleFrequency(str, enum.Enum):
    """Frequency for scheduled operations."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Output(BaseModel):
    """
    Output table definition.

    Represents a materialized output from a transformation.
    Can be scheduled for automatic refresh.
    """

    __tablename__ = "outputs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transformation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transformations.id", ondelete="CASCADE"),
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
    # Output destination configuration
    destination_config: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    transformation: Mapped["Transformation"] = relationship("Transformation")
    created_by: Mapped["User | None"] = relationship("User")
    schedule: Mapped["Schedule | None"] = relationship(
        "Schedule",
        back_populates="output",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Output {self.name}>"


class Schedule(BaseModel):
    """
    Schedule for automatic sync/transform operations.

    Can be attached to a source (for sync) or output (for transform refresh).
    """

    __tablename__ = "schedules"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Can be attached to source or output
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=True,
    )
    output_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("outputs.id", ondelete="CASCADE"),
        nullable=True,
    )
    frequency: Mapped[ScheduleFrequency] = mapped_column(
        Enum(ScheduleFrequency),
        nullable=False,
    )
    # Time of day to run (for daily/weekly/monthly)
    run_at_time: Mapped[datetime | None] = mapped_column(
        Time,
        nullable=True,
    )
    # Day of week (0-6 for weekly) or day of month (1-31 for monthly)
    run_at_day: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    source: Mapped["Source | None"] = relationship("Source")
    output: Mapped["Output | None"] = relationship(
        "Output",
        back_populates="schedule",
    )
    created_by: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Schedule {self.frequency} active={self.is_active}>"
