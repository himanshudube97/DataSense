# Dalgo Lite - Implementation Phases

> **Last Updated:** 2026-02-01
> **Status:** Phases 1-6 Completed, Phase 7 In Progress
> **Architecture:** DLT + Ibis + Supabase

---

## Architecture Overview

### Key Technology Decisions

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Ingestion** | DLT (Data Load Tool) | Lightweight Python lib, handles pagination, retries, schema inference |
| **Transformation** | Ibis + SQLGlot | Battle-tested at Netflix, compiles Python to SQL |
| **Warehouse** | Supabase PostgreSQL | Single database for metadata + raw data + transforms |
| **Preview Grid** | AG Grid Community | Server-side pagination, handles millions of rows |
| **Frontend** | Next.js 15 + React Flow | Modern React with visual pipeline builder |

### Data Flow

```
Sources (Google Sheets, CSV, Kobo)
    ↓ DLT
Supabase (org_{id}.source_{name})
    ↓ Ibis
Supabase (org_{id}.transform_{name})
    ↓
AG Grid Preview / Export
```

---

## Authentication & Multi-tenancy Design

### Current Model (V1 - Admin Controlled)

```
┌─────────────────────────────────────────────────────────────┐
│  SUPER ADMIN (Dalgo Team)                                   │
│         │                                                   │
│         ▼                                                   │
│  Creates Organization (NGO)                                 │
│         │                                                   │
│         ▼                                                   │
│  Invites NGO Admin (email invite)                           │
│         │                                                   │
│         ▼                                                   │
│  NGO Admin signs up via invite link                         │
│         │                                                   │
│         ▼                                                   │
│  NGO Admin invites team members                             │
└─────────────────────────────────────────────────────────────┘
```

### Role Hierarchy

| Level | Role | Permissions |
|-------|------|-------------|
| Platform | `superadmin` | Create orgs, manage all users, system settings |
| Org | `owner` | Full org access, manage members, delete org |
| Org | `admin` | Manage sources, transforms, invite members |
| Org | `member` | Create/edit own transforms, view sources |
| Org | `viewer` | Read-only access (future) |

---

## Progress Overview

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 1 | Database Design | Completed | 100% |
| 2 | Backend Foundation | Completed | 100% |
| 3 | Google Sheets Integration | Completed | 100% |
| 4 | Data Ingestion (Current) | Completed | 100% |
| 5 | Frontend Foundation | Completed | 100% |
| 6 | Pipeline Canvas | Completed | 100% |
| 7 | DLT Integration | Not Started | 0% |
| 8 | Ibis Transformation Engine | Not Started | 0% |
| 9 | Transformation UI | Not Started | 0% |
| 10 | Pipeline Scheduling | Not Started | 0% |
| 11 | Polish & Production | Not Started | 0% |

---

## Phase 1: Database Design (PostgreSQL/Supabase) - COMPLETED

**Goal:** Design a scalable, extensible database schema.

### Completed Tasks

- [x] Core Entity Tables (organizations, users, organization_members)
- [x] Authentication Tables (invitations, refresh_tokens, password_reset_tokens)
- [x] Source Management Tables (sources, source_schemas, sync_runs)
- [x] Warehouse Tables (warehouse_connections, warehouse_tables)
- [x] Transformation Tables (transformations, transformation_versions, transformation_runs)
- [x] Output & Scheduling Tables (outputs, schedules)
- [x] System Tables (audit_logs)
- [x] Create migration files
- [x] Seed superadmin user
- [x] Document ERD diagram (docs/05_DATABASE_ERD.md)

---

## Phase 2: Backend Foundation (FastAPI) - COMPLETED

**Goal:** Set up FastAPI backend with authentication.

### Completed Tasks

- [x] Project Setup (pyproject.toml, virtual env)
- [x] FastAPI Application Structure
- [x] Database Layer (SQLAlchemy 2.0 async)
- [x] Authentication System (JWT, bcrypt)
- [x] Authorization & Permissions (RBAC)
- [x] Invitation System
- [x] Core Utilities (config, logging, exceptions)
- [x] Admin APIs (org management)
- [x] API Versioning (/api/v1/)

---

## Phase 3: Google Sheets Integration - COMPLETED

**Goal:** Connect to Google Sheets API.

### Completed Tasks

- [x] Service account auth via GOOGLE_CREDENTIALS_JSON
- [x] Sheets API wrapper (get metadata, fetch data)
- [x] Source Management API (add, list, preview, delete)
- [x] Schema Inference (type detection)

---

## Phase 4: Data Ingestion (Current) - COMPLETED

**Goal:** Load data from sources into Supabase warehouse.

### Completed Tasks

- [x] Supabase warehouse setup
- [x] CSV file upload with schema inference
- [x] Excel file support (.xlsx, .xls)
- [x] Sync to warehouse (batch insert)
- [x] Sync history tracking
- [x] Warehouse API (tables, status)

---

## Phase 5: Frontend Foundation (Next.js) - COMPLETED

**Goal:** Set up Next.js frontend with auth.

### Completed Tasks

- [x] Next.js 15 with App Router
- [x] Tailwind CSS v4
- [x] Authentication UI (login, signup)
- [x] Protected routes
- [x] Layout & Navigation
- [x] State Management (Zustand)
- [x] API client with auth

---

## Phase 6: Pipeline Canvas - COMPLETED

**Goal:** Build visual pipeline view with React Flow.

### Completed Tasks

- [x] React Flow setup
- [x] SourceNode component
- [x] WarehouseNode component
- [x] AddSourceNode component
- [x] AnimatedEdge component
- [x] Source → Warehouse connections
- [x] Add Source Modal (CSV, Google Sheets)
- [x] Sync trigger from node

---

## Phase 7: DLT Integration

**Goal:** Replace current ingestion with DLT for better reliability.

### Tasks

- [ ] **7.1 DLT Setup**
  - [ ] Install dlt package
  - [ ] Configure PostgreSQL destination
  - [ ] Set up org-specific schemas

- [ ] **7.2 DLT Ingestion Service**
  ```python
  # app/services/dlt_ingestion.py

  class DLTIngestionService:
      async def sync_google_sheet(source_id, spreadsheet_id, sheet_name)
      async def sync_csv(source_id, file_path)
      async def sync_kobo(source_id, form_id, api_token)  # Future
  ```

- [ ] **7.3 Update Source Sync API**
  - [ ] Refactor `POST /sources/{id}/sync` to use DLT
  - [ ] Add DLT load metadata tracking
  - [ ] Handle incremental vs full refresh

- [ ] **7.4 Schema Management**
  - [ ] Create org schemas on first source
  - [ ] Table naming: `org_{org_id}.source_{source_id}`
  - [ ] Track DLT metadata columns

**Deliverables:**
- DLT-based ingestion working
- Org-specific PostgreSQL schemas
- Improved error handling and retries

---

## Phase 8: Ibis Transformation Engine

**Goal:** Build recipe-to-SQL engine using Ibis.

### Tasks

- [ ] **8.1 Ibis Setup**
  - [ ] Install ibis-framework with postgres backend
  - [ ] Configure Supabase connection

- [ ] **8.2 Recipe Schema Design**
  ```json
  {
    "steps": [
      { "type": "source", "table": "source_abc123" },
      { "type": "filter", "column": "status", "operator": "equals", "value": "Active" },
      { "type": "group", "by": ["district"], "aggregates": [...] }
    ]
  }
  ```

- [ ] **8.3 Recipe to Ibis Converter**
  ```python
  # app/services/ibis_transform.py

  class RecipeToIbisConverter:
      def convert(recipe: dict) -> ibis.Table
      def to_sql(recipe: dict) -> str
      def preview(recipe: dict, limit: int, offset: int) -> dict
      def execute(recipe: dict, output_table: str) -> dict
  ```

- [ ] **8.4 Supported Step Types**
  - [ ] `source` - Load table
  - [ ] `filter` - WHERE conditions
  - [ ] `join` - LEFT/INNER/RIGHT/OUTER joins
  - [ ] `group` - GROUP BY with aggregations
  - [ ] `select` - Choose columns
  - [ ] `sort` - ORDER BY
  - [ ] `clean` - Trim, case changes
  - [ ] `categorize` - CASE WHEN rules
  - [ ] `add_column` - Calculated columns
  - [ ] `distinct` - Remove duplicates

- [ ] **8.5 Transformation API**
  - [ ] `POST /transformations` - Create
  - [ ] `GET /transformations` - List
  - [ ] `PUT /transformations/{id}` - Update recipe
  - [ ] `POST /transformations/{id}/preview` - Preview with pagination
  - [ ] `POST /transformations/{id}/execute` - Materialize to table

**Deliverables:**
- Recipe to SQL conversion working
- All step types implemented
- Preview and execute endpoints

---

## Phase 9: Transformation UI

**Goal:** Build Excel-like transformation editor.

### Reference: docs/06_TRANSFORMATION_UI.md

### Tasks

- [ ] **9.1 Transformation List Page**
  ```
  /transformations
  ┌─────────────────────────────────────────────────────────────┐
  │  Transformations                         [+ New Transform]  │
  ├─────────────────────────────────────────────────────────────┤
  │  Name            │ Source        │ Last Run    │ Actions    │
  │  ────────────────┼───────────────┼─────────────┼────────────│
  │  Active Donors   │ donations     │ 2 hours ago │ Edit | Run │
  │  Monthly Summary │ beneficiaries │ Yesterday   │ Edit | Run │
  └─────────────────────────────────────────────────────────────┘
  ```

- [ ] **9.2 AG Grid Setup**
  - [ ] Install AG Grid Community
  - [ ] Server-side pagination (100 rows/page)
  - [ ] Column type indicators
  - [ ] Virtual scrolling

- [ ] **9.3 Transformation Editor Layout**
  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │  ← Back    "Monthly Donor Summary"             [Save] [Run ▼]  │
  ├───────────────────┬─────────────────────────────────────────────┤
  │  Applied Steps    │           Data Preview (AG Grid)            │
  │  ─────────────    │  ┌─────┬─────────┬──────────┬────────────┐  │
  │  1. donations     │  │ id  │ donor   │ amount   │ date       │  │
  │  2. Filter        │  ├─────┼─────────┼──────────┼────────────┤  │
  │  3. Combine       │  │ 1   │ Alice   │ $500     │ 2026-01-15 │  │
  │                   │  │ 2   │ Bob     │ $250     │ 2026-01-14 │  │
  │  [+ Add Step]     │  │ ... │ ...     │ ...      │ ...        │  │
  │                   │  └─────┴─────────┴──────────┴────────────┘  │
  ├───────────────────┴─────────────────────────────────────────────┤
  │  [Filter] [Combine] [Summarize] [Clean] [Categorize] [More ▼]  │
  └─────────────────────────────────────────────────────────────────┘
  ```

- [ ] **9.4 Action Modals (Excel Terminology)**

  | Action | SQL Equivalent | Description |
  |--------|---------------|-------------|
  | Filter | WHERE | Keep/remove rows by condition |
  | Combine | JOIN | Merge with another table (like VLOOKUP) |
  | Summarize | GROUP BY | Pivot table style aggregation |
  | Clean | String functions | Trim, case, fill blanks |
  | Categorize | CASE WHEN | Create categories from values |

- [ ] **9.5 Filter Modal**
  ```
  ┌─────────────────────────────────────────────────┐
  │  Filter Rows                              [×]   │
  ├─────────────────────────────────────────────────┤
  │  Column: [status          ▼]                    │
  │  Condition: [equals       ▼]                    │
  │  Value: [Active           ]                     │
  │                                                 │
  │  [+ Add condition]                              │
  │                                                 │
  │              [Cancel]  [Apply Filter]           │
  └─────────────────────────────────────────────────┘
  ```

- [ ] **9.6 Combine Modal (JOIN)**
  ```
  ┌─────────────────────────────────────────────────┐
  │  Combine Tables                           [×]   │
  ├─────────────────────────────────────────────────┤
  │  Combine with: [districts         ▼]            │
  │                                                 │
  │  Match where:                                   │
  │  [district_id ▼] matches [id ▼] in districts    │
  │                                                 │
  │  Columns to bring:                              │
  │  [x] district_name                              │
  │  [x] region                                     │
  │  [ ] population                                 │
  │                                                 │
  │              [Cancel]  [Apply]                  │
  └─────────────────────────────────────────────────┘
  ```

- [ ] **9.7 Summarize Modal (GROUP BY)**
  ```
  ┌─────────────────────────────────────────────────┐
  │  Summarize Data                           [×]   │
  ├─────────────────────────────────────────────────┤
  │  Group by:                                      │
  │  [x] district                                   │
  │  [ ] gender                                     │
  │  [ ] age_group                                  │
  │                                                 │
  │  Calculate:                                     │
  │  [Count     ▼] of [id           ▼] as [total]   │
  │  [Sum       ▼] of [amount       ▼] as [total_$] │
  │  [+ Add calculation]                            │
  │                                                 │
  │              [Cancel]  [Apply]                  │
  └─────────────────────────────────────────────────┘
  ```

- [ ] **9.8 Clean Modal**
  - [ ] Trim whitespace
  - [ ] Change case (upper/lower/title)
  - [ ] Fill empty cells
  - [ ] Remove duplicates

- [ ] **9.9 Categorize Modal**
  - [ ] Rule-based categorization
  - [ ] Default value for unmatched

- [ ] **9.10 Steps Panel**
  - [ ] Show applied steps list
  - [ ] Click to edit step
  - [ ] Drag to reorder
  - [ ] Delete step
  - [ ] Preview updates on each step

**Deliverables:**
- Complete transformation editor
- All action modals working
- Real-time preview updates
- Recipe JSON construction

---

## Phase 10: Pipeline Scheduling

**Goal:** Implement pipeline execution and scheduling.

### Tasks

- [ ] **10.1 Pipeline Model**
  ```python
  Pipeline:
      - name: str
      - source_ids: list[str]
      - transformation_ids: list[str]
      - schedule: Schedule (optional)
  ```

- [ ] **10.2 Pipeline Service**
  ```python
  class PipelineService:
      async def run_pipeline(pipeline_id: str)
          # 1. Sync all sources (parallel)
          # 2. Run transformations in order
          # 3. Track run status

      async def schedule_pipeline(pipeline_id, frequency, run_at)
  ```

- [ ] **10.3 Pipeline API**
  - [ ] `POST /pipelines` - Create pipeline
  - [ ] `GET /pipelines` - List pipelines
  - [ ] `POST /pipelines/{id}/run` - Manual run
  - [ ] `PUT /pipelines/{id}/schedule` - Set schedule

- [ ] **10.4 Background Task Runner**
  - [ ] Use APScheduler or Celery for scheduling
  - [ ] Handle failures and retries
  - [ ] Send notifications on completion/failure

- [ ] **10.5 Pipeline UI**
  - [ ] Pipeline list view
  - [ ] Create pipeline wizard
  - [ ] Schedule configuration
  - [ ] Run history

**Deliverables:**
- Pipeline execution working
- Scheduling system functional
- Run history tracking

---

## Phase 11: Polish & Production

**Goal:** Prepare for production deployment.

### Tasks

- [ ] **11.1 Error Handling**
  - [ ] User-friendly error messages
  - [ ] Retry logic for transient failures
  - [ ] Graceful degradation

- [ ] **11.2 Testing**
  - [ ] Backend unit tests (pytest)
  - [ ] Recipe to SQL conversion tests
  - [ ] Frontend component tests
  - [ ] E2E tests (Playwright)

- [ ] **11.3 Performance**
  - [ ] Query optimization
  - [ ] Frontend bundle optimization
  - [ ] Lazy loading for large lists

- [ ] **11.4 Documentation**
  - [ ] User guide (for NGO users)
  - [ ] API documentation
  - [ ] Deployment guide

- [ ] **11.5 Deployment**
  - [ ] Backend on Railway/Render
  - [ ] Frontend on Vercel
  - [ ] Environment configuration
  - [ ] CI/CD pipeline (GitHub Actions)

- [ ] **11.6 Monitoring**
  - [ ] Error tracking (Sentry)
  - [ ] Basic analytics
  - [ ] Health checks

**Deliverables:**
- Production-ready application
- Deployed and accessible
- Documentation complete

---

## Session Log

### Session 1 - 2026-02-01
- Created implementation phases document
- Discussed authentication and multi-tenancy design
- Completed Phase 1: Database Design
- Next: Phase 2 - Backend Foundation

### Session 2 - 2026-02-01
- Completed Phase 2: Backend Foundation (FastAPI, JWT auth, RBAC)
- Completed Phase 4: Data Ingestion (Supabase warehouse)
- Completed Phase 6: Frontend Foundation (Next.js, auth flow)
- In Progress: Phase 3 (Google Sheets) & Phase 7 (Canvas)

### Session 3 - 2026-02-01
- Completed Phase 3: Google Sheets Integration
- Added Excel file support (.xlsx, .xls)
- Frontend modal for Google Sheets connection

### Session 4 - 2026-02-01
- Architecture redesign: DLT + Ibis + Supabase
- Updated documentation:
  - docs/02_TECH_STACK.md - Complete rewrite with DLT, Ibis
  - docs/03_ARCHITECTURE.md - Updated with new architecture
  - docs/04_IMPLEMENTATION_PHASES.md - Reorganized phases
  - docs/06_TRANSFORMATION_UI.md - Created UI/UX specifications
- Key decisions:
  - DLT for ingestion (replaces custom Google Sheets code)
  - Ibis for transformations (replaces custom SQL generator)
  - AG Grid with server-side pagination (never load all data)
  - Pipeline-based scheduling (sync all sources, then transforms)
  - Excel terminology in UI (Filter, Combine=JOIN, Summarize=GROUP BY)

---

## Notes & Decisions

### Architecture (Updated)
- **Ingestion:** DLT handles Google Sheets, CSV, KoboToolbox
- **Transformation:** Ibis compiles to SQL, proven at Netflix scale
- **Warehouse:** Supabase PostgreSQL (single database)
- **UI Pattern:** Power Query-style "Applied Steps" panel

### Key Design Patterns
1. **Recipe Pattern** - JSON recipes, not code
2. **Ibis Compilation** - Recipe → Ibis → SQL
3. **Server-Side Pagination** - Never load full datasets
4. **Pipeline Execution** - Atomic: sync all, then transform all
5. **Schema Isolation** - Each org gets own PostgreSQL schema

### Excel → SQL Terminology Mapping
| Excel Term | SQL Equivalent |
|------------|---------------|
| Filter | WHERE |
| Combine (VLOOKUP) | JOIN |
| Summarize (Pivot) | GROUP BY |
| Clean | TRIM, UPPER, LOWER |
| Categorize (IF) | CASE WHEN |

### Tech Stack Locked
- Backend: FastAPI + SQLAlchemy 2.0 + DLT + Ibis
- Frontend: Next.js 15 + TypeScript + Tailwind v4 + AG Grid
- Database: Supabase PostgreSQL (single warehouse)
- Auth: Custom JWT (python-jose + bcrypt)
