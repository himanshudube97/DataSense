# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

DataSense — a no-code data transformation platform for NGOs. Backend is FastAPI (Python), frontend is Next.js 15 (TypeScript/React 19/Tailwind 4).

## Development Commands

### Prerequisites
```bash
docker compose up -d          # PostgreSQL on port 5463
cp .env.example .env          # if .env doesn't exist
```

### Backend (from `backend/`)
```bash
uv sync                                          # install deps
uv run alembic upgrade head                       # apply migrations
uv run alembic revision --autogenerate -m "msg"   # generate migration
uv run uvicorn app.main:app --port 8057 --reload  # start dev server
```
API runs at `http://localhost:8057`. Swagger docs at `/docs`.

### Frontend (from `frontend/`)
```bash
npm install       # install deps
npm run dev       # start dev server on port 3000
npm run build     # production build
npm run lint      # ESLint
```

## Architecture

### Backend (`backend/app/`)
- **`main.py`** — FastAPI app with CORS (allows localhost:3000)
- **`config.py`** — pydantic-settings loading from `../.env`
- **`database.py`** — async SQLAlchemy engine + session + `Base` class
- **`core/security.py`** — bcrypt password hashing + JWT (python-jose). Access tokens (30min) and refresh tokens (7 days), both with a `type` claim
- **`api/deps.py`** — `get_current_user` dependency extracts Bearer token, validates `type=access`, returns `User`
- **`api/auth.py`** — signup (creates user + org + link), login, refresh, me
- **`api/organizations.py`** — list/get orgs for current user
- **`api/router.py`** — combines all routers under `/api/v1`

### Data Model
`User` ↔ `Organization` via `UserOrganization` join table (many-to-many). Signup creates all three records. All IDs are UUIDs. All relationships use `lazy="selectin"` (required for async SQLAlchemy — never use default lazy loading).

### Frontend (`frontend/src/`)
- **`lib/api.ts`** — `apiFetch<T>()` wrapper that auto-injects Bearer token. Access token stored in module-level variable, refresh token in localStorage
- **`lib/auth.tsx`** — `AuthProvider` context with `useAuth()` hook. Handles login/signup/logout/auto-refresh on mount
- **`app/page.tsx`** — redirects to `/dashboard` or `/login` based on auth state
- **`app/(auth)/`** — login and signup pages (unprotected route group)
- **`app/dashboard/layout.tsx`** — protected layout that redirects to `/login` if unauthenticated

### Ports
| Service    | Port |
|------------|------|
| PostgreSQL | 5463 |
| Backend    | 8057 |
| Frontend   | 3000 |

Ports 5432 and 8000 are taken by Airbyte on this machine.

## Key Conventions

- **Password hashing**: Use `bcrypt` directly, not `passlib` (passlib is broken with bcrypt >= 4.1)
- **SQLAlchemy relationships**: Always set `lazy="selectin"` on any relationship that will be accessed, including nested ones
- **Alembic**: Configured for async in `alembic/env.py`. Models must be imported in env.py for autogenerate to detect them
- **Package manager**: `uv` for Python, `npm` for Node
- **Auth tokens**: JWT with `type` field ("access" or "refresh") to prevent token misuse
