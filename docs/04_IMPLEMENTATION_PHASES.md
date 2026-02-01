# Dalgo Lite - Implementation Phases

> **Last Updated:** 2026-02-01
> **Status:** Phase 1 - Completed

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

### Future Model (V2 - Self Signup)

```
┌─────────────────────────────────────────────────────────────┐
│  User signs up → Auto-creates Personal Workspace            │
│         │                                                   │
│         ▼                                                   │
│  Personal workspace (limited, 90-day inactive cleanup)      │
│         │                                                   │
│         ▼                                                   │
│  Create Team Org (requires inviting 1+ member)              │
│         OR                                                  │
│  Join existing org via invite                               │
└─────────────────────────────────────────────────────────────┘
```

### Authentication Method
- **Type:** Username (email) + Password
- **Token:** JWT with refresh tokens
- **Password:** Hashed with bcrypt

### Role Hierarchy

| Level | Role | Permissions |
|-------|------|-------------|
| Platform | `superadmin` | Create orgs, manage all users, system settings |
| Org | `owner` | Full org access, manage members, delete org |
| Org | `admin` | Manage sources, transforms, invite members |
| Org | `member` | Create/edit own transforms, view sources |
| Org | `viewer` | Read-only access (future) |

### Multi-tenancy
- Every resource belongs to an organization
- Users can belong to multiple organizations
- API requests scoped to current organization (via header/context)
- Row-level security enforced at database level

---

## Progress Overview

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 1 | Database Design | Completed | 100% |
| 2 | Backend Foundation | Not Started | 0% |
| 3 | Google Sheets Integration | Not Started | 0% |
| 4 | Data Ingestion Engine | Not Started | 0% |
| 5 | Transformation Engine Core | Not Started | 0% |
| 6 | Frontend Foundation | Not Started | 0% |
| 7 | Transformation Canvas UI | Not Started | 0% |
| 8 | Preview & Execution | Not Started | 0% |
| 9 | Core Transformations | Not Started | 0% |
| 10 | Polish & Production Ready | Not Started | 0% |

---

## Phase 1: Database Design (PostgreSQL/Supabase)

**Goal:** Design a scalable, extensible database schema that supports future features without breaking changes.

**Principles:**
- Use UUIDs for all primary keys (distributed-friendly)
- Soft deletes with `deleted_at` timestamps
- Audit columns on all tables (`created_at`, `updated_at`)
- JSONB for flexible metadata/configuration
- Foreign keys with proper cascading
- Indexes on frequently queried columns

### Tasks

- [x] **1.1 Core Entity Tables**
  - [x] `organizations` - Multi-tenant root entity (name, slug, type, settings)
  - [x] `users` - User accounts (email, password_hash, is_superadmin)
  - [x] `organization_members` - User-org membership with roles (user_id, org_id, role)

- [x] **1.2 Authentication Tables**
  - [x] `invitations` - Pending invites (email, org_id, role, token, expires_at)
  - [x] `refresh_tokens` - JWT refresh token storage (user_id, token_hash, expires_at)
  - [x] `password_reset_tokens` - Password reset flow (user_id, token_hash, expires_at)

- [x] **1.3 Source Management Tables**
  - [x] `sources` - Data source registry (Google Sheets, future: CSV, API)
  - [x] `source_schemas` - Discovered/inferred column schemas
  - [x] `sync_runs` - History of data sync operations

- [x] **1.4 Warehouse Tables**
  - [x] `warehouse_connections` - MotherDuck connection configs per org
  - [x] `warehouse_tables` - Registry of tables in user's warehouse

- [x] **1.5 Transformation Tables**
  - [x] `transformations` - Transformation definitions
  - [x] `transformation_versions` - Version history of recipes
  - [x] `transformation_runs` - Execution history

- [x] **1.6 Output & Scheduling Tables**
  - [x] `outputs` - Output table definitions
  - [x] `schedules` - Sync/transform schedules (future)

- [x] **1.7 System Tables**
  - [x] `audit_logs` - Action audit trail

- [x] **1.8 Create migration files**
- [x] **1.9 Seed superadmin user**
- [x] **1.10 Document ERD diagram**

**Deliverables:**
- SQL migration files
- ERD diagram (Mermaid in docs)
- Seed data script

---

## Phase 2: Backend Foundation (FastAPI)

**Goal:** Set up a well-structured FastAPI backend with database connectivity, authentication, and core utilities.

### Tasks

- [ ] **2.1 Project Setup**
  - [ ] Initialize Python project with `pyproject.toml`
  - [ ] Set up virtual environment
  - [ ] Configure development tools (ruff, pytest, pre-commit)

- [ ] **2.2 FastAPI Application Structure**
  - [ ] Create app directory structure
  - [ ] Configure FastAPI app with middleware
  - [ ] Set up CORS, error handlers
  - [ ] Health check endpoint

- [ ] **2.3 Database Layer**
  - [ ] SQLAlchemy 2.0 async setup
  - [ ] Supabase/PostgreSQL connection configuration
  - [ ] Base model classes with audit columns
  - [ ] Session management

- [ ] **2.4 Authentication System**
  - [ ] Password hashing (bcrypt)
  - [ ] JWT token generation (access + refresh tokens)
  - [ ] Token verification middleware
  - [ ] `POST /auth/login` - Login with email/password
  - [ ] `POST /auth/refresh` - Refresh access token
  - [ ] `POST /auth/logout` - Invalidate refresh token
  - [ ] `GET /auth/me` - Get current user
  - [ ] Current org context (header or token claim)

- [ ] **2.5 Authorization & Permissions**
  - [ ] Role-based access control (RBAC)
  - [ ] Permission decorators/dependencies
  - [ ] Superadmin checks
  - [ ] Org membership validation

- [ ] **2.6 Invitation System**
  - [ ] `POST /invitations` - Create invitation (superadmin/admin only)
  - [ ] `GET /invitations/{token}` - Validate invitation
  - [ ] `POST /auth/signup` - Sign up via invitation
  - [ ] Email sending (optional, can use console for dev)

- [ ] **2.7 Core Utilities**
  - [ ] Configuration management (pydantic-settings)
  - [ ] Logging setup
  - [ ] Exception classes
  - [ ] Response schemas

- [ ] **2.8 Admin APIs**
  - [ ] `POST /admin/organizations` - Create organization (superadmin)
  - [ ] `GET /admin/organizations` - List all organizations (superadmin)
  - [ ] `GET /organizations/{id}/members` - List org members
  - [ ] `DELETE /organizations/{id}/members/{user_id}` - Remove member

- [ ] **2.9 API Versioning**
  - [ ] Set up `/api/v1/` router structure
  - [ ] OpenAPI documentation configuration

**Deliverables:**
- Running FastAPI server
- Full authentication flow working
- Invitation-based signup working
- Role-based access control implemented
- API documentation at `/docs`

---

## Phase 3: Google Sheets Integration

**Goal:** Connect to Google Sheets API, list sheets, and fetch data.

### Tasks

- [ ] **3.1 Google Cloud Setup**
  - [ ] Create GCP project
  - [ ] Enable Sheets API
  - [ ] Create service account (for development)
  - [ ] Download credentials JSON

- [ ] **3.2 Sheets API Wrapper**
  - [ ] Google Sheets client class
  - [ ] List spreadsheets (from shared with service account)
  - [ ] Get spreadsheet metadata (sheets, names)
  - [ ] Fetch sheet data with pagination

- [ ] **3.3 Source Management API**
  - [ ] `POST /sources` - Add new Google Sheet source
  - [ ] `GET /sources` - List all sources
  - [ ] `GET /sources/{id}` - Get source details
  - [ ] `GET /sources/{id}/preview` - Preview first N rows
  - [ ] `DELETE /sources/{id}` - Remove source

- [ ] **3.4 Schema Inference**
  - [ ] Infer column types from data
  - [ ] Handle mixed types gracefully
  - [ ] Store inferred schema in `source_schemas`

**Deliverables:**
- Working Sheets integration
- Source management endpoints
- Schema inference working

---

## Phase 4: Data Ingestion Engine

**Goal:** Load data from Google Sheets into MotherDuck warehouse.

### Tasks

- [ ] **4.1 MotherDuck Setup**
  - [ ] Create MotherDuck account
  - [ ] Generate access token
  - [ ] Test connection from Python

- [ ] **4.2 MotherDuck Client**
  - [ ] Connection manager class
  - [ ] Execute queries
  - [ ] Create tables from schema
  - [ ] Bulk insert data

- [ ] **4.3 Ingestion Service**
  - [ ] Full sync (replace all data)
  - [ ] Incremental sync (append new rows) - future
  - [ ] Handle schema changes
  - [ ] Track sync runs in database

- [ ] **4.4 Sync API**
  - [ ] `POST /sources/{id}/sync` - Trigger sync
  - [ ] `GET /sources/{id}/sync-status` - Get sync status
  - [ ] `GET /sources/{id}/sync-history` - Sync run history

- [ ] **4.5 Warehouse API**
  - [ ] `GET /warehouse/tables` - List all tables
  - [ ] `GET /warehouse/tables/{name}` - Table details
  - [ ] `GET /warehouse/tables/{name}/preview` - Preview data

**Deliverables:**
- Data flowing from Sheets to MotherDuck
- Sync history tracked
- Warehouse exploration endpoints

---

## Phase 5: Transformation Engine Core

**Goal:** Build the recipe-to-SQL generation engine for basic transformations.

### Tasks

- [ ] **5.1 Recipe Schema Design**
  - [ ] Define JSON schema for transformation recipes
  - [ ] Node types: source, filter, select, sort, output
  - [ ] Edge schema for node connections

- [ ] **5.2 SQL Generator**
  - [ ] Base SQL generator class
  - [ ] CTE-based query building
  - [ ] Filter action → WHERE clause
  - [ ] Select action → SELECT columns
  - [ ] Sort action → ORDER BY

- [ ] **5.3 Transformation Service**
  - [ ] Parse recipe JSON
  - [ ] Validate recipe structure
  - [ ] Generate SQL from recipe
  - [ ] Execute and return results

- [ ] **5.4 Transformation API**
  - [ ] `POST /transformations` - Create transformation
  - [ ] `GET /transformations` - List transformations
  - [ ] `GET /transformations/{id}` - Get transformation details
  - [ ] `PUT /transformations/{id}` - Update transformation
  - [ ] `POST /transformations/{id}/preview` - Preview results
  - [ ] `POST /transformations/{id}/execute` - Execute and save

**Deliverables:**
- Working SQL generation
- Basic transformations functional
- Preview and execute working

---

## Phase 6: Frontend Foundation (Next.js)

**Goal:** Set up Next.js frontend with authentication, basic layout, and navigation.

### Tasks

- [ ] **6.1 Project Setup**
  - [ ] Initialize Next.js 15 with App Router
  - [ ] Configure TypeScript
  - [ ] Set up Tailwind CSS v4
  - [ ] Configure ESLint, Prettier

- [ ] **6.2 UI Foundation**
  - [ ] Install and configure Radix UI
  - [ ] Create base component library
  - [ ] Design tokens (colors, spacing)
  - [ ] Dark/light mode support

- [ ] **6.3 Authentication UI**
  - [ ] Login page (`/login`)
  - [ ] Signup via invitation page (`/signup?token=...`)
  - [ ] Forgot password page (future)
  - [ ] Auth context/provider (store JWT, user info)
  - [ ] Protected route wrapper
  - [ ] Auto-redirect if not authenticated
  - [ ] Token refresh logic

- [ ] **6.4 Layout & Navigation**
  - [ ] App shell with sidebar
  - [ ] Navigation menu
  - [ ] User menu (profile, logout, switch org)
  - [ ] Organization switcher (if user has multiple orgs)
  - [ ] Page layouts

- [ ] **6.5 State Management**
  - [ ] Set up Zustand stores (auth, org context)
  - [ ] API client with auth headers
  - [ ] SWR hooks setup with auth

- [ ] **6.6 Source Management Pages**
  - [ ] Sources list page
  - [ ] Add source modal/page
  - [ ] Source detail page
  - [ ] Sync trigger UI

- [ ] **6.7 Admin Pages (Superadmin only)**
  - [ ] Organizations list page
  - [ ] Create organization page
  - [ ] Organization detail (members, invite)

**Deliverables:**
- Running Next.js app
- Full authentication flow (login, signup via invite)
- Protected routes working
- Basic navigation working
- Source management UI complete

---

## Phase 7: Transformation Canvas UI

**Goal:** Build the visual transformation builder using React Flow.

### Tasks

- [ ] **7.1 React Flow Setup**
  - [ ] Install and configure React Flow
  - [ ] Custom node types
  - [ ] Custom edge types
  - [ ] Canvas controls (zoom, pan)

- [ ] **7.2 Node Components**
  - [ ] Source node (table selector)
  - [ ] Filter node (condition builder)
  - [ ] Select node (column picker)
  - [ ] Sort node (column + direction)
  - [ ] Output node (destination)

- [ ] **7.3 Action Palette**
  - [ ] Sidebar with available actions
  - [ ] Drag-and-drop to canvas
  - [ ] Action categories

- [ ] **7.4 Canvas Interaction**
  - [ ] Connect nodes with edges
  - [ ] Delete nodes/edges
  - [ ] Node configuration panels
  - [ ] Canvas state management (Zustand)

- [ ] **7.5 Recipe Serialization**
  - [ ] Canvas state to recipe JSON
  - [ ] Recipe JSON to canvas state
  - [ ] Auto-save drafts

**Deliverables:**
- Working transformation canvas
- Nodes can be added and connected
- Recipe serialization working

---

## Phase 8: Preview & Execution

**Goal:** Implement data preview with AG Grid and execute transformations.

### Tasks

- [ ] **8.1 AG Grid Setup**
  - [ ] Install AG Grid (community edition)
  - [ ] Configure for read-only preview
  - [ ] Column auto-sizing
  - [ ] Virtual scrolling for large datasets

- [ ] **8.2 DuckDB-WASM Integration**
  - [ ] Set up DuckDB-WASM in browser
  - [ ] Load sample data for preview
  - [ ] Execute preview queries locally

- [ ] **8.3 Preview Panel**
  - [ ] Split view: canvas + preview
  - [ ] Real-time preview on changes
  - [ ] Row count display
  - [ ] Column type indicators

- [ ] **8.4 Execution Flow**
  - [ ] Execute button
  - [ ] Progress indicator
  - [ ] Success/error feedback
  - [ ] Output table creation

- [ ] **8.5 Transformation Detail Page**
  - [ ] View transformation
  - [ ] Edit transformation
  - [ ] Run history
  - [ ] Output tables list

**Deliverables:**
- Live preview working
- Transformations can be executed
- Results visible in AG Grid

---

## Phase 9: Core Transformations

**Goal:** Implement the full set of core transformation actions.

### Tasks

- [ ] **9.1 Join Tables**
  - [ ] Join node UI (table selector, key columns)
  - [ ] Join types: inner, left, right, full
  - [ ] SQL generation for joins
  - [ ] Preview with joined data

- [ ] **9.2 Group & Summarize**
  - [ ] Group by node (column selector)
  - [ ] Aggregation functions: COUNT, SUM, AVG, MIN, MAX
  - [ ] Multiple aggregations per group
  - [ ] SQL generation for GROUP BY

- [ ] **9.3 Add Calculated Column**
  - [ ] Expression builder UI
  - [ ] Basic math operations
  - [ ] String operations
  - [ ] Conditional logic (CASE WHEN)
  - [ ] SQL generation for expressions

- [ ] **9.4 Data Cleaning**
  - [ ] Trim whitespace
  - [ ] Change case (upper, lower, title)
  - [ ] Replace values
  - [ ] Handle nulls
  - [ ] SQL generation for cleaning

- [ ] **9.5 Remove Duplicates**
  - [ ] Dedupe node UI
  - [ ] Select columns for uniqueness
  - [ ] Keep first/last option
  - [ ] SQL generation with ROW_NUMBER

- [ ] **9.6 Union Tables**
  - [ ] Union node (table selector)
  - [ ] Union vs Union All
  - [ ] Column mapping
  - [ ] SQL generation for UNION

**Deliverables:**
- All core transformations working
- Complex pipelines can be built
- Full Excel-equivalent functionality

---

## Phase 10: Polish & Production Ready

**Goal:** Prepare for production deployment with error handling, testing, and documentation.

### Tasks

- [ ] **10.1 Error Handling**
  - [ ] User-friendly error messages
  - [ ] Retry logic for API calls
  - [ ] Graceful degradation

- [ ] **10.2 Testing**
  - [ ] Backend unit tests
  - [ ] Backend integration tests
  - [ ] Frontend component tests
  - [ ] E2E tests with Playwright

- [ ] **10.3 Performance**
  - [ ] Query optimization
  - [ ] Frontend bundle optimization
  - [ ] Caching strategies

- [ ] **10.4 Documentation**
  - [ ] API documentation
  - [ ] User guide
  - [ ] Deployment guide

- [ ] **10.5 Deployment**
  - [ ] Backend deployment (Railway/Render)
  - [ ] Frontend deployment (Vercel)
  - [ ] Environment configuration
  - [ ] CI/CD pipeline

- [ ] **10.6 Monitoring**
  - [ ] Error tracking (Sentry)
  - [ ] Basic analytics
  - [ ] Health monitoring

**Deliverables:**
- Production-ready application
- Deployed and accessible
- Documentation complete

---

## Session Log

> Track what was done in each session for context.

### Session 1 - 2026-02-01
- Created implementation phases document
- Discussed authentication and multi-tenancy design
- Decided: Admin-controlled onboarding for V1 (superadmin creates orgs, invites NGO admins)
- Decided: JWT-based auth with email/password
- Future: Self-signup with personal workspaces
- **Completed Phase 1: Database Design**
  - Set up backend project structure (`backend/`)
  - Created all SQLAlchemy models (16 tables)
  - Set up Alembic with initial migration
  - Created seed script for superadmin
  - Documented ERD diagram (`docs/05_DATABASE_ERD.md`)
- Next: Phase 2 - Backend Foundation (FastAPI app, auth system)

---

## Notes & Decisions

### Authentication (V1)
- **Method:** Email + Password with JWT tokens
- **Onboarding:** Superadmin creates org → invites NGO admin → admin invites members
- **Tokens:** Access token (short-lived) + Refresh token (long-lived, stored in DB)
- **Password:** Hashed with bcrypt
- **Future:** Add Google OAuth, self-signup with personal workspaces

### Multi-tenancy
- Org-based isolation (each NGO = one org)
- Users can belong to multiple orgs
- API requests include org context (header: `X-Organization-ID` or from JWT)
- All resources scoped to organization

### Role Hierarchy
```
superadmin (platform-level)
    └── owner (org-level)
        └── admin
            └── member
                └── viewer (future)
```

### Key Dependencies
- Phase 2 depends on Phase 1 (database)
- Phase 3-4 can run in parallel after Phase 2
- Phase 5 depends on Phase 4 (needs data in warehouse)
- Phase 7-8 depend on Phase 6 (frontend foundation)
- Phase 9 depends on Phase 5, 7, 8

### Tech Stack Locked
- Backend: FastAPI + SQLAlchemy 2.0 + Python 3.12
- Frontend: Next.js 15 + TypeScript + Tailwind v4
- Database: Supabase (PostgreSQL)
- Warehouse: MotherDuck (DuckDB)
- Auth: Custom JWT (python-jose + bcrypt)
