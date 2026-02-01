# Dalgo Lite: System Architecture

**Version:** 2.0
**Date:** February 2026
**Status:** Design (Updated with DLT + Ibis)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Ingestion System (DLT)](#ingestion-system-dlt)
6. [Transformation Engine (Ibis)](#transformation-engine-ibis)
7. [Pipeline Scheduling](#pipeline-scheduling)
8. [API Design](#api-design)
9. [Security Architecture](#security-architecture)
10. [Deployment Architecture](#deployment-architecture)

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
│  │   │   Pipeline   │  │ Transformer  │  │     AG Grid Preview      │ │   │
│  │   │    Canvas    │  │    Editor    │  │  (Server-Side Pagination)│ │   │
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
│  │   │     DLT      │  │    Ibis      │  │      Supabase            │ │   │
│  │   │  Ingestion   │  │  Transform   │  │    Warehouse             │ │   │
│  │   └──────────────┘  └──────────────┘  └──────────────────────────┘ │   │
│  │                          FastAPI + Python                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                          │                    │                             │
│                          ▼                    ▼                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        SUPABASE (Single Warehouse)                   │  │
│  │                                                                      │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │  │
│  │  │    Metadata     │  │    Raw Data     │  │  Transformed Data   │ │  │
│  │  │    (users,      │  │   (source_*)    │  │    (transform_*)    │ │  │
│  │  │  orgs, sources) │  │                 │  │                     │ │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data Ingestion | DLT (Data Load Tool) | Lightweight Python library, handles pagination, retries, schema inference |
| Transformations | Ibis + SQLGlot | Battle-tested at Netflix, compiles Python to SQL, 20+ backend support |
| Warehouse | Supabase PostgreSQL | Single database for metadata, raw data, and transforms |
| Preview Grid | AG Grid Community | Handles millions of rows, server-side pagination, free |
| Scheduling | Pipeline-based | One schedule per pipeline, all sources sync then transforms run |

---

## Architecture Principles

### 1. Single Warehouse Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUPABASE AS SINGLE WAREHOUSE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  METADATA TABLES (public schema):                               │
│  ─────────────────────────────                                  │
│  • users, organizations, organization_members                   │
│  • sources, source_schemas, sync_runs                           │
│  • transformations, transformation_versions, transformation_runs│
│  • pipelines, schedules                                         │
│                                                                 │
│  RAW DATA (org-specific schema):                                │
│  ──────────────────────────────                                 │
│  • org_{org_id}.source_{source_id}                              │
│  • Tables created dynamically per source                        │
│  • Schema inferred from source data                             │
│                                                                 │
│  TRANSFORMED DATA (org-specific schema):                        │
│  ────────────────────────────────────────                       │
│  • org_{org_id}.transform_{transform_id}                        │
│  • Created when transformation is executed                      │
│  • Can be input to other transformations                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Recipe Pattern with Ibis

Transformations stored as **JSON recipes**, converted to **Ibis expressions**, then compiled to **SQL**:

```json
{
  "id": "trans_abc123",
  "name": "Active Beneficiaries by District",
  "steps": [
    {
      "type": "source",
      "table": "raw_beneficiaries"
    },
    {
      "type": "filter",
      "column": "status",
      "operator": "equals",
      "value": "Active"
    },
    {
      "type": "group",
      "by": ["district"],
      "aggregates": [
        { "function": "count", "column": "id", "alias": "total" }
      ]
    }
  ]
}
```

Recipe → Ibis:
```python
expr = con.table("raw_beneficiaries")
expr = expr.filter(expr.status == "Active")
expr = expr.group_by("district").aggregate(total=expr.id.count())
```

Ibis → SQL (via SQLGlot):
```sql
SELECT district, COUNT(id) AS total
FROM raw_beneficiaries
WHERE status = 'Active'
GROUP BY district
```

### 3. Pipeline-Based Scheduling

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE EXECUTION MODEL                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PIPELINE = Sources + Transformations + Schedule                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Pipeline: "Monthly Donor Report"                        │   │
│  │                                                          │   │
│  │  Sources:                                                │   │
│  │  ├── Google Sheet: Donations                             │   │
│  │  └── Google Sheet: Donors                                │   │
│  │                                                          │   │
│  │  Transformations:                                        │   │
│  │  ├── [1] Clean Donations → cleaned_donations             │   │
│  │  └── [2] Join + Summarize → donor_summary (uses [1])     │   │
│  │                                                          │   │
│  │  Schedule: Daily at 6:00 AM                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  EXECUTION ORDER:                                               │
│  1. Sync all sources (parallel)                                 │
│  2. Wait for all syncs to complete                              │
│  3. Run transformations in dependency order                     │
│  4. Mark pipeline run complete                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
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
│  │   └── signup/page.tsx                                                │
│  │                                                                      │
│  ├── (dashboard)/                 # Protected routes                    │
│  │   ├── layout.tsx               # Dashboard shell                     │
│  │   ├── page.tsx                 # Pipeline canvas (home)              │
│  │   │                                                                  │
│  │   ├── pipelines/               # Pipeline management                 │
│  │   │   ├── page.tsx             # Pipeline list                       │
│  │   │   └── [id]/page.tsx        # Pipeline detail                     │
│  │   │                                                                  │
│  │   ├── transformations/         # Transformation views                │
│  │   │   ├── page.tsx             # Transform list                      │
│  │   │   ├── new/page.tsx         # New transformation                  │
│  │   │   └── [id]/page.tsx        # Transformation editor               │
│  │   │                                                                  │
│  │   └── settings/                # Organization settings               │
│  │       └── page.tsx                                                   │
│  │                                                                      │
│  components/                                                            │
│  ├── ui/                          # Base UI (Radix primitives)          │
│  │                                                                      │
│  ├── canvas/                      # React Flow components               │
│  │   ├── DataPipelineCanvas.tsx   # Main pipeline view                  │
│  │   ├── nodes/                   # Custom node types                   │
│  │   │   ├── SourceNode.tsx                                             │
│  │   │   ├── WarehouseNode.tsx                                          │
│  │   │   └── AddSourceNode.tsx                                          │
│  │   └── edges/                   # Custom edge types                   │
│  │       └── AnimatedEdge.tsx                                           │
│  │                                                                      │
│  ├── transform/                   # Transformation editor               │
│  │   ├── TransformEditor.tsx      # Main editor layout                  │
│  │   ├── DataGrid.tsx             # AG Grid wrapper                     │
│  │   ├── StepsPanel.tsx           # Applied steps sidebar               │
│  │   └── actions/                 # Action modals                       │
│  │       ├── FilterModal.tsx                                            │
│  │       ├── CombineModal.tsx     # JOIN                                │
│  │       ├── SummarizeModal.tsx   # GROUP BY                            │
│  │       ├── CleanModal.tsx                                             │
│  │       └── CategorizeModal.tsx                                        │
│  │                                                                      │
│  hooks/                                                                 │
│  ├── useSources.ts                # Source API hooks                    │
│  ├── useTransformations.ts        # Transform API hooks                 │
│  └── usePipelines.ts              # Pipeline API hooks                  │
│                                                                         │
│  lib/                                                                   │
│  ├── api.ts                       # API client with auth                │
│  └── recipe-builder.ts            # Recipe JSON construction            │
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
│  │  /api/v1/sources        → SourceRouter                          │   │
│  │  /api/v1/transforms     → TransformRouter                       │   │
│  │  /api/v1/pipelines      → PipelineRouter                        │   │
│  │  /api/v1/warehouse      → WarehouseRouter                       │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      SERVICE LAYER                               │   │
│  │                                                                  │   │
│  │  ┌───────────────────┐  ┌────────────────────┐  ┌─────────────┐ │   │
│  │  │  DLTIngestionSvc  │  │ IbisTransformSvc   │  │ PipelineSvc │ │   │
│  │  │                   │  │                    │  │             │ │   │
│  │  │ • sync_source()   │  │ • parse_recipe()   │  │ • create()  │ │   │
│  │  │ • get_schema()    │  │ • to_ibis_expr()   │  │ • run()     │ │   │
│  │  │ • list_sheets()   │  │ • preview()        │  │ • schedule()│ │   │
│  │  │                   │  │ • execute()        │  │             │ │   │
│  │  └───────────────────┘  └────────────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        CORE LAYER                                │   │
│  │                                                                  │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │   │
│  │  │       DLT        │  │   Ibis + SQLGlot │  │  Supabase     │ │   │
│  │  │                  │  │                  │  │  Client       │ │   │
│  │  │ Data ingestion   │  │ Recipe → SQL     │  │               │ │   │
│  │  │ from any source  │  │ compilation      │  │ Query exec    │ │   │
│  │  └──────────────────┘  └──────────────────┘  └───────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Ingestion Flow (DLT)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          INGESTION FLOW (DLT)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. USER ADDS SOURCE                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ AddSourceModal                                                   │   │
│  │ ├── CSV Upload → File stored temporarily                         │   │
│  │ ├── Google Sheets → Spreadsheet ID + Sheet Name                  │   │
│  │ └── KoboToolbox → Form ID + API Key (future)                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  2. DLT PIPELINE RUNS                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  import dlt                                                      │   │
│  │                                                                  │   │
│  │  # Google Sheets source                                          │   │
│  │  @dlt.resource                                                   │   │
│  │  def google_sheets(spreadsheet_id: str, sheet_name: str):        │   │
│  │      sheets_client = get_sheets_client()                         │   │
│  │      data = sheets_client.get_values(spreadsheet_id, sheet_name) │   │
│  │      yield from data                                             │   │
│  │                                                                  │   │
│  │  # Run pipeline                                                  │   │
│  │  pipeline = dlt.pipeline(                                        │   │
│  │      pipeline_name="source_sync",                                │   │
│  │      destination=dlt.destinations.postgres(connection_url),      │   │
│  │      dataset_name=f"org_{org_id}"                                │   │
│  │  )                                                               │   │
│  │  pipeline.run(google_sheets(spreadsheet_id, sheet_name))         │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  3. DATA LOADED TO SUPABASE                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  Schema: org_{org_id}                                            │   │
│  │  Table: source_{source_id}                                       │   │
│  │                                                                  │   │
│  │  Columns automatically inferred:                                 │   │
│  │  • id (TEXT) - from source                                       │   │
│  │  • name (TEXT)                                                   │   │
│  │  • district (TEXT)                                               │   │
│  │  • age (INTEGER)                                                 │   │
│  │  • _dlt_load_id (TEXT) - DLT metadata                            │   │
│  │  • _dlt_id (TEXT) - DLT row identifier                           │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Transformation Flow (Ibis)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TRANSFORMATION FLOW (IBIS)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. USER BUILDS TRANSFORMATION (Excel-like UI)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────────────────────────┐   │   │
│  │  │  Applied Steps  │  │         Data Preview (AG Grid)      │   │   │
│  │  │                 │  │                                     │   │   │
│  │  │  1. beneficiaries│  │  name     │ district │ status      │   │   │
│  │  │  2. Filter       │  │  ─────────┼──────────┼───────────  │   │   │
│  │  │  3. Combine      │  │  Alice    │ Nairobi  │ Active      │   │   │
│  │  │                 │  │  Bob      │ Mombasa  │ Active      │   │   │
│  │  │  [+ Add Step]   │  │  ...      │ ...      │ ...         │   │   │
│  │  └─────────────────┘  └─────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  │  Actions: [Filter] [Combine] [Summarize] [Clean] [Categorize]   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    │ Recipe JSON stored                 │
│                                    ▼                                    │
│  2. RECIPE STORED                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ {                                                                │   │
│  │   "steps": [                                                     │   │
│  │     { "type": "source", "table": "source_abc123" },             │   │
│  │     { "type": "filter", "column": "status",                     │   │
│  │       "operator": "equals", "value": "Active" },                │   │
│  │     { "type": "join", "with": "source_def456",                  │   │
│  │       "left_on": "district_id", "right_on": "id" }              │   │
│  │   ]                                                              │   │
│  │ }                                                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    │ POST /api/v1/transforms/preview    │
│                                    ▼                                    │
│  3. IBIS EXPRESSION BUILT                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  con = ibis.postgres.connect(url=supabase_url)                   │   │
│  │                                                                  │   │
│  │  # Build expression from recipe                                  │   │
│  │  expr = con.table("org_xxx.source_abc123")                       │   │
│  │  expr = expr.filter(expr.status == "Active")                     │   │
│  │  expr = expr.left_join(                                          │   │
│  │      con.table("org_xxx.source_def456"),                         │   │
│  │      expr.district_id == _.id                                    │   │
│  │  )                                                               │   │
│  │                                                                  │   │
│  │  # Compile to SQL                                                │   │
│  │  sql = ibis.to_sql(expr)                                         │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    │ Execute on Supabase                │
│                                    ▼                                    │
│  4. RESULTS (Preview or Materialize)                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  Preview Mode:                                                   │   │
│  │  • Execute: SELECT ... LIMIT 100 OFFSET {page * 100}            │   │
│  │  • Return rows to AG Grid                                        │   │
│  │  • Server-side pagination (never load all data)                  │   │
│  │                                                                  │   │
│  │  Execute Mode:                                                   │   │
│  │  • CREATE TABLE org_xxx.transform_yyy AS SELECT ...              │   │
│  │  • Track in warehouse_tables                                     │   │
│  │  • Available as input to other transformations                   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Ingestion System (DLT)

### DLT Ingestion Service

```python
# app/services/dlt_ingestion.py

import dlt
from dlt.destinations import postgres
from google.oauth2 import service_account
from googleapiclient.discovery import build

class DLTIngestionService:
    """
    Data ingestion using DLT (Data Load Tool).

    Features:
    - Automatic schema inference
    - Incremental loading support
    - Retry/pagination handling
    - Multiple source types
    """

    def __init__(self, warehouse_url: str, org_id: str):
        self.warehouse_url = warehouse_url
        self.org_id = org_id
        self.schema_name = f"org_{org_id}"

    async def sync_google_sheet(
        self,
        source_id: str,
        spreadsheet_id: str,
        sheet_name: str
    ) -> SyncResult:
        """Sync a Google Sheet to warehouse."""

        @dlt.resource(name=f"source_{source_id}")
        def google_sheets_data():
            """DLT resource for Google Sheets."""
            creds = service_account.Credentials.from_service_account_info(
                settings.google_credentials,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )
            service = build("sheets", "v4", credentials=creds)

            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=sheet_name
            ).execute()

            values = result.get("values", [])
            if not values:
                return

            headers = values[0]
            for row in values[1:]:
                # Pad row if shorter than headers
                padded = row + [""] * (len(headers) - len(row))
                yield dict(zip(headers, padded))

        # Create and run pipeline
        pipeline = dlt.pipeline(
            pipeline_name=f"source_{source_id}",
            destination=postgres(self.warehouse_url),
            dataset_name=self.schema_name
        )

        load_info = pipeline.run(
            google_sheets_data(),
            write_disposition="replace"  # Full refresh
        )

        return SyncResult(
            success=not load_info.has_failed_jobs,
            rows_synced=load_info.metrics.get("rows_total", 0),
            load_id=load_info.load_id
        )

    async def sync_csv(
        self,
        source_id: str,
        file_path: str
    ) -> SyncResult:
        """Sync a CSV file to warehouse."""

        @dlt.resource(name=f"source_{source_id}")
        def csv_data():
            import csv
            with open(file_path, "r") as f:
                reader = csv.DictReader(f)
                yield from reader

        pipeline = dlt.pipeline(
            pipeline_name=f"source_{source_id}",
            destination=postgres(self.warehouse_url),
            dataset_name=self.schema_name
        )

        load_info = pipeline.run(
            csv_data(),
            write_disposition="replace"
        )

        return SyncResult(
            success=not load_info.has_failed_jobs,
            rows_synced=load_info.metrics.get("rows_total", 0),
            load_id=load_info.load_id
        )

    async def sync_kobo(
        self,
        source_id: str,
        form_id: str,
        api_token: str
    ) -> SyncResult:
        """Sync KoboToolbox form data to warehouse (future)."""
        from dlt.sources.rest_api import rest_api_source

        kobo_source = rest_api_source({
            "client": {
                "base_url": "https://kf.kobotoolbox.org/api/v2/",
                "auth": {"token": api_token}
            },
            "resources": [
                {
                    "name": f"source_{source_id}",
                    "endpoint": {
                        "path": f"assets/{form_id}/data/",
                        "paginator": "offset"
                    }
                }
            ]
        })

        pipeline = dlt.pipeline(
            pipeline_name=f"source_{source_id}",
            destination=postgres(self.warehouse_url),
            dataset_name=self.schema_name
        )

        load_info = pipeline.run(kobo_source)

        return SyncResult(
            success=not load_info.has_failed_jobs,
            rows_synced=load_info.metrics.get("rows_total", 0),
            load_id=load_info.load_id
        )
```

---

## Transformation Engine (Ibis)

### Recipe to Ibis Converter

```python
# app/services/ibis_transform.py

import ibis
from ibis import _
from typing import Any

class RecipeToIbisConverter:
    """
    Converts transformation recipes to Ibis expressions.

    Ibis compiles to optimized SQL via SQLGlot.
    Battle-tested at Netflix, Voltron Data.
    """

    def __init__(self, connection_url: str, schema_name: str):
        self.con = ibis.postgres.connect(url=connection_url)
        self.schema_name = schema_name

    def convert(self, recipe: dict) -> ibis.Table:
        """Convert recipe JSON to Ibis expression."""
        expr = None

        for step in recipe["steps"]:
            expr = self._apply_step(expr, step)

        return expr

    def _apply_step(self, expr: ibis.Table | None, step: dict) -> ibis.Table:
        """Apply a single transformation step."""
        step_type = step["type"]

        match step_type:
            case "source":
                return self._source(step)
            case "filter":
                return self._filter(expr, step)
            case "join":
                return self._join(expr, step)
            case "group":
                return self._group(expr, step)
            case "select":
                return self._select(expr, step)
            case "sort":
                return self._sort(expr, step)
            case "clean":
                return self._clean(expr, step)
            case "categorize":
                return self._categorize(expr, step)
            case "add_column":
                return self._add_column(expr, step)
            case "distinct":
                return expr.distinct()
            case _:
                raise ValueError(f"Unknown step type: {step_type}")

    def _source(self, step: dict) -> ibis.Table:
        """Load source table."""
        table_name = step["table"]
        return self.con.table(f"{self.schema_name}.{table_name}")

    def _filter(self, expr: ibis.Table, step: dict) -> ibis.Table:
        """Apply filter condition."""
        column = step["column"]
        operator = step["operator"]
        value = step["value"]

        col = expr[column]

        match operator:
            case "equals":
                condition = col == value
            case "not_equals":
                condition = col != value
            case "contains":
                condition = col.lower().contains(value.lower())
            case "starts_with":
                condition = col.lower().startswith(value.lower())
            case "ends_with":
                condition = col.lower().endswith(value.lower())
            case "greater_than":
                condition = col > value
            case "less_than":
                condition = col < value
            case "greater_or_equal":
                condition = col >= value
            case "less_or_equal":
                condition = col <= value
            case "is_null":
                condition = col.isnull()
            case "is_not_null":
                condition = col.notnull()
            case "in":
                condition = col.isin(value)
            case "between":
                condition = col.between(value[0], value[1])
            case _:
                raise ValueError(f"Unknown operator: {operator}")

        return expr.filter(condition)

    def _join(self, expr: ibis.Table, step: dict) -> ibis.Table:
        """Join with another table."""
        right_table = step["with"]
        left_on = step["left_on"]
        right_on = step["right_on"]
        join_type = step.get("join_type", "left")
        columns = step.get("columns", None)  # Columns to bring from right

        right = self.con.table(f"{self.schema_name}.{right_table}")

        # Build join condition
        left_col = expr[left_on]
        right_col = right[right_on]

        match join_type:
            case "left":
                result = expr.left_join(right, left_col == right_col)
            case "inner":
                result = expr.inner_join(right, left_col == right_col)
            case "right":
                result = expr.right_join(right, left_col == right_col)
            case "outer":
                result = expr.outer_join(right, left_col == right_col)

        # Select specific columns if specified
        if columns:
            left_cols = [expr[c] for c in expr.columns]
            right_cols = [right[c].name(f"{right_table}_{c}") for c in columns]
            result = result.select(*left_cols, *right_cols)

        return result

    def _group(self, expr: ibis.Table, step: dict) -> ibis.Table:
        """Group by and aggregate."""
        group_by = step["by"]
        aggregates = step["aggregates"]

        agg_exprs = {}
        for agg in aggregates:
            func = agg["function"]
            column = agg["column"]
            alias = agg["alias"]

            col = expr[column]

            match func:
                case "count":
                    agg_exprs[alias] = col.count()
                case "count_distinct":
                    agg_exprs[alias] = col.nunique()
                case "sum":
                    agg_exprs[alias] = col.sum()
                case "avg" | "average":
                    agg_exprs[alias] = col.mean()
                case "min":
                    agg_exprs[alias] = col.min()
                case "max":
                    agg_exprs[alias] = col.max()
                case _:
                    raise ValueError(f"Unknown aggregate: {func}")

        return expr.group_by(group_by).aggregate(**agg_exprs)

    def _select(self, expr: ibis.Table, step: dict) -> ibis.Table:
        """Select specific columns."""
        columns = step["columns"]
        return expr.select(*columns)

    def _sort(self, expr: ibis.Table, step: dict) -> ibis.Table:
        """Sort by columns."""
        columns = step["columns"]
        order_exprs = []

        for col_spec in columns:
            if isinstance(col_spec, str):
                order_exprs.append(expr[col_spec])
            else:
                col = expr[col_spec["column"]]
                if col_spec.get("descending", False):
                    col = col.desc()
                order_exprs.append(col)

        return expr.order_by(*order_exprs)

    def _clean(self, expr: ibis.Table, step: dict) -> ibis.Table:
        """Apply cleaning operations."""
        columns = step["columns"]
        operations = step["operations"]

        for col_name in columns:
            col = expr[col_name]

            for op in operations:
                match op:
                    case "trim":
                        col = col.strip()
                    case "upper":
                        col = col.upper()
                    case "lower":
                        col = col.lower()
                    case "title":
                        col = col.capitalize()  # Ibis title case
                    case "remove_duplicates":
                        pass  # Handled at table level

            expr = expr.mutate(**{col_name: col})

        if "remove_duplicates" in operations:
            expr = expr.distinct()

        return expr

    def _categorize(self, expr: ibis.Table, step: dict) -> ibis.Table:
        """Create category column based on rules."""
        new_column = step["new_column"]
        source_column = step["source_column"]
        rules = step["rules"]
        default = step.get("default", "Other")

        col = expr[source_column]

        # Build CASE expression
        case_expr = ibis.case()

        for rule in rules:
            operator = rule["operator"]
            value = rule["value"]
            category = rule["category"]

            match operator:
                case "equals":
                    condition = col == value
                case "contains":
                    condition = col.lower().contains(value.lower())
                case "starts_with":
                    condition = col.lower().startswith(value.lower())
                case "greater_than":
                    condition = col > value
                case "less_than":
                    condition = col < value
                case "between":
                    condition = col.between(value[0], value[1])

            case_expr = case_expr.when(condition, category)

        case_expr = case_expr.else_(default).end()

        return expr.mutate(**{new_column: case_expr})

    def _add_column(self, expr: ibis.Table, step: dict) -> ibis.Table:
        """Add calculated column."""
        name = step["name"]
        expression_type = step["expression_type"]

        match expression_type:
            case "math":
                # e.g., {"left": "price", "operator": "*", "right": "quantity"}
                left = expr[step["left"]]
                right = expr[step["right"]] if step["right"] in expr.columns else step["right"]

                match step["operator"]:
                    case "+":
                        result = left + right
                    case "-":
                        result = left - right
                    case "*":
                        result = left * right
                    case "/":
                        result = left / right

            case "concat":
                # e.g., {"columns": ["first_name", "last_name"], "separator": " "}
                cols = [expr[c] for c in step["columns"]]
                sep = step.get("separator", " ")
                result = cols[0]
                for col in cols[1:]:
                    result = result + sep + col

            case "extract":
                # e.g., {"column": "date", "part": "year"}
                col = expr[step["column"]]
                match step["part"]:
                    case "year":
                        result = col.year()
                    case "month":
                        result = col.month()
                    case "day":
                        result = col.day()

        return expr.mutate(**{name: result})

    def to_sql(self, recipe: dict) -> str:
        """Convert recipe to SQL string."""
        expr = self.convert(recipe)
        return ibis.to_sql(expr)

    def preview(self, recipe: dict, limit: int = 100, offset: int = 0) -> dict:
        """Execute preview query with pagination."""
        expr = self.convert(recipe)
        expr = expr.limit(limit, offset=offset)

        df = expr.execute()

        return {
            "columns": list(df.columns),
            "rows": df.to_dict(orient="records"),
            "total_count": self._get_count(recipe)
        }

    def execute(self, recipe: dict, output_table: str) -> dict:
        """Execute transformation and save to table."""
        expr = self.convert(recipe)
        sql = ibis.to_sql(expr)

        # Create table
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.schema_name}.{output_table} AS
            {sql}
        """

        self.con.raw_sql(create_sql)

        # Get row count
        count_result = self.con.raw_sql(
            f"SELECT COUNT(*) FROM {self.schema_name}.{output_table}"
        ).fetchone()

        return {
            "table": output_table,
            "row_count": count_result[0],
            "sql": sql
        }

    def _get_count(self, recipe: dict) -> int:
        """Get total row count for pagination."""
        expr = self.convert(recipe)
        return expr.count().execute()
```

---

## Pipeline Scheduling

### Pipeline Execution Model

```python
# app/services/pipeline.py

from datetime import datetime, time
from enum import Enum

class PipelineFrequency(str, Enum):
    MANUAL = "manual"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"

class PipelineService:
    """
    Manages pipeline execution.

    Pipeline = Sources + Transformations + Schedule
    """

    async def run_pipeline(self, pipeline_id: str) -> PipelineRunResult:
        """
        Execute a complete pipeline.

        Order:
        1. Sync all sources (parallel)
        2. Run transformations in dependency order
        """
        pipeline = await self.get_pipeline(pipeline_id)
        run_id = str(uuid.uuid4())

        # Start run tracking
        await self.start_run(run_id, pipeline_id)

        try:
            # Step 1: Sync all sources in parallel
            sync_tasks = [
                self.sync_source(source_id)
                for source_id in pipeline.source_ids
            ]
            sync_results = await asyncio.gather(*sync_tasks, return_exceptions=True)

            # Check for sync failures
            failed_syncs = [r for r in sync_results if isinstance(r, Exception)]
            if failed_syncs:
                await self.fail_run(run_id, f"Sync failed: {failed_syncs[0]}")
                return PipelineRunResult(success=False, error=str(failed_syncs[0]))

            # Step 2: Run transformations in order
            for transform_id in pipeline.transformation_ids:
                result = await self.run_transformation(transform_id)
                if not result.success:
                    await self.fail_run(run_id, f"Transform failed: {result.error}")
                    return PipelineRunResult(success=False, error=result.error)

            # Success
            await self.complete_run(run_id)
            return PipelineRunResult(success=True)

        except Exception as e:
            await self.fail_run(run_id, str(e))
            return PipelineRunResult(success=False, error=str(e))

    async def schedule_pipeline(
        self,
        pipeline_id: str,
        frequency: PipelineFrequency,
        run_at: time | None = None,
        day_of_week: int | None = None
    ):
        """
        Schedule a pipeline for automatic execution.

        Examples:
        - Daily at 6:00 AM: frequency=daily, run_at=06:00
        - Weekly on Monday: frequency=weekly, run_at=06:00, day_of_week=0
        """
        schedule = Schedule(
            pipeline_id=pipeline_id,
            frequency=frequency,
            run_at_time=run_at,
            run_at_day=day_of_week,
            next_run_at=self._calculate_next_run(frequency, run_at, day_of_week)
        )

        await self.save_schedule(schedule)
```

---

## API Design

### REST API Endpoints

```yaml
# Sources
/api/v1/sources:
  GET:
    summary: List all sources for org
    response: Source[]

  POST:
    summary: Add new source
    body:
      type: "csv" | "google_sheets" | "kobo"
      name: string
      config: object
    response: Source

/api/v1/sources/{id}/sync:
  POST:
    summary: Trigger source sync
    response: SyncResult

# Transformations
/api/v1/transformations:
  GET:
    summary: List all transformations
    response: Transformation[]

  POST:
    summary: Create transformation
    body:
      name: string
      recipe: Recipe
    response: Transformation

/api/v1/transformations/{id}:
  PUT:
    summary: Update transformation recipe
    body: Recipe
    response: Transformation

/api/v1/transformations/{id}/preview:
  POST:
    summary: Preview transformation results
    body:
      recipe: Recipe
      limit: number
      offset: number
    response: PreviewResult

/api/v1/transformations/{id}/execute:
  POST:
    summary: Execute and save transformation
    body:
      output_table_name: string
    response: ExecuteResult

# Pipelines
/api/v1/pipelines:
  GET:
    summary: List all pipelines
    response: Pipeline[]

  POST:
    summary: Create pipeline
    body:
      name: string
      source_ids: string[]
      transformation_ids: string[]
    response: Pipeline

/api/v1/pipelines/{id}/run:
  POST:
    summary: Run pipeline manually
    response: PipelineRunResult

/api/v1/pipelines/{id}/schedule:
  PUT:
    summary: Set pipeline schedule
    body:
      frequency: "manual" | "hourly" | "daily" | "weekly"
      run_at: string (HH:MM)
      day_of_week: number (0-6)
    response: Schedule

# Warehouse
/api/v1/warehouse/tables:
  GET:
    summary: List all tables (sources + transforms)
    response: WarehouseTable[]

/api/v1/warehouse/tables/{name}/preview:
  GET:
    summary: Preview table data with pagination
    query:
      limit: number
      offset: number
    response: PreviewResult
```

### Response Types

```typescript
// Types for API responses

interface Source {
  id: string;
  name: string;
  source_type: "csv" | "google_sheets" | "kobo";
  config: object;
  warehouse_table_name: string;
  column_count: number;
  row_count: number;
  last_synced_at: string | null;
  created_at: string;
}

interface Transformation {
  id: string;
  name: string;
  description: string | null;
  recipe: Recipe;
  output_table_name: string | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
}

interface Recipe {
  steps: Step[];
}

interface Step {
  type: "source" | "filter" | "join" | "group" | "select" | "sort" | "clean" | "categorize" | "add_column";
  // Step-specific config...
}

interface Pipeline {
  id: string;
  name: string;
  source_ids: string[];
  transformation_ids: string[];
  schedule: Schedule | null;
  last_run_at: string | null;
  created_at: string;
}

interface Schedule {
  frequency: "manual" | "hourly" | "daily" | "weekly";
  run_at_time: string | null;  // HH:MM
  run_at_day: number | null;   // 0-6 for weekly
  next_run_at: string;
  is_active: boolean;
}

interface PreviewResult {
  columns: string[];
  rows: Record<string, any>[];
  total_count: number;
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
│  1. User logs in with email/password                                    │
│     └──▶ Backend validates credentials                                  │
│     └──▶ Issues JWT (access + refresh tokens)                           │
│                                                                         │
│  2. Frontend stores tokens                                              │
│     └──▶ Access token in memory                                         │
│     └──▶ Refresh token in httpOnly cookie                               │
│                                                                         │
│  3. API requests include Authorization header                           │
│     └──▶ Bearer token validated on each request                         │
│     └──▶ User and org context extracted                                 │
│                                                                         │
│  4. Token refresh                                                       │
│     └──▶ Access token expires (15 min)                                  │
│     └──▶ Refresh token used to get new access token                     │
│     └──▶ Refresh token rotated on each use                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Isolation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MULTI-TENANT DATA ISOLATION                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SCHEMA-BASED ISOLATION:                                                │
│  ───────────────────────                                                │
│                                                                         │
│  Supabase Database                                                      │
│  ├── public (metadata)                                                  │
│  │   ├── organizations                                                  │
│  │   ├── users                                                          │
│  │   ├── sources (FK to org)                                            │
│  │   └── transformations (FK to org)                                    │
│  │                                                                      │
│  ├── org_abc123 (Org A's data)                                          │
│  │   ├── source_xxx                                                     │
│  │   ├── source_yyy                                                     │
│  │   └── transform_zzz                                                  │
│  │                                                                      │
│  └── org_def456 (Org B's data)                                          │
│      ├── source_aaa                                                     │
│      └── transform_bbb                                                  │
│                                                                         │
│  ENFORCEMENT:                                                           │
│  • All queries include org_id from JWT                                  │
│  • Schema name derived from org_id                                      │
│  • Row-level security on metadata tables                                │
│  • No cross-org data access possible                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
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
│  │   │  • DLT ingestion                                          │ │   │
│  │   │  • Ibis transformations                                   │ │   │
│  │   │  • Pipeline scheduling                                    │ │   │
│  │   └──────────────────────────────────────────────────────────┘ │   │
│  │                              │                                   │   │
│  └──────────────────────────────┼───────────────────────────────────┘   │
│                                 │                                       │
│              ┌──────────────────┼──────────────────┐                   │
│              │                  │                  │                   │
│              ▼                  ▼                  ▼                   │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────────┐     │
│  │   Supabase     │  │  Google APIs    │  │     Upstash         │     │
│  │                │  │                 │  │     (Redis)         │     │
│  │  • PostgreSQL  │  │  • Sheets API   │  │                     │     │
│  │  • Metadata    │  │  • Drive API    │  │  • Task queues      │     │
│  │  • Raw data    │  │                 │  │  • Rate limiting    │     │
│  │  • Transforms  │  │                 │  │                     │     │
│  └────────────────┘  └─────────────────┘  └─────────────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Environment Variables

```bash
# Backend (.env)

# Supabase (single warehouse for everything)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
SUPABASE_DB_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres

# Google (for Sheets integration)
GOOGLE_CREDENTIALS_JSON='{"type": "service_account", ...}'

# Auth
JWT_SECRET_KEY=xxx
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption (for stored credentials)
ENCRYPTION_KEY=xxx

# Redis (optional, for background tasks)
REDIS_URL=redis://xxx
```

---

## Appendix: Key Design Patterns

### 1. Recipe Pattern
All transformations stored as declarative JSON recipes, not code.

### 2. Ibis Compilation
Recipe → Ibis Expression → SQL (via SQLGlot)

### 3. Server-Side Pagination
Never load full datasets to browser. AG Grid fetches pages on demand.

### 4. Pipeline Execution
Atomic pipeline runs: all sources sync, then all transforms run in order.

### 5. Schema Isolation
Each org gets its own PostgreSQL schema for data isolation.

---

*Document maintained by: Dalgo Lite Architecture Team*
*Last updated: February 2026*
