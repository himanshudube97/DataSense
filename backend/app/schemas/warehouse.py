"""Warehouse connection schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class WarehouseConnectionCreate(BaseModel):
    """Schema for creating a warehouse connection."""

    supabase_url: HttpUrl = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., min_length=20, description="Supabase service role key")
    schema_name: str = Field(default="public", description="Database schema to use")


class WarehouseConnectionResponse(BaseModel):
    """Warehouse connection response schema."""

    id: uuid.UUID
    organization_id: uuid.UUID
    supabase_url: str
    schema_name: str
    is_connected: bool
    last_connected_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WarehouseConnectionStatus(BaseModel):
    """Warehouse connection status."""

    connected: bool
    has_warehouse: bool
    supabase_url: str | None = None
    schema_name: str | None = None
    table_count: int = 0
    last_connected_at: datetime | None = None


class WarehouseTestResult(BaseModel):
    """Result of testing warehouse connection."""

    success: bool
    message: str
    tables_found: int = 0


class WarehouseTableInfo(BaseModel):
    """Information about a warehouse table."""

    name: str
    schema_name: str
    row_count: int | None = None
    columns: list["ColumnInfo"] = []


class ColumnInfo(BaseModel):
    """Column information."""

    name: str
    data_type: str
    is_nullable: bool = True


WarehouseTableInfo.model_rebuild()
