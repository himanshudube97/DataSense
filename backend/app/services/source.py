"""Source management service."""

import csv
import io
import re
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.models import Organization, Source, SourceSchema, SourceType, SyncRun, SyncStatus, WarehouseConnection
from app.schemas.source import (
    CSVUploadResponse,
    SourceCreateCSV,
    SourceListResponse,
    SourcePreviewData,
    SourceSchemaInfo,
    SyncRunResponse,
    SyncTriggerResponse,
)


class SourceService:
    """Service for managing data sources."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sources(self, org_id: uuid.UUID) -> list[SourceListResponse]:
        """List all sources for an organization."""
        result = await self.db.execute(
            select(Source)
            .where(
                Source.organization_id == org_id,
                Source.deleted_at.is_(None),
            )
            .order_by(Source.created_at.desc())
        )
        sources = result.scalars().all()

        return [
            SourceListResponse(
                id=s.id,
                name=s.name,
                source_type=s.source_type,
                warehouse_table_name=s.warehouse_table_name,
                last_synced_at=s.last_synced_at,
                column_count=len([c for c in s.schemas if c.deleted_at is None]),
                created_at=s.created_at,
            )
            for s in sources
        ]

    async def get_source(self, org_id: uuid.UUID, source_id: uuid.UUID) -> Source | None:
        """Get a source by ID."""
        result = await self.db.execute(
            select(Source).where(
                Source.id == source_id,
                Source.organization_id == org_id,
                Source.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_csv_source(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SourceCreateCSV,
        csv_content: bytes,
    ) -> CSVUploadResponse:
        """Create a new CSV source from uploaded file."""
        # Verify organization exists
        result = await self.db.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValueError("Organization not found")

        # Parse CSV content
        content_str = csv_content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content_str))

        # Read all rows
        rows = list(reader)
        if not rows:
            raise ValueError("CSV file is empty")

        # Infer schema from data
        columns = self._infer_schema(rows)

        # Generate table name if not provided
        table_name = data.warehouse_table_name
        if not table_name:
            table_name = self._sanitize_table_name(data.name)

        # Create source record
        source = Source(
            organization_id=org_id,
            name=data.name,
            description=data.description,
            source_type=SourceType.CSV,
            config={
                "original_filename": data.name,
                "row_count": len(rows),
            },
            warehouse_table_name=table_name,
            created_by_id=user_id,
        )
        self.db.add(source)
        await self.db.flush()

        # Create schema records
        for col in columns:
            schema = SourceSchema(
                source_id=source.id,
                column_name=col.column_name,
                column_type=col.column_type,
                column_order=col.column_order,
                is_nullable=col.is_nullable,
                metadata_={},
            )
            self.db.add(schema)

        # Store CSV data temporarily in config for later sync
        source.config["csv_data"] = rows

        await self.db.commit()
        await self.db.refresh(source)

        return CSVUploadResponse(
            source_id=source.id,
            name=source.name,
            row_count=len(rows),
            columns=columns,
            preview_data=rows[:10],  # First 10 rows for preview
        )

    async def delete_source(self, org_id: uuid.UUID, source_id: uuid.UUID) -> None:
        """Soft delete a source."""
        source = await self.get_source(org_id, source_id)
        if source is None:
            raise ValueError("Source not found")

        source.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def preview_source(
        self,
        org_id: uuid.UUID,
        source_id: uuid.UUID,
        limit: int = 100,
    ) -> SourcePreviewData:
        """Preview source data."""
        source = await self.get_source(org_id, source_id)
        if source is None:
            raise ValueError("Source not found")

        # Get columns from schema
        columns = [
            SourceSchemaInfo(
                column_name=s.column_name,
                column_type=s.column_type,
                column_order=s.column_order,
                is_nullable=s.is_nullable,
            )
            for s in sorted(source.schemas, key=lambda x: x.column_order)
            if s.deleted_at is None
        ]

        # For CSV, data is stored in config
        if source.source_type == SourceType.CSV:
            rows = source.config.get("csv_data", [])
            return SourcePreviewData(
                columns=columns,
                rows=rows[:limit],
                total_rows=len(rows),
            )

        # For synced sources, fetch from warehouse
        # (implement later when warehouse sync is ready)
        return SourcePreviewData(
            columns=columns,
            rows=[],
            total_rows=0,
        )

    async def sync_source(
        self,
        org_id: uuid.UUID,
        source_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SyncTriggerResponse:
        """Sync source data to warehouse."""
        source = await self.get_source(org_id, source_id)
        if source is None:
            raise ValueError("Source not found")

        # Get warehouse connection
        result = await self.db.execute(
            select(WarehouseConnection).where(
                WarehouseConnection.organization_id == org_id,
                WarehouseConnection.deleted_at.is_(None),
            )
        )
        warehouse = result.scalar_one_or_none()

        if warehouse is None:
            raise ValueError("No warehouse connection configured")

        # Create sync run record
        sync_run = SyncRun(
            source_id=source_id,
            status=SyncStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            triggered_by_id=user_id,
        )
        self.db.add(sync_run)
        await self.db.flush()

        try:
            # Get data based on source type
            if source.source_type == SourceType.CSV:
                rows = source.config.get("csv_data", [])
            else:
                raise ValueError(f"Source type {source.source_type} sync not implemented")

            if not rows:
                raise ValueError("No data to sync")

            # Sync to Supabase warehouse
            rows_synced = await self._sync_to_supabase(
                warehouse,
                source.warehouse_table_name,
                rows,
                [s for s in source.schemas if s.deleted_at is None],
            )

            # Update sync run
            sync_run.status = SyncStatus.SUCCESS
            sync_run.completed_at = datetime.now(timezone.utc)
            sync_run.rows_synced = rows_synced

            # Update source
            source.last_synced_at = datetime.now(timezone.utc)

            await self.db.commit()

            return SyncTriggerResponse(
                sync_run_id=sync_run.id,
                status=SyncStatus.SUCCESS,
                message=f"Successfully synced {rows_synced} rows",
            )

        except Exception as e:
            sync_run.status = SyncStatus.FAILED
            sync_run.completed_at = datetime.now(timezone.utc)
            sync_run.error_message = str(e)
            await self.db.commit()

            return SyncTriggerResponse(
                sync_run_id=sync_run.id,
                status=SyncStatus.FAILED,
                message=f"Sync failed: {str(e)}",
            )

    async def get_sync_history(
        self,
        org_id: uuid.UUID,
        source_id: uuid.UUID,
        limit: int = 10,
    ) -> list[SyncRunResponse]:
        """Get sync history for a source."""
        source = await self.get_source(org_id, source_id)
        if source is None:
            raise ValueError("Source not found")

        result = await self.db.execute(
            select(SyncRun)
            .where(SyncRun.source_id == source_id)
            .order_by(SyncRun.created_at.desc())
            .limit(limit)
        )
        runs = result.scalars().all()

        return [SyncRunResponse.model_validate(r) for r in runs]

    async def _sync_to_supabase(
        self,
        warehouse: WarehouseConnection,
        table_name: str,
        rows: list[dict],
        schema: list[SourceSchema],
    ) -> int:
        """Sync data to Supabase using REST API."""
        api_key = decrypt_value(warehouse.supabase_key_encrypted)

        async with httpx.AsyncClient() as client:
            # First, try to create the table if it doesn't exist
            # We'll use upsert which handles this

            # Delete existing data (full refresh)
            await client.delete(
                f"{warehouse.supabase_url}/rest/v1/{table_name}",
                headers={
                    "apikey": api_key,
                    "Authorization": f"Bearer {api_key}",
                    "Prefer": "return=minimal",
                },
                params={"id": "neq."},  # Match all rows
                timeout=30.0,
            )

            # Insert new data in batches
            batch_size = 1000
            total_inserted = 0

            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]

                response = await client.post(
                    f"{warehouse.supabase_url}/rest/v1/{table_name}",
                    headers={
                        "apikey": api_key,
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    },
                    json=batch,
                    timeout=60.0,
                )

                if response.status_code not in [200, 201]:
                    raise Exception(f"Failed to insert data: {response.text}")

                total_inserted += len(batch)

            return total_inserted

    def _infer_schema(self, rows: list[dict]) -> list[SourceSchemaInfo]:
        """Infer schema from CSV data."""
        if not rows:
            return []

        columns = list(rows[0].keys())
        schema = []

        for i, col in enumerate(columns):
            values = [row.get(col) for row in rows[:100]]  # Sample first 100 rows
            col_type = self._infer_column_type(values)

            schema.append(
                SourceSchemaInfo(
                    column_name=col,
                    column_type=col_type,
                    column_order=i,
                    is_nullable=any(v is None or v == "" for v in values),
                )
            )

        return schema

    def _infer_column_type(self, values: list) -> str:
        """Infer column type from sample values."""
        non_null = [v for v in values if v is not None and v != ""]

        if not non_null:
            return "TEXT"

        # Try integer
        if all(self._is_integer(v) for v in non_null):
            return "INTEGER"

        # Try float
        if all(self._is_float(v) for v in non_null):
            return "DOUBLE"

        # Try boolean
        if all(self._is_boolean(v) for v in non_null):
            return "BOOLEAN"

        # Try date (simple patterns)
        if all(self._is_date(v) for v in non_null):
            return "DATE"

        return "TEXT"

    def _is_integer(self, value: str) -> bool:
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False

    def _is_float(self, value: str) -> bool:
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _is_boolean(self, value: str) -> bool:
        return str(value).lower() in ("true", "false", "yes", "no", "1", "0")

    def _is_date(self, value: str) -> bool:
        # Simple date patterns
        patterns = [
            r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
            r"^\d{2}/\d{2}/\d{4}$",  # MM/DD/YYYY
            r"^\d{2}-\d{2}-\d{4}$",  # DD-MM-YYYY
        ]
        return any(re.match(p, str(value)) for p in patterns)

    def _sanitize_table_name(self, name: str) -> str:
        """Convert name to valid table name."""
        # Convert to lowercase, replace spaces/special chars with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9]", "_", name.lower())
        # Remove leading numbers
        sanitized = re.sub(r"^[0-9]+", "", sanitized)
        # Remove consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")

        return sanitized or "untitled_source"
