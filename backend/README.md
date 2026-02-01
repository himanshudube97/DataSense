# Dalgo Lite - Backend

FastAPI backend for the Dalgo Lite no-code data transformation platform.

## Tech Stack

- **Framework:** FastAPI
- **Language:** Python 3.12+
- **Database:** PostgreSQL (Supabase)
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic
- **Auth:** JWT (python-jose + bcrypt)

## Project Structure

```
backend/
├── alembic/                 # Database migrations
│   ├── versions/            # Migration files
│   └── env.py               # Alembic configuration
├── app/
│   ├── api/                 # API routes
│   │   └── v1/              # API v1 endpoints
│   ├── core/                # Core functionality
│   │   ├── config.py        # Settings management
│   │   ├── database.py      # Database connection
│   │   └── seed.py          # Seed data script
│   ├── models/              # SQLAlchemy models
│   │   ├── base.py          # Base model classes
│   │   ├── user.py          # User model
│   │   ├── organization.py  # Organization models
│   │   ├── auth.py          # Auth-related models
│   │   ├── source.py        # Source management models
│   │   ├── warehouse.py     # Warehouse models
│   │   ├── transformation.py # Transformation models
│   │   ├── output.py        # Output & schedule models
│   │   └── audit.py         # Audit log model
│   ├── schemas/             # Pydantic schemas
│   └── services/            # Business logic
├── tests/                   # Test files
├── alembic.ini              # Alembic config
├── pyproject.toml           # Project dependencies
└── .env.example             # Environment template
```

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL database (local or Supabase)

### Installation

1. **Clone and navigate to backend:**
   ```bash
   cd dalgo-lite/backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Seed superadmin user:**
   ```bash
   python -m app.core.seed
   ```

### Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

API documentation will be available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database

### Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base
```

### Local PostgreSQL with Docker

```bash
docker run --name dalgo-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=dalgo_lite \
  -p 5432:5432 \
  -d postgres:16
```

## Development

### Code Style

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

### Running Tests

```bash
pytest
pytest --cov=app  # With coverage
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `JWT_SECRET_KEY` | Secret for JWT signing | Required |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |
| `SUPERADMIN_EMAIL` | Initial admin email | `admin@dalgo.org` |
| `SUPERADMIN_PASSWORD` | Initial admin password | `changeme123` |
