"""Source management schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.source import SourceType, SyncStatus


class SourceSchemaInfo(BaseModel):
    """Column schema information."""

    column_name: str
    column_type: str
    column_order: int
    is_nullable: bool = True


class SourceBase(BaseModel):
    """Base source schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    warehouse_table_name: str | None = Field(
        None,
        pattern=r"^[a-z_][a-z0-9_]*$",
        description="Table name in warehouse (lowercase, underscores only)",
    )


class SourceCreateCSV(SourceBase):
    """Schema for creating a CSV source."""

    source_type: SourceType = SourceType.CSV


class SourceCreateGoogleSheets(SourceBase):
    """Schema for creating a Google Sheets source."""

    source_type: SourceType = SourceType.GOOGLE_SHEETS
    spreadsheet_id: str = Field(..., description="Google Spreadsheet ID")
    sheet_name: str = Field(default="Sheet1", description="Sheet/tab name")


class SourceResponse(SourceBase):
    """Source response schema."""

    id: uuid.UUID
    organization_id: uuid.UUID
    source_type: SourceType
    config: dict = {}
    last_synced_at: datetime | None = None
    created_at: datetime
    schema_columns: list[SourceSchemaInfo] = []

    model_config = {"from_attributes": True}


class SourceListResponse(BaseModel):
    """Source list response."""

    id: uuid.UUID
    name: str
    source_type: SourceType
    warehouse_table_name: str | None
    last_synced_at: datetime | None
    column_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncRunResponse(BaseModel):
    """Sync run response schema."""

    id: uuid.UUID
    source_id: uuid.UUID
    status: SyncStatus
    started_at: datetime | None
    completed_at: datetime | None
    rows_synced: int | None
    error_message: str | None

    model_config = {"from_attributes": True}


class SyncTriggerResponse(BaseModel):
    """Response when triggering a sync."""

    sync_run_id: uuid.UUID
    status: SyncStatus
    message: str


class CSVUploadResponse(BaseModel):
    """Response after CSV upload and parse."""

    source_id: uuid.UUID
    name: str
    row_count: int
    columns: list[SourceSchemaInfo]
    preview_data: list[dict] = []


class SourcePreviewData(BaseModel):
    """Preview of source data."""

    columns: list[SourceSchemaInfo]
    rows: list[dict]
    total_rows: int
