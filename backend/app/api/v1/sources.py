"""Source management API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.source import (
    CSVUploadResponse,
    SourceCreateCSV,
    SourceListResponse,
    SourcePreviewData,
    SourceResponse,
    SourceSchemaInfo,
    SyncRunResponse,
    SyncTriggerResponse,
)
from app.services.source import SourceService

router = APIRouter(prefix="/organizations/{org_id}/sources", tags=["Sources"])


@router.get("", response_model=list[SourceListResponse])
async def list_sources(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SourceListResponse]:
    """
    List all sources for an organization.
    """
    service = SourceService(db)
    return await service.list_sources(org_id)


@router.post("/csv", response_model=CSVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_csv_source(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="CSV file to upload"),
    name: str = Form(..., description="Name for the source"),
    description: str | None = Form(None, description="Optional description"),
    warehouse_table_name: str | None = Form(None, description="Table name in warehouse"),
) -> CSVUploadResponse:
    """
    Upload a CSV file as a new source.

    Parses the CSV, infers schema, and stores metadata.
    Data can then be synced to the warehouse.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        )

    # Read file content
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 50MB",
        )

    # Create source data
    source_data = SourceCreateCSV(
        name=name,
        description=description,
        warehouse_table_name=warehouse_table_name,
    )

    service = SourceService(db)

    try:
        return await service.create_csv_source(
            org_id=org_id,
            user_id=current_user.id,
            data=source_data,
            csv_content=content,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    org_id: uuid.UUID,
    source_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SourceResponse:
    """
    Get source details.
    """
    service = SourceService(db)
    source = await service.get_source(org_id, source_id)

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    # Get schema columns
    schema_columns = [
        SourceSchemaInfo(
            column_name=s.column_name,
            column_type=s.column_type,
            column_order=s.column_order,
            is_nullable=s.is_nullable,
        )
        for s in sorted(source.schemas, key=lambda x: x.column_order)
        if s.deleted_at is None
    ]

    return SourceResponse(
        id=source.id,
        organization_id=source.organization_id,
        name=source.name,
        description=source.description,
        source_type=source.source_type,
        warehouse_table_name=source.warehouse_table_name,
        config={k: v for k, v in source.config.items() if k != "csv_data"},  # Exclude raw data
        last_synced_at=source.last_synced_at,
        created_at=source.created_at,
        schema_columns=schema_columns,
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    org_id: uuid.UUID,
    source_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a source.
    """
    service = SourceService(db)

    try:
        await service.delete_source(org_id, source_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{source_id}/preview", response_model=SourcePreviewData)
async def preview_source_data(
    org_id: uuid.UUID,
    source_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
) -> SourcePreviewData:
    """
    Preview source data.

    Returns sample rows and column information.
    """
    service = SourceService(db)

    try:
        return await service.preview_source(org_id, source_id, limit=limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{source_id}/sync", response_model=SyncTriggerResponse)
async def sync_source(
    org_id: uuid.UUID,
    source_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncTriggerResponse:
    """
    Sync source data to the warehouse.

    Pushes data from the source to the connected Supabase warehouse.
    """
    service = SourceService(db)

    try:
        return await service.sync_source(org_id, source_id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{source_id}/sync-history", response_model=list[SyncRunResponse])
async def get_sync_history(
    org_id: uuid.UUID,
    source_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 10,
) -> list[SyncRunResponse]:
    """
    Get sync history for a source.
    """
    service = SourceService(db)

    try:
        return await service.get_sync_history(org_id, source_id, limit=limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
