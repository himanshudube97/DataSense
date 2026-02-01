# Dalgo Lite: Technology Stack

**Version:** 1.0
**Date:** February 2026
**Status:** Approved

---

## Table of Contents

1. [Stack Overview](#stack-overview)
2. [Frontend](#frontend)
3. [Backend](#backend)
4. [Database & Storage](#database--storage)
5. [Data Warehouse](#data-warehouse)
6. [Authentication](#authentication)
7. [Infrastructure](#infrastructure)
8. [Development Tools](#development-tools)
9. [Third-Party Services](#third-party-services)

---

## Stack Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                    │
│                     Next.js 15 (App Router)                             │
│              TypeScript • Tailwind CSS • Zustand                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST API / WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                     │
│                      Python 3.12 + FastAPI                              │
│              SQLAlchemy • Pydantic • Celery (optional)                  │
└─────────────────────────────────────────────────────────────────────────┘
                    │                               │
                    │                               │
                    ▼                               ▼
┌─────────────────────────────┐     ┌─────────────────────────────────────┐
│      SUPABASE               │     │         MOTHERDUCK                  │
│  ─────────────────────────  │     │  ───────────────────────────────    │
│  • Authentication (OAuth)   │     │  • User's data warehouse            │
│  • PostgreSQL (metadata)    │     │  • Transformation execution         │
│  • Row Level Security       │     │  • 10GB free per user               │
│  • Realtime subscriptions   │     │  • DuckDB SQL                       │
└─────────────────────────────┘     └─────────────────────────────────────┘
```

---

## Frontend

### Framework: Next.js 15

**Why Next.js?**
- Server Components for better performance
- App Router for modern routing patterns
- Excellent TypeScript support
- Same framework as Dalgo main product (code sharing potential)
- Large ecosystem and community

**Version:** 15.x with App Router

```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  }
}
```

### Language: TypeScript

**Why TypeScript?**
- Type safety for complex transformation logic
- Better IDE support and autocomplete
- Catch errors at compile time
- Self-documenting code

```json
{
  "devDependencies": {
    "typescript": "^5.3.0",
    "@types/react": "^19.0.0",
    "@types/node": "^20.0.0"
  }
}
```

### Styling: Tailwind CSS v4

**Why Tailwind?**
- Rapid UI development
- Consistent design system
- Small bundle size (purged unused styles)
- Excellent component library ecosystem

```json
{
  "dependencies": {
    "tailwindcss": "^4.0.0",
    "@tailwindcss/forms": "^0.5.0"
  }
}
```

### State Management: Zustand

**Why Zustand?**
- Lightweight (< 1KB)
- Simple API, minimal boilerplate
- Works great with React 19
- Already used in Dalgo main product

```json
{
  "dependencies": {
    "zustand": "^5.0.0"
  }
}
```

### Key UI Libraries

| Library | Purpose | Why This Choice |
|---------|---------|-----------------|
| **[AG Grid](https://www.ag-grid.com/)** | Spreadsheet-like data grid | Best-in-class Excel-like experience, free community version |
| **[Radix UI](https://www.radix-ui.com/)** | Accessible primitives | Unstyled, accessible, composable |
| **[React Flow](https://reactflow.dev/)** | Transformation canvas | Node-based diagrams, drag-and-drop |
| **[React Query Builder](https://react-querybuilder.js.org/)** | Filter/condition UI | SQL export built-in |
| **[Lucide React](https://lucide.dev/)** | Icons | Consistent, lightweight |
| **[Sonner](https://sonner.emilkowal.ski/)** | Toast notifications | Beautiful, simple API |

```json
{
  "dependencies": {
    "ag-grid-react": "^32.0.0",
    "ag-grid-community": "^32.0.0",
    "@radix-ui/react-dialog": "^1.0.0",
    "@radix-ui/react-dropdown-menu": "^2.0.0",
    "@radix-ui/react-select": "^2.0.0",
    "@radix-ui/react-tabs": "^1.0.0",
    "@xyflow/react": "^12.0.0",
    "react-querybuilder": "^7.0.0",
    "lucide-react": "^0.300.0",
    "sonner": "^1.0.0"
  }
}
```

### Data Fetching: SWR

**Why SWR?**
- Stale-while-revalidate strategy
- Built-in caching and deduplication
- Real-time updates support
- Already used in Dalgo main product

```json
{
  "dependencies": {
    "swr": "^2.2.0"
  }
}
```

### Form Handling: React Hook Form + Zod

```json
{
  "dependencies": {
    "react-hook-form": "^7.50.0",
    "zod": "^3.22.0",
    "@hookform/resolvers": "^3.3.0"
  }
}
```

---

## Backend

### Framework: FastAPI

**Why FastAPI over Django?**
- Async-first (better for I/O-heavy data operations)
- Automatic OpenAPI documentation
- Pydantic integration (validation)
- Lighter weight than Django
- Better suited for API-only backend

**Why Python?**
- Best ecosystem for data processing
- Native DuckDB/MotherDuck support
- Easy SQL generation and manipulation
- Familiar to data engineers

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
```

### ORM: SQLAlchemy 2.0

**Why SQLAlchemy?**
- Industry standard Python ORM
- Async support in 2.0
- Works with any SQL database
- Powerful query builder

```
sqlalchemy>=2.0.0
asyncpg>=0.29.0  # Async PostgreSQL driver
```

### Validation: Pydantic v2

```
pydantic>=2.5.0
pydantic-settings>=2.1.0
```

### Key Backend Libraries

| Library | Purpose |
|---------|---------|
| **duckdb** | Local DuckDB operations, query building |
| **google-api-python-client** | Google Sheets API |
| **google-auth** | Google OAuth |
| **sqlglot** | SQL parsing and transpilation |
| **httpx** | Async HTTP client |
| **python-jose** | JWT handling |
| **passlib** | Password hashing |

```
duckdb>=0.10.0
google-api-python-client>=2.100.0
google-auth>=2.25.0
google-auth-oauthlib>=1.2.0
sqlglot>=20.0.0
httpx>=0.26.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

### Background Tasks: Celery (Optional)

For scheduled sync jobs:

```
celery>=5.3.0
redis>=5.0.0
```

**Note:** Start without Celery, add if needed for scheduled syncs.

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Settings management
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependencies (auth, db)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── sources.py      # Google Sheets endpoints
│   │   │   ├── transforms.py   # Transformation endpoints
│   │   │   ├── warehouse.py    # MotherDuck endpoints
│   │   │   └── users.py        # User management
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # Auth utilities
│   │   ├── google_sheets.py    # Sheets API wrapper
│   │   ├── motherduck.py       # MotherDuck client
│   │   └── sql_generator.py    # Click actions → SQL
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── data_source.py
│   │   └── transformation.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── source.py
│   │   ├── transform.py
│   │   └── common.py
│   │
│   └── services/
│       ├── __init__.py
│       ├── ingestion.py        # Sheets → MotherDuck
│       ├── transformation.py   # Execute transforms
│       └── sync.py             # Scheduled sync logic
│
├── tests/
├── alembic/                    # Database migrations
├── requirements.txt
├── pyproject.toml
└── Dockerfile
```

---

## Database & Storage

### Metadata Database: Supabase (PostgreSQL)

**Why Supabase?**

| Feature | Benefit for Dalgo Lite |
|---------|------------------------|
| **Managed PostgreSQL** | No database ops needed |
| **Built-in Auth** | Google OAuth out of the box |
| **Row Level Security** | Multi-tenant data isolation |
| **Realtime** | Live updates for collaboration |
| **Free Tier** | 500MB database, 50k monthly active users |
| **REST API** | Auto-generated from schema |

**What We Store in Supabase:**

```sql
-- Organizations (tenants)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    motherduck_token_encrypted TEXT, -- Encrypted MD credentials
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    email TEXT NOT NULL,
    full_name TEXT,
    organization_id UUID REFERENCES organizations(id),
    role TEXT DEFAULT 'member', -- 'admin', 'member'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data Sources (Google Sheets connections)
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name TEXT NOT NULL,
    sheet_id TEXT NOT NULL,
    sheet_tab TEXT,
    table_name TEXT NOT NULL, -- Name in MotherDuck
    sync_frequency TEXT DEFAULT 'manual',
    last_synced_at TIMESTAMPTZ,
    row_count INTEGER,
    schema_json JSONB, -- Column names and types
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transformations (saved pipelines)
CREATE TABLE transformations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name TEXT NOT NULL,
    description TEXT,
    canvas_json JSONB NOT NULL, -- Visual canvas state
    steps_json JSONB NOT NULL,  -- Ordered transformation steps
    output_table TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transformation Steps (for history/debugging)
CREATE TABLE transformation_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transformation_id UUID REFERENCES transformations(id),
    step_order INTEGER NOT NULL,
    step_type TEXT NOT NULL, -- 'filter', 'join', 'aggregate', etc.
    config_json JSONB NOT NULL,
    generated_sql TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Row Level Security Example:**

```sql
-- Users can only see their organization's data
ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own org data sources"
ON data_sources FOR ALL
USING (
    organization_id IN (
        SELECT organization_id FROM users WHERE id = auth.uid()
    )
);
```

### Supabase Setup

```bash
# Install Supabase CLI
npm install -g supabase

# Initialize project
supabase init

# Start local development
supabase start

# Deploy to production
supabase link --project-ref <project-id>
supabase db push
```

**Environment Variables:**

```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # Backend only
```

---

## Data Warehouse

### MotherDuck (User's Account)

**Why MotherDuck?**

| Feature | Benefit |
|---------|---------|
| **10GB Free** | Generous for NGO datasets |
| **DuckDB Compatible** | Modern SQL, fast analytics |
| **Serverless** | No infrastructure to manage |
| **Shareable** | Team collaboration built-in |
| **Data Stays with User** | They own their warehouse |

**Integration Approach:**

```python
# User connects their MotherDuck account via OAuth
# We store encrypted token in Supabase
# All queries run in their MotherDuck instance

import duckdb

def get_user_connection(user_id: str) -> duckdb.DuckDBPyConnection:
    """Get connection to user's MotherDuck instance."""
    token = get_encrypted_token(user_id)  # From Supabase
    return duckdb.connect(f"md:?motherduck_token={token}")
```

**What Gets Stored in MotherDuck:**

```sql
-- Raw data from Google Sheets
CREATE TABLE raw_beneficiaries AS
SELECT * FROM read_csv('data.csv');

-- Transformed outputs
CREATE TABLE transformed_beneficiary_summary AS
SELECT
    district,
    COUNT(*) as total_beneficiaries,
    AVG(age) as avg_age
FROM raw_beneficiaries
WHERE status = 'Active'
GROUP BY district;
```

### DuckDB-WASM (Browser Preview)

For instant previews without hitting MotherDuck:

```typescript
import * as duckdb from '@duckdb/duckdb-wasm';

// Initialize in browser
const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);
const worker = new Worker(bundle.mainWorker);
const logger = new duckdb.ConsoleLogger();
const db = new duckdb.AsyncDuckDB(logger, worker);
await db.instantiate(bundle.mainModule);

// Run preview queries
const conn = await db.connect();
const result = await conn.query(`
    SELECT * FROM uploaded_data LIMIT 100
`);
```

---

## Authentication

### Supabase Auth + Google OAuth

**Flow:**

```
┌─────────┐     ┌─────────────┐     ┌──────────────┐     ┌───────────┐
│  User   │────▶│  Next.js    │────▶│   Supabase   │────▶│  Google   │
│ Browser │     │  Frontend   │     │    Auth      │     │  OAuth    │
└─────────┘     └─────────────┘     └──────────────┘     └───────────┘
                      │                    │
                      │   JWT Token        │
                      │◀───────────────────│
                      │                    │
                      ▼                    │
               ┌─────────────┐             │
               │  FastAPI    │◀────────────┘
               │  Backend    │   Verify JWT
               └─────────────┘
```

**Why Google OAuth?**

1. **Single Sign-On:** Users already have Google accounts
2. **Sheets Access:** Same OAuth grants Sheets API access
3. **No Password Management:** Reduced security burden
4. **Trust:** NGOs trust Google

**Frontend Implementation:**

```typescript
// lib/supabase.ts
import { createBrowserClient } from '@supabase/ssr'

export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Login with Google
export async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      scopes: 'https://www.googleapis.com/auth/spreadsheets.readonly',
      redirectTo: `${window.location.origin}/auth/callback`
    }
  })
}
```

**Backend JWT Verification:**

```python
# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import jwt, JWTError

security = HTTPBearer()

async def get_current_user(
    credentials = Depends(security)
) -> dict:
    """Verify Supabase JWT and return user."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
```

---

## Infrastructure

### Development

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL DEVELOPMENT                         │
├─────────────────────────────────────────────────────────────┤
│  Next.js (npm run dev)          → localhost:3000            │
│  FastAPI (uvicorn)              → localhost:8000            │
│  Supabase Local (supabase start) → localhost:54321          │
│  DuckDB (local file)            → ./dev.duckdb              │
└─────────────────────────────────────────────────────────────┘
```

### Production

```
┌─────────────────────────────────────────────────────────────┐
│                      PRODUCTION                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐                                        │
│  │    Vercel       │  ← Next.js frontend                    │
│  │  (Free tier)    │                                        │
│  └────────┬────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │   Railway /     │     │    Supabase     │               │
│  │   Render        │────▶│   (Free tier)   │               │
│  │   (FastAPI)     │     │   PostgreSQL    │               │
│  └────────┬────────┘     └─────────────────┘               │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                        │
│  │   MotherDuck    │  ← User's own account                 │
│  │  (User's data)  │                                        │
│  └─────────────────┘                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Hosting Recommendations

| Component | Service | Tier | Monthly Cost |
|-----------|---------|------|--------------|
| Frontend | Vercel | Free/Pro | $0-20 |
| Backend | Railway | Starter | $0-20 |
| Database | Supabase | Free | $0 |
| Data Warehouse | MotherDuck | Free (user's) | $0 |

**Total infrastructure cost: $0-40/month** for significant scale.

---

## Development Tools

### Code Quality

```json
{
  "devDependencies": {
    "eslint": "^8.56.0",
    "eslint-config-next": "^15.0.0",
    "prettier": "^3.2.0",
    "prettier-plugin-tailwindcss": "^0.5.0",
    "@typescript-eslint/eslint-plugin": "^7.0.0"
  }
}
```

**Python:**

```
ruff>=0.1.0           # Fast linter
black>=24.0.0         # Formatter
mypy>=1.8.0           # Type checking
pytest>=8.0.0         # Testing
pytest-asyncio>=0.23.0
```

### Testing

**Frontend:**

```json
{
  "devDependencies": {
    "jest": "^29.7.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "playwright": "^1.41.0"
  }
}
```

**Backend:**

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
httpx>=0.26.0  # For testing FastAPI
```

### CI/CD

**GitHub Actions:**

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run lint
      - run: npm run test
      - run: npm run build

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: mypy .
      - run: pytest --cov
```

---

## Third-Party Services

### Required

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| **Google Cloud** | Sheets API, OAuth | 100 requests/100 sec |
| **Supabase** | Auth, metadata DB | 500MB, 50k MAU |
| **MotherDuck** | Data warehouse | 10GB per user |

### Optional

| Service | Purpose | When to Add |
|---------|---------|-------------|
| **Sentry** | Error tracking | At launch |
| **PostHog** | Product analytics | For growth |
| **Resend** | Transactional email | For notifications |

---

## Environment Variables

### Frontend (.env.local)

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Feature flags
NEXT_PUBLIC_ENABLE_DEBUG=false
```

### Backend (.env)

```env
# App
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret

# Google
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx

# MotherDuck (for testing only, users bring their own)
MOTHERDUCK_TOKEN=md_xxx

# Redis (if using Celery)
REDIS_URL=redis://localhost:6379/0
```

---

## Version Summary

| Component | Version | Notes |
|-----------|---------|-------|
| Node.js | 20 LTS | Required for Next.js 15 |
| Python | 3.12 | Latest stable |
| Next.js | 15.x | App Router |
| FastAPI | 0.109+ | Async support |
| PostgreSQL | 15+ | Via Supabase |
| DuckDB | 0.10+ | MotherDuck compatible |

---

*Document maintained by: Dalgo Lite Engineering Team*
*Last updated: February 2026*
