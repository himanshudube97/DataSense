"""Warehouse connection API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_org_admin
from app.core.database import get_db
from app.models import User
from app.schemas.warehouse import (
    WarehouseConnectionCreate,
    WarehouseConnectionResponse,
    WarehouseConnectionStatus,
    WarehouseTableInfo,
    WarehouseTestResult,
)
from app.services.warehouse import WarehouseService

router = APIRouter(prefix="/organizations/{org_id}/warehouse", tags=["Warehouse"])


@router.get("", response_model=WarehouseConnectionStatus)
async def get_warehouse_status(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WarehouseConnectionStatus:
    """
    Get warehouse connection status for an organization.

    Returns whether a warehouse is connected and basic info.
    """
    service = WarehouseService(db)
    return await service.get_status(org_id)


@router.post("", response_model=WarehouseConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse_connection(
    org_id: uuid.UUID,
    data: WarehouseConnectionCreate,
    current_user: Annotated[User, Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WarehouseConnectionResponse:
    """
    Create a new warehouse connection.

    Requires admin role in the organization.
    """
    service = WarehouseService(db)

    try:
        connection = await service.create_connection(org_id, data)
        return WarehouseConnectionResponse.model_validate(connection)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("", response_model=WarehouseConnectionResponse)
async def update_warehouse_connection(
    org_id: uuid.UUID,
    data: WarehouseConnectionCreate,
    current_user: Annotated[User, Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WarehouseConnectionResponse:
    """
    Update existing warehouse connection.

    Requires admin role in the organization.
    """
    service = WarehouseService(db)

    try:
        connection = await service.update_connection(org_id, data)
        return WarehouseConnectionResponse.model_validate(connection)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/test", response_model=WarehouseTestResult)
async def test_warehouse_connection(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WarehouseTestResult:
    """
    Test the warehouse connection.

    Attempts to connect and list tables.
    """
    service = WarehouseService(db)
    return await service.test_connection(org_id)


@router.get("/tables", response_model=list[WarehouseTableInfo])
async def list_warehouse_tables(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WarehouseTableInfo]:
    """
    List all tables in the warehouse.

    Returns table names, schemas, and column information.
    """
    service = WarehouseService(db)
    return await service.list_tables(org_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse_connection(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete warehouse connection.

    Requires admin role in the organization.
    """
    service = WarehouseService(db)

    try:
        await service.delete_connection(org_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
