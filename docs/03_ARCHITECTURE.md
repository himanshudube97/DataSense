# Dalgo Lite: System Architecture

**Version:** 1.0
**Date:** February 2026
**Status:** Design

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Ingestion System](#ingestion-system)
6. [Transformation Engine](#transformation-engine)
7. [API Design](#api-design)
8. [Security Architecture](#security-architecture)
9. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                              DALGO LITE                                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         PRESENTATION LAYER                           │   │
│  │                                                                      │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │   │
│  │   │   Ingestion  │  │ Transformer  │  │     Preview / Output     │ │   │
│  │   │     View     │  │    Canvas    │  │         Grid             │ │   │
│  │   └──────────────┘  └──────────────┘  └──────────────────────────┘ │   │
│  │                         Next.js 15 + React 19                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      │ REST API                             │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          APPLICATION LAYER                           │   │
│  │                                                                      │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │   │
│  │   │   Ingestion  │  │  Transform   │  │      Warehouse           │ │   │
│  │   │   Service    │  │   Service    │  │      Service             │ │   │
│  │   └──────────────┘  └──────────────┘  └──────────────────────────┘ │   │
│  │                          FastAPI + Python                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                          │                    │                             │
│                          ▼                    ▼                             │
│  ┌─────────────────────────────┐  ┌────────────────────────────────────┐  │
│  │        DATA LAYER           │  │         STORAGE LAYER               │  │
│  │                             │  │                                     │  │
│  │  ┌───────────────────────┐  │  │  ┌─────────────────────────────┐   │  │
│  │  │    Google Sheets      │  │  │  │        Supabase             │   │  │
│  │  │    (User's Data)      │  │  │  │   (Metadata + Auth)         │   │  │
│  │  └───────────────────────┘  │  │  └─────────────────────────────┘   │  │
│  │                             │  │                                     │  │
│  │  ┌───────────────────────┐  │  │  ┌─────────────────────────────┐   │  │
│  │  │      MotherDuck       │  │  │  │  Transformation Recipes     │   │  │
│  │  │  (User's Warehouse)   │  │  │  │       (JSON in PG)          │   │  │
│  │  └───────────────────────┘  │  │  └─────────────────────────────┘   │  │
│  └─────────────────────────────┘  └────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data Storage | User's MotherDuck | Data ownership, compliance, cost |
| Metadata Storage | Supabase PostgreSQL | Managed, RLS, free tier |
| Auth | Supabase Auth + Google | Single OAuth for Sheets access |
| Transformations | Click UI → SQL | Non-technical user accessibility |
| SQL Engine | DuckDB/MotherDuck | Modern, fast, free |

---

## Architecture Principles

### 1. User Data Ownership

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA OWNERSHIP MODEL                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  DALGO LITE STORES:              USER OWNS:                 │
│  ─────────────────               ──────────                 │
│  • User accounts                 • Google Sheets (source)   │
│  • Organization settings         • MotherDuck data (output) │
│  • Transformation recipes        • Query results            │
│  • Connection metadata           • Credentials (encrypted)  │
│                                                             │
│  WE NEVER STORE:                                            │
│  ───────────────                                            │
│  • Actual row-level data                                    │
│  • PII or sensitive information                             │
│  • Unencrypted credentials                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Stateless Transformations

Transformations are stored as **recipes** (JSON), not executed code:

```json
{
  "id": "trans_abc123",
  "name": "Active Beneficiaries by District",
  "steps": [
    {
      "type": "source",
      "config": { "table": "raw_beneficiaries" }
    },
    {
      "type": "filter",
      "config": {
        "column": "status",
        "operator": "equals",
        "value": "Active"
      }
    },
    {
      "type": "group",
      "config": {
        "groupBy": ["district"],
        "aggregates": [
          { "function": "count", "column": "id", "alias": "total" }
        ]
      }
    }
  ]
}
```

The recipe is converted to SQL at execution time:

```sql
SELECT district, COUNT(id) as total
FROM raw_beneficiaries
WHERE status = 'Active'
GROUP BY district
```

### 3. Progressive Enhancement

```
┌─────────────────────────────────────────────────────────────┐
│                 PROGRESSIVE CAPABILITY                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  BASIC (Browser Only):                                      │
│  • DuckDB-WASM for instant previews                         │
│  • Small datasets in memory                                 │
│  • No backend required for preview                          │
│                                                             │
│  STANDARD (With MotherDuck):                                │
│  • Persistent storage                                       │
│  • Larger datasets                                          │
│  • Scheduled syncs                                          │
│                                                             │
│  ADVANCED (Future):                                         │
│  • BigQuery support                                         │
│  • Custom SQL                                               │
│  • API access                                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Frontend Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  app/                                                                   │
│  ├── (auth)/                      # Auth routes (public)                │
│  │   ├── login/page.tsx                                                 │
│  │   └── callback/page.tsx                                              │
│  │                                                                      │
│  ├── (dashboard)/                 # Protected routes                    │
│  │   ├── layout.tsx               # Dashboard shell                     │
│  │   ├── sources/                 # Ingestion views                     │
│  │   │   ├── page.tsx             # Source list                         │
│  │   │   ├── [id]/page.tsx        # Source detail                       │
│  │   │   └── new/page.tsx         # Add source wizard                   │
│  │   │                                                                  │
│  │   ├── transform/               # Transformation views                │
│  │   │   ├── page.tsx             # Transform list                      │
│  │   │   ├── [id]/page.tsx        # Canvas editor                       │
│  │   │   └── new/page.tsx         # New transform                       │
│  │   │                                                                  │
│  │   └── settings/                # Organization settings               │
│  │       └── page.tsx                                                   │
│  │                                                                      │
│  components/                                                            │
│  ├── ui/                          # Base UI components (Radix)          │
│  ├── sources/                     # Source-specific components          │
│  │   ├── SheetPicker.tsx                                                │
│  │   ├── SourceCard.tsx                                                 │
│  │   └── SyncStatus.tsx                                                 │
│  ├── transform/                   # Transform components                │
│  │   ├── Canvas.tsx               # React Flow canvas                   │
│  │   ├── ActionPanel.tsx          # Click actions list                  │
│  │   ├── PreviewGrid.tsx          # AG Grid preview                     │
│  │   └── actions/                 # Individual action dialogs           │
│  │       ├── FilterAction.tsx                                           │
│  │       ├── JoinAction.tsx                                             │
│  │       ├── GroupAction.tsx                                            │
│  │       ├── CleanAction.tsx                                            │
│  │       └── ...                                                        │
│  │                                                                      │
│  hooks/                                                                 │
│  ├── api/                         # SWR hooks for API calls             │
│  │   ├── useSources.ts                                                  │
│  │   ├── useTransforms.ts                                               │
│  │   └── useWarehouse.ts                                                │
│  └── useGoogleSheets.ts           # Google Sheets API hook              │
│                                                                         │
│  stores/                          # Zustand stores                      │
│  ├── useCanvasStore.ts            # Canvas state                        │
│  └── usePreviewStore.ts           # Preview data state                  │
│                                                                         │
│  lib/                                                                   │
│  ├── supabase.ts                  # Supabase client                     │
│  ├── sql-generator.ts             # Client-side SQL preview             │
│  └── duckdb-wasm.ts               # Browser DuckDB instance             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Backend Services

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKEND ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        API LAYER                                 │   │
│  │                                                                  │   │
│  │  /api/v1/sources      → SourceRouter                            │   │
│  │  /api/v1/transforms   → TransformRouter                         │   │
│  │  /api/v1/warehouse    → WarehouseRouter                         │   │
│  │  /api/v1/users        → UserRouter                              │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      SERVICE LAYER                               │   │
│  │                                                                  │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │   │
│  │  │ IngestionService │  │ TransformService │  │ WarehouseService│ │   │
│  │  │                  │  │                  │  │               │ │   │
│  │  │ • list_sheets()  │  │ • parse_recipe() │  │ • connect()   │ │   │
│  │  │ • sync_sheet()   │  │ • generate_sql() │  │ • execute()   │ │   │
│  │  │ • get_schema()   │  │ • execute()      │  │ • get_tables()│ │   │
│  │  │ • schedule()     │  │ • validate()     │  │ • preview()   │ │   │
│  │  └──────────────────┘  └──────────────────┘  └───────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        CORE LAYER                                │   │
│  │                                                                  │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │   │
│  │  │ GoogleSheetsAPI  │  │  SQLGenerator    │  │MotherDuckClient│ │   │
│  │  │                  │  │                  │  │               │ │   │
│  │  │ Wrapper for      │  │ Recipe → SQL     │  │ Connection    │ │   │
│  │  │ Google API       │  │ conversion       │  │ management    │ │   │
│  │  └──────────────────┘  └──────────────────┘  └───────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          INGESTION FLOW                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. USER SELECTS SHEET                                                  │
│  ┌─────────────┐                                                        │
│  │ Google      │                                                        │
│  │ Picker UI   │ ──── User selects "Beneficiary_Data" ────┐            │
│  └─────────────┘                                          │            │
│                                                           ▼            │
│  2. FRONTEND SENDS REQUEST                               │            │
│  ┌─────────────┐                                          │            │
│  │ Next.js     │ ◀────────────────────────────────────────┘            │
│  │ POST /api/v1/sources                                   │            │
│  │ {                                                      │            │
│  │   sheet_id: "1abc...",                                 │            │
│  │   tab: "Sheet1",                                       │            │
│  │   table_name: "beneficiaries"                          │            │
│  │ }                                                      │            │
│  └──────┬──────┘                                                        │
│         │                                                               │
│         ▼                                                               │
│  3. BACKEND PROCESSES                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ FastAPI                                                          │   │
│  │                                                                  │   │
│  │  a) Validate user access to sheet (Google API)                  │   │
│  │  b) Fetch schema (column names, types)                          │   │
│  │  c) Fetch data (all rows)                                       │   │
│  │  d) Create table in MotherDuck                                  │   │
│  │  e) Insert data                                                 │   │
│  │  f) Save metadata to Supabase                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│         │                                                               │
│         ▼                                                               │
│  4. DATA STORED                                                         │
│  ┌──────────────────────┐  ┌──────────────────────────────────────┐    │
│  │ Supabase             │  │ MotherDuck (User's)                  │    │
│  │                      │  │                                      │    │
│  │ data_sources: {      │  │ CREATE TABLE beneficiaries (         │    │
│  │   id: "src_123",     │  │   id TEXT,                           │    │
│  │   sheet_id: "1abc",  │  │   name TEXT,                         │    │
│  │   table: "benefic..",│  │   district TEXT,                     │    │
│  │   rows: 12456,       │  │   age INTEGER,                       │    │
│  │   synced_at: "..."   │  │   ...                                │    │
│  │ }                    │  │ );                                   │    │
│  └──────────────────────┘  └──────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Transformation Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TRANSFORMATION FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. USER BUILDS TRANSFORMATION ON CANVAS                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │   [beneficiaries] ──▶ [Filter: Active] ──▶ [Group by District]  │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    │ Stored as JSON recipe              │
│                                    ▼                                    │
│  2. RECIPE GENERATED (Frontend)                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ {                                                                │   │
│  │   "steps": [                                                     │   │
│  │     { "type": "source", "table": "beneficiaries" },             │   │
│  │     { "type": "filter", "column": "status", "op": "=",          │   │
│  │       "value": "Active" },                                       │   │
│  │     { "type": "group", "by": ["district"],                      │   │
│  │       "aggs": [{"fn": "count", "col": "id", "as": "total"}] }   │   │
│  │   ]                                                              │   │
│  │ }                                                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    │ POST /api/v1/transforms/execute    │
│                                    ▼                                    │
│  3. SQL GENERATED (Backend)                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ SQLGenerator.generate(recipe) →                                  │   │
│  │                                                                  │   │
│  │   WITH step_1 AS (                                              │   │
│  │     SELECT * FROM beneficiaries                                 │   │
│  │   ),                                                            │   │
│  │   step_2 AS (                                                   │   │
│  │     SELECT * FROM step_1 WHERE status = 'Active'                │   │
│  │   ),                                                            │   │
│  │   step_3 AS (                                                   │   │
│  │     SELECT district, COUNT(id) as total                         │   │
│  │     FROM step_2                                                 │   │
│  │     GROUP BY district                                           │   │
│  │   )                                                             │   │
│  │   SELECT * FROM step_3                                          │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    │ Execute on MotherDuck              │
│                                    ▼                                    │
│  4. RESULTS RETURNED                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ district    │ total                                              │   │
│  │ ────────────┼───────                                             │   │
│  │ Nairobi     │ 4,521                                              │   │
│  │ Mombasa     │ 3,200                                              │   │
│  │ Kisumu      │ 2,100                                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Ingestion System

### Google Sheets Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GOOGLE SHEETS INTEGRATION                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AUTHENTICATION FLOW                                                    │
│  ───────────────────                                                    │
│                                                                         │
│  ┌─────────┐     ┌──────────┐     ┌─────────┐     ┌────────────────┐  │
│  │  User   │────▶│ Supabase │────▶│ Google  │────▶│ Access Token   │  │
│  │         │     │  Auth    │     │  OAuth  │     │ + Refresh Token│  │
│  └─────────┘     └──────────┘     └─────────┘     └────────────────┘  │
│                                                                         │
│  SCOPES REQUESTED:                                                      │
│  • https://www.googleapis.com/auth/spreadsheets.readonly               │
│  • https://www.googleapis.com/auth/drive.readonly                      │
│                                                                         │
│  TOKEN STORAGE:                                                         │
│  • Encrypted in Supabase                                                │
│  • Auto-refresh on expiry                                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Sync Mechanism

```python
# core/ingestion.py

class IngestionService:
    """Handles Google Sheets to MotherDuck sync."""

    async def sync_source(
        self,
        source_id: str,
        user_id: str,
        full_refresh: bool = False
    ) -> SyncResult:
        """
        Sync a Google Sheet to MotherDuck.

        Flow:
        1. Get source config from Supabase
        2. Fetch data from Google Sheets
        3. Detect schema changes
        4. Load to MotherDuck
        5. Update sync metadata
        """
        # 1. Get source config
        source = await self.get_source(source_id)

        # 2. Fetch from Google Sheets
        sheets_client = GoogleSheetsClient(
            await self.get_user_token(user_id)
        )
        data = await sheets_client.get_sheet_data(
            sheet_id=source.sheet_id,
            tab=source.sheet_tab
        )

        # 3. Detect schema
        schema = self.infer_schema(data)

        # 4. Load to MotherDuck
        md_client = MotherDuckClient(
            await self.get_user_md_token(user_id)
        )

        if full_refresh or self.schema_changed(source.schema, schema):
            await md_client.recreate_table(
                table=source.table_name,
                schema=schema,
                data=data
            )
        else:
            await md_client.upsert_data(
                table=source.table_name,
                data=data
            )

        # 5. Update metadata
        await self.update_source_metadata(
            source_id=source_id,
            row_count=len(data),
            schema=schema,
            synced_at=datetime.utcnow()
        )

        return SyncResult(
            success=True,
            rows_synced=len(data)
        )
```

### Schema Inference

```python
# core/schema.py

from enum import Enum
from typing import Any

class ColumnType(str, Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    FLOAT = "DOUBLE"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP"

def infer_column_type(values: list[Any]) -> ColumnType:
    """
    Infer DuckDB column type from sample values.

    Priority: DATE > INTEGER > FLOAT > BOOLEAN > TEXT
    """
    non_null = [v for v in values if v is not None and v != ""]

    if not non_null:
        return ColumnType.TEXT

    # Try date patterns
    if all(looks_like_date(v) for v in non_null[:100]):
        return ColumnType.DATE

    # Try integer
    if all(looks_like_integer(v) for v in non_null[:100]):
        return ColumnType.INTEGER

    # Try float
    if all(looks_like_float(v) for v in non_null[:100]):
        return ColumnType.FLOAT

    # Try boolean
    if all(looks_like_boolean(v) for v in non_null[:100]):
        return ColumnType.BOOLEAN

    return ColumnType.TEXT


def infer_schema(data: list[dict]) -> dict[str, ColumnType]:
    """Infer schema from data."""
    if not data:
        return {}

    columns = data[0].keys()
    schema = {}

    for col in columns:
        values = [row.get(col) for row in data]
        schema[col] = infer_column_type(values)

    return schema
```

---

## Transformation Engine

### Step Types

```python
# core/transforms/types.py

from enum import Enum
from pydantic import BaseModel

class StepType(str, Enum):
    SOURCE = "source"
    FILTER = "filter"
    SELECT = "select"
    JOIN = "join"
    GROUP = "group"
    SORT = "sort"
    DISTINCT = "distinct"
    ADD_COLUMN = "add_column"
    RENAME = "rename"
    CLEAN = "clean"
    SPLIT = "split"
    COMBINE = "combine"

# Filter step config
class FilterConfig(BaseModel):
    column: str
    operator: str  # equals, not_equals, contains, gt, lt, etc.
    value: str | int | float | list
    case_sensitive: bool = False

# Join step config
class JoinConfig(BaseModel):
    right_table: str
    left_on: str
    right_on: str
    join_type: str = "left"  # left, inner, right, full
    columns_to_include: list[str] | None = None

# Group step config
class GroupConfig(BaseModel):
    group_by: list[str]
    aggregates: list[AggregateConfig]

class AggregateConfig(BaseModel):
    function: str  # count, sum, avg, min, max, count_distinct
    column: str
    alias: str

# Add column config
class AddColumnConfig(BaseModel):
    name: str
    type: str  # categorize, math, text, date, boolean
    config: dict  # Type-specific configuration

# Clean config
class CleanConfig(BaseModel):
    columns: list[str]
    operations: list[str]  # trim, upper, lower, title, remove_nulls
    null_replacement: str | None = None
```

### SQL Generator

```python
# core/transforms/sql_generator.py

class SQLGenerator:
    """
    Converts transformation recipes to SQL.

    Each step becomes a CTE (Common Table Expression).
    """

    def generate(self, recipe: TransformRecipe) -> str:
        """Generate SQL from recipe."""
        ctes = []
        prev_step = None

        for i, step in enumerate(recipe.steps):
            step_name = f"step_{i + 1}"
            sql = self._generate_step(step, prev_step)
            ctes.append(f"{step_name} AS (\n{sql}\n)")
            prev_step = step_name

        # Combine CTEs
        cte_sql = ",\n".join(ctes)
        final_sql = f"WITH {cte_sql}\nSELECT * FROM {prev_step}"

        return final_sql

    def _generate_step(self, step: TransformStep, prev: str | None) -> str:
        """Generate SQL for a single step."""
        match step.type:
            case StepType.SOURCE:
                return self._gen_source(step.config)
            case StepType.FILTER:
                return self._gen_filter(step.config, prev)
            case StepType.SELECT:
                return self._gen_select(step.config, prev)
            case StepType.JOIN:
                return self._gen_join(step.config, prev)
            case StepType.GROUP:
                return self._gen_group(step.config, prev)
            case StepType.ADD_COLUMN:
                return self._gen_add_column(step.config, prev)
            case StepType.CLEAN:
                return self._gen_clean(step.config, prev)
            case _:
                raise ValueError(f"Unknown step type: {step.type}")

    def _gen_source(self, config: SourceConfig) -> str:
        return f"SELECT * FROM {config.table}"

    def _gen_filter(self, config: FilterConfig, prev: str) -> str:
        condition = self._build_condition(config)
        return f"SELECT * FROM {prev} WHERE {condition}"

    def _gen_join(self, config: JoinConfig, prev: str) -> str:
        join_type = config.join_type.upper()
        cols = "*"
        if config.columns_to_include:
            left_cols = f"{prev}.*"
            right_cols = ", ".join(
                f"{config.right_table}.{c}"
                for c in config.columns_to_include
            )
            cols = f"{left_cols}, {right_cols}"

        return f"""
            SELECT {cols}
            FROM {prev}
            {join_type} JOIN {config.right_table}
            ON {prev}.{config.left_on} = {config.right_table}.{config.right_on}
        """

    def _gen_group(self, config: GroupConfig, prev: str) -> str:
        group_cols = ", ".join(config.group_by)
        agg_cols = ", ".join(
            f"{a.function.upper()}({a.column}) AS {a.alias}"
            for a in config.aggregates
        )
        return f"""
            SELECT {group_cols}, {agg_cols}
            FROM {prev}
            GROUP BY {group_cols}
        """

    def _gen_add_column(self, config: AddColumnConfig, prev: str) -> str:
        """Generate calculated column."""
        match config.type:
            case "categorize":
                expr = self._build_case_when(config.config)
            case "math":
                expr = self._build_math_expr(config.config)
            case "text":
                expr = self._build_text_expr(config.config)
            case "date":
                expr = self._build_date_expr(config.config)
            case _:
                raise ValueError(f"Unknown column type: {config.type}")

        return f"SELECT *, {expr} AS {config.name} FROM {prev}"

    def _gen_clean(self, config: CleanConfig, prev: str) -> str:
        """Generate data cleaning SQL."""
        transformations = []

        for col in config.columns:
            expr = col
            for op in config.operations:
                match op:
                    case "trim":
                        expr = f"TRIM({expr})"
                    case "upper":
                        expr = f"UPPER({expr})"
                    case "lower":
                        expr = f"LOWER({expr})"
                    case "title":
                        expr = f"INITCAP({expr})"

            transformations.append(f"{expr} AS {col}")

        # Get other columns
        other_cols = f"* EXCLUDE ({', '.join(config.columns)})"

        return f"SELECT {other_cols}, {', '.join(transformations)} FROM {prev}"

    def _build_condition(self, config: FilterConfig) -> str:
        """Build WHERE condition."""
        col = config.column
        val = config.value

        if isinstance(val, str):
            val = f"'{val}'"

        match config.operator:
            case "equals":
                return f"{col} = {val}"
            case "not_equals":
                return f"{col} != {val}"
            case "contains":
                return f"{col} ILIKE '%{config.value}%'"
            case "starts_with":
                return f"{col} ILIKE '{config.value}%'"
            case "gt":
                return f"{col} > {val}"
            case "gte":
                return f"{col} >= {val}"
            case "lt":
                return f"{col} < {val}"
            case "lte":
                return f"{col} <= {val}"
            case "is_null":
                return f"{col} IS NULL"
            case "is_not_null":
                return f"{col} IS NOT NULL"
            case "in":
                values = ", ".join(f"'{v}'" for v in config.value)
                return f"{col} IN ({values})"
            case _:
                raise ValueError(f"Unknown operator: {config.operator}")

    def _build_case_when(self, config: dict) -> str:
        """Build CASE WHEN for categorization."""
        cases = []
        for rule in config.get("rules", []):
            condition = self._build_condition(FilterConfig(**rule["condition"]))
            cases.append(f"WHEN {condition} THEN '{rule['value']}'")

        default = config.get("default", "NULL")
        if isinstance(default, str) and default != "NULL":
            default = f"'{default}'"

        return f"CASE {' '.join(cases)} ELSE {default} END"
```

### Transformation Execution

```python
# core/transforms/executor.py

class TransformExecutor:
    """Execute transformations on MotherDuck."""

    def __init__(self, md_client: MotherDuckClient):
        self.md_client = md_client
        self.sql_generator = SQLGenerator()

    async def preview(
        self,
        recipe: TransformRecipe,
        limit: int = 100
    ) -> PreviewResult:
        """
        Execute transformation and return preview.

        Returns limited rows for UI preview.
        """
        sql = self.sql_generator.generate(recipe)
        sql_with_limit = f"{sql} LIMIT {limit}"

        result = await self.md_client.execute(sql_with_limit)

        return PreviewResult(
            columns=result.columns,
            rows=result.rows,
            total_rows=await self._count_rows(sql),
            sql=sql  # For debugging/advanced users
        )

    async def execute_and_save(
        self,
        recipe: TransformRecipe,
        output_table: str
    ) -> ExecuteResult:
        """
        Execute transformation and save to table.

        Creates a new table with the results.
        """
        sql = self.sql_generator.generate(recipe)

        create_sql = f"""
            CREATE OR REPLACE TABLE {output_table} AS
            {sql}
        """

        await self.md_client.execute(create_sql)
        row_count = await self.md_client.count_rows(output_table)

        return ExecuteResult(
            success=True,
            table=output_table,
            row_count=row_count
        )

    async def _count_rows(self, sql: str) -> int:
        """Get total row count for a query."""
        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql}) t"
        result = await self.md_client.execute(count_sql)
        return result.rows[0]["cnt"]
```

---

## API Design

### REST API Endpoints

```yaml
# OpenAPI-style specification

/api/v1/sources:
  GET:
    summary: List all data sources
    response: Source[]

  POST:
    summary: Add new data source
    body:
      sheet_id: string
      sheet_tab: string
      table_name: string
      sync_frequency: "manual" | "6h" | "daily"
    response: Source

/api/v1/sources/{id}:
  GET:
    summary: Get source details
    response: Source

  DELETE:
    summary: Remove data source
    response: { success: true }

/api/v1/sources/{id}/sync:
  POST:
    summary: Trigger manual sync
    body:
      full_refresh: boolean
    response: SyncResult

/api/v1/sources/{id}/preview:
  GET:
    summary: Preview source data
    query:
      limit: number (default: 100)
    response: PreviewResult

# Transformations
/api/v1/transforms:
  GET:
    summary: List all transformations
    response: Transform[]

  POST:
    summary: Create new transformation
    body: TransformRecipe
    response: Transform

/api/v1/transforms/{id}:
  GET:
    summary: Get transformation details
    response: Transform

  PUT:
    summary: Update transformation
    body: TransformRecipe
    response: Transform

  DELETE:
    summary: Delete transformation
    response: { success: true }

/api/v1/transforms/{id}/preview:
  POST:
    summary: Preview transformation results
    body:
      recipe: TransformRecipe
      limit: number
    response: PreviewResult

/api/v1/transforms/{id}/execute:
  POST:
    summary: Execute and save transformation
    body:
      output_table: string
    response: ExecuteResult

# Warehouse
/api/v1/warehouse/tables:
  GET:
    summary: List all tables in user's warehouse
    response: Table[]

/api/v1/warehouse/tables/{name}:
  GET:
    summary: Get table schema and stats
    response: TableInfo

  DELETE:
    summary: Drop table
    response: { success: true }

/api/v1/warehouse/query:
  POST:
    summary: Execute raw SQL (advanced users)
    body:
      sql: string
      limit: number
    response: QueryResult
```

### Response Types

```typescript
// types/api.ts

interface Source {
  id: string;
  name: string;
  sheet_id: string;
  sheet_tab: string | null;
  table_name: string;
  sync_frequency: 'manual' | '6h' | 'daily';
  last_synced_at: string | null;
  row_count: number;
  schema: ColumnSchema[];
  status: 'syncing' | 'synced' | 'error';
}

interface ColumnSchema {
  name: string;
  type: 'TEXT' | 'INTEGER' | 'DOUBLE' | 'BOOLEAN' | 'DATE' | 'TIMESTAMP';
}

interface Transform {
  id: string;
  name: string;
  description: string | null;
  canvas_state: CanvasState;
  recipe: TransformRecipe;
  output_table: string | null;
  created_at: string;
  updated_at: string;
}

interface TransformRecipe {
  steps: TransformStep[];
}

interface TransformStep {
  id: string;
  type: StepType;
  config: StepConfig;
}

interface PreviewResult {
  columns: ColumnSchema[];
  rows: Record<string, any>[];
  total_rows: number;
  sql?: string;
}

interface SyncResult {
  success: boolean;
  rows_synced: number;
  duration_ms: number;
  error?: string;
}
```

---

## Security Architecture

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AUTHENTICATION FLOW                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. User clicks "Sign in with Google"                                   │
│     └──▶ Supabase Auth redirects to Google                             │
│                                                                         │
│  2. Google OAuth consent                                                │
│     └──▶ User grants: profile, email, spreadsheets.readonly            │
│                                                                         │
│  3. Callback to Supabase                                                │
│     └──▶ Supabase creates/updates user                                 │
│     └──▶ Stores Google refresh token (encrypted)                       │
│     └──▶ Issues JWT to frontend                                        │
│                                                                         │
│  4. Frontend stores JWT                                                 │
│     └──▶ Sent with every API request                                   │
│                                                                         │
│  5. Backend verifies JWT                                                │
│     └──▶ Extracts user_id, org_id                                      │
│     └──▶ All queries scoped to org                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Isolation

```sql
-- Row Level Security ensures data isolation

-- Organizations table
CREATE POLICY "Users see own org"
ON organizations FOR SELECT
USING (
    id IN (SELECT organization_id FROM users WHERE id = auth.uid())
);

-- Data sources scoped to org
CREATE POLICY "Org members see org sources"
ON data_sources FOR ALL
USING (
    organization_id IN (
        SELECT organization_id FROM users WHERE id = auth.uid()
    )
);

-- Same for transformations
CREATE POLICY "Org members see org transforms"
ON transformations FOR ALL
USING (
    organization_id IN (
        SELECT organization_id FROM users WHERE id = auth.uid()
    )
);
```

### Credential Management

```python
# core/security.py

from cryptography.fernet import Fernet

class CredentialManager:
    """
    Manages encrypted storage of user credentials.

    - Google OAuth tokens
    - MotherDuck tokens
    """

    def __init__(self, encryption_key: str):
        self.fernet = Fernet(encryption_key.encode())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt sensitive data."""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt sensitive data."""
        return self.fernet.decrypt(ciphertext.encode()).decode()

    async def store_google_token(
        self,
        user_id: str,
        token: dict
    ) -> None:
        """Store encrypted Google OAuth token."""
        encrypted = self.encrypt(json.dumps(token))
        await self.db.execute(
            """
            UPDATE users
            SET google_token_encrypted = $1
            WHERE id = $2
            """,
            encrypted, user_id
        )

    async def get_google_token(self, user_id: str) -> dict:
        """Retrieve and decrypt Google OAuth token."""
        result = await self.db.fetchone(
            "SELECT google_token_encrypted FROM users WHERE id = $1",
            user_id
        )
        return json.loads(self.decrypt(result["google_token_encrypted"]))
```

---

## Deployment Architecture

### Production Setup

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PRODUCTION ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                           ┌─────────────┐                               │
│                           │   Vercel    │                               │
│                           │  (Next.js)  │                               │
│                           │             │                               │
│                           │  - CDN edge │                               │
│                           │  - SSR      │                               │
│                           │  - API routes│                              │
│                           └──────┬──────┘                               │
│                                  │                                      │
│                                  │ HTTPS                                │
│                                  ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Railway / Render                          │   │
│  │                                                                  │   │
│  │   ┌──────────────────────────────────────────────────────────┐ │   │
│  │   │                   FastAPI Application                     │ │   │
│  │   │                                                           │ │   │
│  │   │  • Auto-scaling containers                                │ │   │
│  │   │  • Health checks                                          │ │   │
│  │   │  • Environment variables                                  │ │   │
│  │   └──────────────────────────────────────────────────────────┘ │   │
│  │                              │                                   │   │
│  └──────────────────────────────┼───────────────────────────────────┘   │
│                                 │                                       │
│              ┌──────────────────┼──────────────────┐                   │
│              │                  │                  │                   │
│              ▼                  ▼                  ▼                   │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────────┐     │
│  │   Supabase     │  │  Google APIs    │  │    MotherDuck       │     │
│  │                │  │                 │  │   (User's Account)  │     │
│  │  • PostgreSQL  │  │  • Sheets API   │  │                     │     │
│  │  • Auth        │  │  • Drive API    │  │  • Query execution  │     │
│  │  • Realtime    │  │  • OAuth        │  │  • Data storage     │     │
│  └────────────────┘  └─────────────────┘  └─────────────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Environment Configuration

```yaml
# docker-compose.yml (for local development)

version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - NEXT_PUBLIC_API_URL=http://localhost:8000

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Scaling Considerations

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SCALING STRATEGY                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  FRONTEND (Vercel):                                                     │
│  • Automatic edge deployment                                            │
│  • Serverless functions for API routes                                  │
│  • No manual scaling needed                                             │
│                                                                         │
│  BACKEND (Railway/Render):                                              │
│  • Horizontal scaling via replicas                                      │
│  • Start with 1 instance, scale to 3+ as needed                        │
│  • Stateless design enables easy scaling                                │
│                                                                         │
│  DATABASE (Supabase):                                                   │
│  • Free tier: Good for 50k MAU                                         │
│  • Pro tier: Dedicated compute if needed                                │
│  • Connection pooling via Supavisor                                     │
│                                                                         │
│  DATA WAREHOUSE (MotherDuck):                                           │
│  • Each user has own account                                            │
│  • No centralized scaling concern                                       │
│  • Costs distributed to users                                           │
│                                                                         │
│  BOTTLENECKS TO MONITOR:                                                │
│  • Google Sheets API rate limits (100 req/100sec per user)             │
│  • Large sheet syncs (use pagination)                                   │
│  • Complex transformations (add query timeouts)                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: Key Design Patterns

### 1. Recipe Pattern

All transformations stored as declarative JSON recipes, not imperative code:

```json
{
  "version": "1.0",
  "steps": [...]
}
```

Benefits:
- Portable (can re-execute on different backends)
- Auditable (full history)
- Versionable (schema migrations)

### 2. CTE-Based SQL Generation

Each transformation step becomes a CTE:

```sql
WITH
  step_1 AS (...),
  step_2 AS (...),
  step_3 AS (...)
SELECT * FROM step_3
```

Benefits:
- Readable generated SQL
- Easy debugging
- Optimizer handles efficiency

### 3. Progressive Loading

Preview data loads progressively:

1. Show schema immediately
2. Load first 100 rows
3. Calculate total count async
4. Enable pagination

### 4. Optimistic UI Updates

Canvas updates locally before server confirmation:

1. User adds filter node
2. UI updates immediately
3. Recipe saved to server async
4. Rollback on error

---

*Document maintained by: Dalgo Lite Architecture Team*
*Last updated: February 2026*
