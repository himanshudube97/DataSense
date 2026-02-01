# Dalgo Lite: Technology Stack

**Version:** 2.0
**Date:** February 2026
**Status:** Approved

---

## Table of Contents

1. [Stack Overview](#stack-overview)
2. [Frontend](#frontend)
3. [Backend](#backend)
4. [Ingestion Layer (DLT)](#ingestion-layer-dlt)
5. [Transformation Layer (Ibis)](#transformation-layer-ibis)
6. [Database & Warehouse](#database--warehouse)
7. [Authentication](#authentication)
8. [Infrastructure](#infrastructure)
9. [Development Tools](#development-tools)

---

## Stack Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
│                     Next.js 15 (App Router)                                 │
│         TypeScript • Tailwind CSS • Zustand • AG Grid • React Flow          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST API
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
│                      Python 3.12 + FastAPI                                  │
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐                        │
│  │   INGESTION (DLT)   │    │ TRANSFORMATION (Ibis)│                        │
│  │                     │    │                     │                        │
│  │ • Google Sheets     │    │ • Recipe → Ibis     │                        │
│  │ • KoboToolbox       │    │ • Ibis → SQLGlot    │                        │
│  │ • CommCare          │    │ • SQLGlot → SQL     │                        │
│  │ • CSV/Excel         │    │ • Execute on PG     │                        │
│  └─────────────────────┘    └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPABASE (PostgreSQL)                                │
│                                                                             │
│  • Metadata (users, orgs, transformations)                                  │
│  • Raw data tables (from DLT ingestion)                                     │
│  • Transformed data tables (from Ibis execution)                            │
│  • Authentication & Row Level Security                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Technology Decisions

| Component | Technology | Why |
|-----------|------------|-----|
| **Ingestion** | DLT (Data Load Tool) | Lightweight, Python-native, handles pagination/retries |
| **Transformation** | Ibis + SQLGlot | Battle-tested SQL generation, 20+ backends |
| **Data Grid** | AG Grid | Excel-like UI, handles millions of rows |
| **Warehouse** | Supabase (PostgreSQL) | Single database for everything, simpler ops |
| **Pipeline Canvas** | React Flow | Node-based diagrams, drag-and-drop |

---

## Frontend

### Framework: Next.js 15

```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.3.0"
  }
}
```

### UI Libraries

| Library | Purpose | Why |
|---------|---------|-----|
| **AG Grid Community** | Spreadsheet-like data grid | Free, handles millions of rows with server-side pagination |
| **React Flow** | Pipeline visualization | Node-based diagrams, drag-and-drop |
| **React Query Builder** | Filter condition builder | SQL export built-in |
| **Radix UI** | Accessible UI primitives | Unstyled, composable |
| **Tailwind CSS v4** | Styling | Rapid development, consistent design |
| **Zustand** | State management | Lightweight, simple API |
| **SWR** | Data fetching | Stale-while-revalidate, caching |

```json
{
  "dependencies": {
    "ag-grid-react": "^32.0.0",
    "ag-grid-community": "^32.0.0",
    "@xyflow/react": "^12.0.0",
    "react-querybuilder": "^7.0.0",
    "@radix-ui/react-dialog": "^1.0.0",
    "@radix-ui/react-dropdown-menu": "^2.0.0",
    "@radix-ui/react-select": "^2.0.0",
    "tailwindcss": "^4.0.0",
    "zustand": "^5.0.0",
    "swr": "^2.2.0",
    "lucide-react": "^0.300.0",
    "sonner": "^1.0.0"
  }
}
```

### Frontend Project Structure

```
frontend/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── (auth)/               # Public auth pages
│   │   │   ├── login/
│   │   │   └── signup/
│   │   ├── (dashboard)/          # Protected pages
│   │   │   ├── pipeline/         # Pipeline view
│   │   │   ├── transformations/  # Transformation list & editor
│   │   │   └── settings/
│   │   └── layout.tsx
│   │
│   ├── components/
│   │   ├── ui/                   # Base UI components
│   │   ├── pipeline/             # Pipeline canvas components
│   │   │   ├── PipelineCanvas.tsx
│   │   │   ├── SourceNode.tsx
│   │   │   └── TransformNode.tsx
│   │   ├── transformation/       # Transformation editor
│   │   │   ├── TransformationEditor.tsx
│   │   │   ├── DataGrid.tsx      # AG Grid wrapper
│   │   │   ├── StepsPanel.tsx    # Applied steps
│   │   │   └── modals/           # Action modals
│   │   │       ├── FilterModal.tsx
│   │   │       ├── CombineModal.tsx
│   │   │       ├── SummarizeModal.tsx
│   │   │       └── CleanModal.tsx
│   │   └── common/
│   │
│   ├── hooks/
│   │   ├── useTransformation.ts
│   │   ├── usePipeline.ts
│   │   └── useDataPreview.ts
│   │
│   ├── stores/
│   │   ├── authStore.ts
│   │   ├── pipelineStore.ts
│   │   └── transformationStore.ts
│   │
│   └── lib/
│       ├── api.ts                # API client
│       └── utils.ts
```

---

## Backend

### Framework: FastAPI + Python 3.12

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
httpx>=0.26.0
```

### Backend Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/v1/
│   │   ├── auth.py
│   │   ├── organizations.py
│   │   ├── sources.py
│   │   ├── pipelines.py
│   │   └── transformations.py
│   │
│   ├── models/                   # SQLAlchemy models
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── source.py
│   │   ├── pipeline.py
│   │   └── transformation.py
│   │
│   ├── schemas/                  # Pydantic schemas
│   │   ├── source.py
│   │   ├── pipeline.py
│   │   └── transformation.py
│   │
│   └── services/
│       ├── ingestion/            # DLT integration
│       │   ├── dlt_service.py
│       │   ├── google_sheets.py
│       │   ├── kobo.py
│       │   └── commcare.py
│       │
│       ├── transformation/       # Ibis integration
│       │   ├── recipe_executor.py
│       │   ├── ibis_converter.py
│       │   └── preview_service.py
│       │
│       └── pipeline/
│           ├── pipeline_runner.py
│           └── scheduler.py
```

---

## Ingestion Layer (DLT)

### Why DLT?

| Feature | Custom Code | DLT |
|---------|-------------|-----|
| Pagination | Write yourself | Built-in |
| Rate limiting | Write yourself | Built-in |
| Retries | Write yourself | Built-in |
| Schema inference | Write yourself | Built-in |
| Incremental loads | Write yourself | One flag |

### DLT Dependencies

```
dlt[postgres]>=0.4.0
```

### DLT Source Configuration

```python
# services/ingestion/dlt_service.py
import dlt
from dlt.sources.rest_api import rest_api_source
from dlt.sources.google_sheets import google_spreadsheet

class DLTIngestionService:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.pipeline = dlt.pipeline(
            pipeline_name="dalgo_ingestion",
            destination="postgres",
            dataset_name="raw_data",
            credentials={"connection_string": f"{supabase_url}?apikey={supabase_key}"}
        )

    def sync_google_sheets(self, spreadsheet_id: str, sheet_names: list[str]):
        source = google_spreadsheet(
            spreadsheet_id=spreadsheet_id,
            sheet_names=sheet_names
        )
        return self.pipeline.run(source)

    def sync_kobo(self, api_key: str, form_ids: list[str]):
        source = rest_api_source({
            "client": {
                "base_url": "https://kf.kobotoolbox.org/api/v2/",
                "auth": {"type": "api_key", "api_key": api_key}
            },
            "resources": [
                {"name": f"form_{fid}", "endpoint": f"assets/{fid}/data"}
                for fid in form_ids
            ]
        })
        return self.pipeline.run(source)
```

---

## Transformation Layer (Ibis)

### Why Ibis + SQLGlot?

| Feature | Custom SQL Generator | Ibis |
|---------|---------------------|------|
| SQL injection protection | You handle | Built-in |
| Dialect handling | You handle | 31 dialects |
| Edge cases (NULL, types) | You discover in prod | Already fixed |
| Testing | You write | Community tested |
| Backend flexibility | Locked to one DB | 20+ backends |

### Ibis Dependencies

```
ibis-framework[postgres]>=8.0.0
sqlglot>=20.0.0
```

### Recipe to Ibis Converter

```python
# services/transformation/ibis_converter.py
import ibis
from ibis import _

class RecipeToIbisConverter:
    def __init__(self, connection_url: str):
        self.con = ibis.postgres.connect(url=connection_url)

    def convert(self, recipe: dict) -> ibis.Table:
        """Convert recipe JSON to Ibis expression."""
        expr = None

        for step in recipe["steps"]:
            expr = self._apply_step(expr, step)

        return expr

    def _apply_step(self, expr, step: dict):
        step_type = step["type"]

        if step_type == "source":
            return self.con.table(step["table"])

        elif step_type == "filter":
            return self._apply_filter(expr, step)

        elif step_type == "select":
            return expr.select(*step["columns"])

        elif step_type == "join":
            right = self.con.table(step["with"])
            return expr.left_join(
                right,
                getattr(expr, step["left_on"]) == getattr(right, step["right_on"])
            )

        elif step_type == "group":
            aggs = {}
            for agg in step["aggregates"]:
                col = getattr(expr, agg["column"])
                fn = getattr(col, agg["function"])()
                aggs[agg["alias"]] = fn
            return expr.group_by(*step["by"]).aggregate(**aggs)

        elif step_type == "sort":
            col = getattr(expr, step["column"])
            if step.get("descending"):
                col = col.desc()
            return expr.order_by(col)

        elif step_type == "clean":
            return self._apply_clean(expr, step)

        elif step_type == "categorize":
            return self._apply_categorize(expr, step)

        elif step_type == "distinct":
            return expr.distinct()

        else:
            raise ValueError(f"Unknown step type: {step_type}")

    def _apply_filter(self, expr, step: dict):
        column = getattr(expr, step["column"])
        op = step["operator"]
        value = step["value"]

        ops = {
            "equals": lambda c, v: c == v,
            "not_equals": lambda c, v: c != v,
            "greater_than": lambda c, v: c > v,
            "less_than": lambda c, v: c < v,
            "contains": lambda c, v: c.contains(v),
            "is_null": lambda c, v: c.isnull(),
            "is_not_null": lambda c, v: c.notnull(),
            "in": lambda c, v: c.isin(v),
        }

        condition = ops[op](column, value)
        return expr.filter(condition)

    def _apply_clean(self, expr, step: dict):
        mutations = {}
        for col in step["columns"]:
            column = getattr(expr, col)
            for op in step["operations"]:
                if op == "trim":
                    column = column.strip()
                elif op == "upper":
                    column = column.upper()
                elif op == "lower":
                    column = column.lower()
                elif op == "capitalize":
                    column = column.capitalize()
            mutations[col] = column
        return expr.mutate(**mutations)

    def _apply_categorize(self, expr, step: dict):
        case_expr = ibis.case()
        for rule in step["rules"]:
            col = getattr(expr, rule["column"])
            condition = self._build_condition(col, rule)
            case_expr = case_expr.when(condition, rule["value"])
        case_expr = case_expr.else_(step.get("default")).end()
        return expr.mutate(**{step["name"]: case_expr})
```

### Preview Service with Pagination

```python
# services/transformation/preview_service.py
class PreviewService:
    def __init__(self, converter: RecipeToIbisConverter):
        self.converter = converter

    async def preview(
        self,
        recipe: dict,
        page: int = 1,
        page_size: int = 100
    ) -> dict:
        expr = self.converter.convert(recipe)

        # Get total count
        total = expr.count().execute()

        # Apply pagination
        offset = (page - 1) * page_size
        paginated = expr.limit(page_size, offset=offset)

        # Execute and return
        rows = paginated.execute().to_dict('records')

        return {
            "rows": rows,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    def to_sql(self, recipe: dict) -> str:
        """Generate SQL for debugging/advanced users."""
        expr = self.converter.convert(recipe)
        return ibis.to_sql(expr)

    async def execute_and_save(self, recipe: dict, output_table: str):
        """Execute transformation and save as table."""
        expr = self.converter.convert(recipe)
        sql = ibis.to_sql(expr)

        # Create table from query
        create_sql = f"CREATE TABLE {output_table} AS {sql}"
        await self.converter.con.raw_sql(create_sql)

        return {"table": output_table, "rows": expr.count().execute()}
```

---

## Database & Warehouse

### Supabase (PostgreSQL)

**Single database for everything:**

| Data Type | Schema | Purpose |
|-----------|--------|---------|
| Metadata | `public` | Users, orgs, pipelines, transformations |
| Raw data | `raw_data` | Tables from DLT ingestion |
| Transformed | `transformed` | Output tables from Ibis |

### Key Tables

```sql
-- Pipelines
CREATE TABLE pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name TEXT NOT NULL,
    description TEXT,
    schedule TEXT DEFAULT 'manual',  -- 'manual', 'hourly', 'daily'
    last_run_at TIMESTAMPTZ,
    status TEXT DEFAULT 'idle',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sources (linked to pipeline)
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID REFERENCES pipelines(id),
    organization_id UUID REFERENCES organizations(id),
    name TEXT NOT NULL,
    source_type TEXT NOT NULL,  -- 'google_sheets', 'kobo', 'commcare', 'csv'
    config JSONB NOT NULL,
    warehouse_table TEXT,
    last_synced_at TIMESTAMPTZ,
    row_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transformations
CREATE TABLE transformations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID REFERENCES pipelines(id),
    organization_id UUID REFERENCES organizations(id),
    name TEXT NOT NULL,
    description TEXT,
    recipe JSONB NOT NULL,
    output_table TEXT,
    depends_on TEXT[],  -- Source tables this transform needs
    run_order INTEGER,
    last_run_at TIMESTAMPTZ,
    row_count INTEGER,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Authentication

### JWT-based with Supabase

- Email/password authentication
- Invitation-based signup for organizations
- JWT tokens with refresh
- Role-based access control (owner, admin, member)

---

## Infrastructure

### Development

```
Frontend:  npm run dev        → localhost:3000
Backend:   uvicorn app:main   → localhost:8000
Database:  Supabase Local     → localhost:54321
```

### Production

| Component | Service | Cost |
|-----------|---------|------|
| Frontend | Vercel | Free |
| Backend | Railway/Render | $0-20/mo |
| Database | Supabase | Free tier |

---

## Version Summary

| Component | Version |
|-----------|---------|
| Node.js | 20 LTS |
| Python | 3.12 |
| Next.js | 15.x |
| FastAPI | 0.109+ |
| DLT | 0.4+ |
| Ibis | 8.0+ |
| PostgreSQL | 15+ (Supabase) |
| AG Grid | 32.x (Community) |

---

*Document maintained by: Dalgo Lite Engineering Team*
*Last updated: February 2026*
