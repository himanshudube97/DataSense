"""Warehouse service for managing Supabase connections."""

import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value, encrypt_value
from app.models import Organization, WarehouseConnection
from app.schemas.warehouse import (
    ColumnInfo,
    WarehouseConnectionCreate,
    WarehouseConnectionStatus,
    WarehouseTableInfo,
    WarehouseTestResult,
)


class WarehouseService:
    """Service for managing warehouse connections."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_connection(self, org_id: uuid.UUID) -> WarehouseConnection | None:
        """Get warehouse connection for an organization."""
        result = await self.db.execute(
            select(WarehouseConnection).where(
                WarehouseConnection.organization_id == org_id,
                WarehouseConnection.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_status(self, org_id: uuid.UUID) -> WarehouseConnectionStatus:
        """Get warehouse connection status for an organization."""
        connection = await self.get_connection(org_id)

        if connection is None:
            return WarehouseConnectionStatus(
                connected=False,
                has_warehouse=False,
            )

        # Count tables
        table_count = len([t for t in connection.tables if t.deleted_at is None])

        return WarehouseConnectionStatus(
            connected=connection.is_connected,
            has_warehouse=True,
            supabase_url=connection.supabase_url,
            schema_name=connection.schema_name,
            table_count=table_count,
            last_connected_at=connection.last_connected_at,
        )

    async def create_connection(
        self,
        org_id: uuid.UUID,
        data: WarehouseConnectionCreate,
    ) -> WarehouseConnection:
        """Create a new warehouse connection."""
        # Check organization exists
        result = await self.db.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValueError("Organization not found")

        # Check if connection already exists
        existing = await self.get_connection(org_id)
        if existing:
            raise ValueError("Warehouse connection already exists for this organization")

        # Encrypt the API key
        encrypted_key = encrypt_value(data.supabase_key)

        connection = WarehouseConnection(
            organization_id=org_id,
            supabase_url=str(data.supabase_url),
            supabase_key_encrypted=encrypted_key,
            schema_name=data.schema_name,
            is_connected=False,
        )

        self.db.add(connection)
        await self.db.commit()
        await self.db.refresh(connection)

        return connection

    async def update_connection(
        self,
        org_id: uuid.UUID,
        data: WarehouseConnectionCreate,
    ) -> WarehouseConnection:
        """Update an existing warehouse connection."""
        connection = await self.get_connection(org_id)
        if connection is None:
            raise ValueError("No warehouse connection found")

        # Encrypt the new API key
        encrypted_key = encrypt_value(data.supabase_key)

        connection.supabase_url = str(data.supabase_url)
        connection.supabase_key_encrypted = encrypted_key
        connection.schema_name = data.schema_name
        connection.is_connected = False  # Reset connection status

        await self.db.commit()
        await self.db.refresh(connection)

        return connection

    async def test_connection(self, org_id: uuid.UUID) -> WarehouseTestResult:
        """Test the warehouse connection."""
        connection = await self.get_connection(org_id)
        if connection is None:
            return WarehouseTestResult(
                success=False,
                message="No warehouse connection configured",
            )

        try:
            # Decrypt the API key
            api_key = decrypt_value(connection.supabase_key_encrypted)

            # Test connection by listing tables
            tables = await self._fetch_tables(
                connection.supabase_url,
                api_key,
                connection.schema_name,
            )

            # Update connection status
            connection.is_connected = True
            connection.last_connected_at = datetime.now(timezone.utc)
            await self.db.commit()

            return WarehouseTestResult(
                success=True,
                message="Connection successful",
                tables_found=len(tables),
            )

        except Exception as e:
            connection.is_connected = False
            await self.db.commit()

            return WarehouseTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
            )

    async def list_tables(self, org_id: uuid.UUID) -> list[WarehouseTableInfo]:
        """List all tables in the warehouse."""
        connection = await self.get_connection(org_id)
        if connection is None:
            return []

        try:
            api_key = decrypt_value(connection.supabase_key_encrypted)
            tables = await self._fetch_tables(
                connection.supabase_url,
                api_key,
                connection.schema_name,
            )
            return tables
        except Exception:
            return []

    async def _fetch_tables(
        self,
        supabase_url: str,
        api_key: str,
        schema_name: str,
    ) -> list[WarehouseTableInfo]:
        """Fetch tables from Supabase using the REST API."""
        # Use Supabase REST API to query information_schema
        # We use PostgREST's RPC endpoint for raw SQL

        # First, let's try to get table info using the OpenAPI schema endpoint
        async with httpx.AsyncClient() as client:
            # Get the OpenAPI spec which lists all tables
            response = await client.get(
                f"{supabase_url}/rest/v1/",
                headers={
                    "apikey": api_key,
                    "Authorization": f"Bearer {api_key}",
                },
                timeout=10.0,
            )

            if response.status_code != 200:
                raise Exception(f"Failed to connect: HTTP {response.status_code}")

            # Parse the OpenAPI spec to get table names
            spec = response.json()
            tables = []

            if "definitions" in spec:
                for table_name, table_def in spec["definitions"].items():
                    if table_name.startswith("_"):
                        continue  # Skip internal tables

                    columns = []
                    if "properties" in table_def:
                        for col_name, col_def in table_def["properties"].items():
                            columns.append(
                                ColumnInfo(
                                    name=col_name,
                                    data_type=col_def.get("type", "unknown"),
                                    is_nullable=True,  # Default to true
                                )
                            )

                    tables.append(
                        WarehouseTableInfo(
                            name=table_name,
                            schema_name=schema_name,
                            columns=columns,
                        )
                    )

            return tables

    async def delete_connection(self, org_id: uuid.UUID) -> None:
        """Soft delete warehouse connection."""
        connection = await self.get_connection(org_id)
        if connection is None:
            raise ValueError("No warehouse connection found")

        connection.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
